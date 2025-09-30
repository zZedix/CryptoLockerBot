"""Async Telegram bot for managing encrypted credentials."""
from __future__ import annotations

import asyncio
import logging
from logging.handlers import RotatingFileHandler
import os
import time
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
    constants,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from crypto import EncryptionContext, EncryptionError, build_context, decrypt, encrypt
from db import Database
from i18n import DEFAULT_LANG, SUPPORTED_LANGS, t

LOGGER = logging.getLogger(__name__)
STATE_TTL_SECONDS = 300
MAX_ACCOUNTS_INLINE = 50


@dataclass
class UserState:
    action: str
    step: str
    data: Dict[str, Any] = field(default_factory=dict)
    expires_at: float = field(default_factory=lambda: time.monotonic())


class StateManager:
    def __init__(self, ttl: int = STATE_TTL_SECONDS) -> None:
        self._ttl = ttl
        self._states: Dict[int, UserState] = {}

    def _cleanup(self) -> None:
        now = time.monotonic()
        expired = [user_id for user_id, state in self._states.items() if state.expires_at <= now]
        for user_id in expired:
            self._states.pop(user_id, None)

    def set(self, user_id: int, action: str, step: str, *, data: Optional[Dict[str, Any]] = None) -> None:
        self._cleanup()
        self._states[user_id] = UserState(
            action=action,
            step=step,
            data=data or {},
            expires_at=time.monotonic() + self._ttl,
        )

    def get(self, user_id: int) -> Optional[UserState]:
        self._cleanup()
        state = self._states.get(user_id)
        if state:
            state.expires_at = time.monotonic() + self._ttl
        return state

    def clear(self, user_id: int) -> None:
        self._states.pop(user_id, None)


@dataclass
class RuntimeContext:
    db: Database
    encryption: EncryptionContext
    admin_id: int
    states: StateManager


def build_main_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [t(lang, "BTN_ADD"), t(lang, "BTN_SEARCH")],
            [t(lang, "BTN_REMOVE"), t(lang, "BTN_EDIT")],
            [t(lang, "BTN_SHOW")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def get_runtime(context: ContextTypes.DEFAULT_TYPE) -> RuntimeContext:
    return context.bot_data["runtime"]


def is_authorized(user_id: Optional[int], runtime: RuntimeContext) -> bool:
    return user_id is not None and user_id == runtime.admin_id


async def ensure_user(runtime: RuntimeContext, telegram_id: int) -> None:
    await runtime.db.ensure_user(telegram_id)


async def get_user_lang(runtime: RuntimeContext, telegram_id: int) -> str:
    try:
        return await runtime.db.get_user_lang(telegram_id)
    except Exception:
        LOGGER.exception("Failed obtaining language for user %s", telegram_id)
        return DEFAULT_LANG


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = get_runtime(context)
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return
    if not is_authorized(user.id, runtime):
        await update.message.reply_text(t(DEFAULT_LANG, "NOT_ADMIN"))
        return
    await ensure_user(runtime, user.id)
    lang = await get_user_lang(runtime, user.id)
    menu = build_main_menu(lang)
    text = f"{t(lang, 'WELCOME')}\n\n{t(lang, 'MENU_HINT')}"
    await update.message.reply_text(text, reply_markup=menu)
    LOGGER.info("Sent start menu to %s", user.id)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = get_runtime(context)
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return
    if not is_authorized(user.id, runtime):
        await update.message.reply_text(t(DEFAULT_LANG, "NOT_ADMIN"))
        return
    await ensure_user(runtime, user.id)
    lang = await get_user_lang(runtime, user.id)
    menu_markup = build_main_menu(lang)
    await update.message.reply_text(t(lang, "MENU_HINT"), reply_markup=menu_markup)


async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = get_runtime(context)
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return
    if not is_authorized(user.id, runtime):
        await update.message.reply_text(t(DEFAULT_LANG, "NOT_ADMIN"))
        return
    await ensure_user(runtime, user.id)
    if not context.args:
        await update.message.reply_text(f"Usage: /lang {'|'.join(SUPPORTED_LANGS)}")
        return
    lang = context.args[0].lower()
    if lang not in SUPPORTED_LANGS:
        await update.message.reply_text(f"Usage: /lang {'|'.join(SUPPORTED_LANGS)}")
        return
    await runtime.db.set_user_lang(user.id, lang)
    menu_markup = build_main_menu(lang)
    key = "LANG_CHANGED_EN" if lang == "en" else "LANG_CHANGED_FA"
    await update.message.reply_text(t(lang, key), reply_markup=menu_markup)


def _validate_name(name: str) -> bool:
    return 1 <= len(name) <= 64


def _validate_secret(value: str) -> bool:
    return 1 <= len(value) <= 512


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = get_runtime(context)
    message = update.message
    if not message:
        return
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return
    if not is_authorized(user.id, runtime):
        await message.reply_text(t(DEFAULT_LANG, "NOT_ADMIN"))
        return
    await ensure_user(runtime, user.id)
    lang = await get_user_lang(runtime, user.id)
    text = message.text.strip()
    state = runtime.states.get(user.id)
    if state:
        await handle_stateful_message(update, context, state, lang)
        return

    if text == t(lang, "BTN_ADD"):
        runtime.states.set(user.id, action="add", step="name", data={})
        await message.reply_text(t(lang, "ASK_ADD_NAME"))
        LOGGER.info("User %s started add flow", user.id)
    elif text == t(lang, "BTN_SEARCH"):
        runtime.states.set(user.id, action="search", step="query")
        await message.reply_text(t(lang, "ASK_SEARCH"))
    elif text == t(lang, "BTN_REMOVE"):
        await send_account_list(update, context, lang, purpose="remove")
    elif text == t(lang, "BTN_EDIT"):
        await send_account_list(update, context, lang, purpose="edit")
    elif text == t(lang, "BTN_SHOW"):
        await send_account_list(update, context, lang, purpose="show")
    else:
        await message.reply_text(t(lang, "MENU_HINT"), reply_markup=build_main_menu(lang))


async def handle_stateful_message(update: Update, context: ContextTypes.DEFAULT_TYPE, state: UserState, lang: str) -> None:
    runtime = get_runtime(context)
    message = update.message
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return
    text = message.text.strip()
    if state.action == "add":
        await handle_add_flow(runtime, message, state, user_id, text, lang)
    elif state.action == "search":
        runtime.states.clear(user_id)
        await process_search_query(runtime, message, user_id, text, lang)
    elif state.action == "edit_value":
        await handle_edit_value(runtime, message, state, user_id, text, lang)
    else:
        runtime.states.clear(user_id)
        await message.reply_text(t(lang, "ERR_GENERIC"))


async def handle_add_flow(runtime: RuntimeContext, message, state: UserState, user_id: int, text: str, lang: str) -> None:
    if state.step == "name":
        name = text.strip()
        if not _validate_name(name):
            await message.reply_text(t(lang, "INVALID_NAME"))
            return
        state.data["name"] = name
        state.step = "username"
        await message.reply_text(t(lang, "ASK_ADD_USERNAME", name=name))
    elif state.step == "username":
        username = text.strip()
        if not _validate_secret(username):
            await message.reply_text(t(lang, "INVALID_CREDENTIAL"))
            return
        state.data["username"] = username
        state.step = "password"
        await message.reply_text(t(lang, "ASK_ADD_PASSWORD", name=state.data["name"]))
    elif state.step == "password":
        password = text.strip()
        if not _validate_secret(password):
            await message.reply_text(t(lang, "INVALID_CREDENTIAL"))
            return
        name = state.data["name"]
        username = state.data["username"]
        try:
            enc = runtime.encryption
            username_ct = encrypt(username, enc)
            password_ct = encrypt(password, enc)
            await runtime.db.add_account(user_id, name, username_ct, password_ct)
            await message.reply_text(t(lang, "ADDED_SUCCESS", name=name))
            LOGGER.info("User %s added credential '%s'", user_id, name)
        except EncryptionError:
            LOGGER.exception("Encryption failure while adding account for %s", user_id)
            await message.reply_text(t(lang, "ERR_GENERIC"))
        finally:
            runtime.states.clear(user_id)
    else:
        runtime.states.clear(user_id)
        await message.reply_text(t(lang, "ERR_GENERIC"))


async def process_search_query(runtime: RuntimeContext, message, user_id: int, query: str, lang: str) -> None:
    results = await runtime.db.search_accounts(user_id, query)
    if not results:
        await message.reply_text(t(lang, "NO_MATCH", q=query))
        return
    buttons = [
        [InlineKeyboardButton(text=entry.name, callback_data=f"show|{entry.id}")]
        for entry in results[:MAX_ACCOUNTS_INLINE]
    ]
    markup = InlineKeyboardMarkup(buttons)
    await message.reply_text(t(lang, "SEARCH_RESULTS"), reply_markup=markup)


async def send_account_list(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, *, purpose: str) -> None:
    runtime = get_runtime(context)
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return
    accounts = await runtime.db.list_accounts(user.id)
    if not accounts:
        await context.bot.send_message(chat.id, t(lang, "NO_ACCOUNTS"))
        return
    if purpose == "remove":
        callback_prefix = "remove_confirm"
        prompt_key = "PROMPT_REMOVE"
    elif purpose == "edit":
        callback_prefix = "edit_select"
        prompt_key = "PROMPT_EDIT"
    else:
        callback_prefix = "show"
        prompt_key = "PROMPT_SHOW"
    buttons = [
        [InlineKeyboardButton(text=entry.name, callback_data=f"{callback_prefix}|{entry.id}")]
        for entry in accounts[:MAX_ACCOUNTS_INLINE]
    ]
    markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(chat.id, t(lang, prompt_key), reply_markup=markup)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = get_runtime(context)
    query = update.callback_query
    user = update.effective_user
    if not query or not user:
        return
    await query.answer()
    if not is_authorized(user.id, runtime):
        await query.edit_message_text(t(DEFAULT_LANG, "NOT_ADMIN"))
        return

    lang = await get_user_lang(runtime, user.id)
    payload = query.data or ""
    parts = payload.split("|")

    if parts[0] == "show" and len(parts) == 2:
        await handle_show_callback(query, runtime, user.id, parts[1], lang)
    elif parts[0] == "remove_confirm" and len(parts) == 2:
        await handle_remove_confirm(query, runtime, user.id, parts[1], lang)
    elif parts[0] == "remove_do" and len(parts) == 2:
        await handle_remove_do(query, runtime, user.id, parts[1], lang)
    elif parts[0] == "cancel":
        await query.edit_message_text(t(lang, "MENU_HINT"))
    elif parts[0] == "edit_select" and len(parts) == 2:
        await handle_edit_select(query, runtime, user.id, parts[1], lang)
    elif parts[0] == "edit_field" and len(parts) == 3:
        await handle_edit_field(query, runtime, user.id, parts[1], parts[2], lang)
    elif parts[0] == "close":
        if query.message:
            try:
                await query.message.delete()
            except Exception:
                LOGGER.debug("Failed to delete message for user %s", user.id)
    else:
        await query.edit_message_text(t(lang, "ERR_GENERIC"))


async def handle_show_callback(query, runtime: RuntimeContext, user_id: int, account_id_raw: str, lang: str) -> None:
    if not account_id_raw.isdigit():
        await query.edit_message_text(t(lang, "ERR_GENERIC"))
        return
    account_id = int(account_id_raw)
    account = await runtime.db.get_account(account_id, user_id)
    if not account:
        await query.edit_message_text(t(lang, "ERR_GENERIC"))
        return
    try:
        username = decrypt(account.username, runtime.encryption)
        password = decrypt(account.password, runtime.encryption)
    except EncryptionError:
        LOGGER.exception("Failed to decrypt account %s for user %s", account_id, user_id)
        await query.edit_message_text(t(lang, "ERR_GENERIC"))
        return
    text = (
        f"<b>{escape(account.name)}</b>\n"
        f"<pre>Username: {escape(username)}\nPassword: {escape(password)}</pre>"
    )
    close_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text=t(lang, "BTN_CLOSE"), callback_data="close")]]
    )
    await query.edit_message_text(text, parse_mode=constants.ParseMode.HTML, reply_markup=close_button)


async def handle_remove_confirm(query, runtime: RuntimeContext, user_id: int, account_id_raw: str, lang: str) -> None:
    if not account_id_raw.isdigit():
        await query.edit_message_text(t(lang, "ERR_GENERIC"))
        return
    account_id = int(account_id_raw)
    account = await runtime.db.get_account(account_id, user_id)
    if not account:
        await query.edit_message_text(t(lang, "ERR_GENERIC"))
        return
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text=t(lang, "BTN_YES_DELETE"), callback_data=f"remove_do|{account_id}"),
                InlineKeyboardButton(text=t(lang, "BTN_NO_CANCEL"), callback_data="cancel"),
            ]
        ]
    )
    await query.edit_message_text(
        t(lang, "ASK_REMOVE_CONFIRM", name=account.name),
        reply_markup=buttons,
    )


async def handle_remove_do(query, runtime: RuntimeContext, user_id: int, account_id_raw: str, lang: str) -> None:
    if not account_id_raw.isdigit():
        await query.edit_message_text(t(lang, "ERR_GENERIC"))
        return
    account_id = int(account_id_raw)
    account = await runtime.db.get_account(account_id, user_id)
    if not account:
        await query.edit_message_text(t(lang, "ERR_GENERIC"))
        return
    success = await runtime.db.delete_account(account_id, user_id)
    if success:
        await query.edit_message_text(t(lang, "REMOVED_SUCCESS", name=account.name))
        LOGGER.info("User %s removed credential '%s'", user_id, account.name)
    else:
        await query.edit_message_text(t(lang, "ERR_GENERIC"))


async def handle_edit_select(query, runtime: RuntimeContext, user_id: int, account_id_raw: str, lang: str) -> None:
    if not account_id_raw.isdigit():
        await query.edit_message_text(t(lang, "ERR_GENERIC"))
        return
    account_id = int(account_id_raw)
    account = await runtime.db.get_account(account_id, user_id)
    if not account:
        await query.edit_message_text(t(lang, "ERR_GENERIC"))
        return
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=t(lang, "BTN_EDIT_USERNAME"),
                    callback_data=f"edit_field|{account_id}|username",
                ),
                InlineKeyboardButton(
                    text=t(lang, "BTN_EDIT_PASSWORD"),
                    callback_data=f"edit_field|{account_id}|password",
                ),
            ]
        ]
    )
    await query.edit_message_text(t(lang, "EDIT_CHOOSE_FIELD", name=account.name), reply_markup=buttons)


async def handle_edit_field(query, runtime: RuntimeContext, user_id: int, account_id_raw: str, field: str, lang: str) -> None:
    if not account_id_raw.isdigit():
        await query.edit_message_text(t(lang, "ERR_GENERIC"))
        return
    if field not in {"username", "password"}:
        await query.edit_message_text(t(lang, "ERR_GENERIC"))
        return
    account_id = int(account_id_raw)
    account = await runtime.db.get_account(account_id, user_id)
    if not account:
        await query.edit_message_text(t(lang, "ERR_GENERIC"))
        return
    runtime.states.set(
        user_id,
        action="edit_value",
        step="await_value",
        data={"account_id": account_id, "field": field, "name": account.name},
    )
    prompt_key = "ASK_NEW_USERNAME" if field == "username" else "ASK_NEW_PASSWORD"
    await query.edit_message_text(t(lang, prompt_key, name=account.name))


async def handle_edit_value(runtime: RuntimeContext, message, state: UserState, user_id: int, text: str, lang: str) -> None:
    field = state.data.get("field")
    account_id = state.data.get("account_id")
    account_name = state.data.get("name")
    if not field or not account_id:
        runtime.states.clear(user_id)
        await message.reply_text(t(lang, "ERR_GENERIC"))
        return
    value = text.strip()
    if not _validate_secret(value):
        await message.reply_text(t(lang, "INVALID_CREDENTIAL"))
        return
    try:
        ciphertext = encrypt(value, runtime.encryption)
        updated = await runtime.db.update_account_field(account_id, user_id, field=field, value=ciphertext)
        if updated:
            runtime.states.clear(user_id)
            field_label = ("Username" if field == "username" else "Password")
            if lang == "fa":
                field_label = "نام‌کاربری" if field == "username" else "رمز"
            await message.reply_text(
                t(lang, "EDIT_SUCCESS", field=field_label, name=account_name),
                reply_markup=build_main_menu(lang),
            )
            LOGGER.info("User %s updated %s for credential '%s'", user_id, field, account_name)
        else:
            runtime.states.clear(user_id)
            await message.reply_text(t(lang, "ERR_GENERIC"))
    except EncryptionError:
        LOGGER.exception("Encryption failure during edit for user %s", user_id)
        runtime.states.clear(user_id)
        await message.reply_text(t(lang, "ERR_GENERIC"))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.exception("Unhandled error while processing update: %s", update)
    if isinstance(update, Update):
        user = update.effective_user
        runtime = get_runtime(context)
        if user and is_authorized(user.id, runtime):
            lang = await get_user_lang(runtime, user.id)
            if update.message:
                await update.message.reply_text(t(lang, "ERR_GENERIC"))
            elif update.callback_query:
                await update.callback_query.edit_message_text(t(lang, "ERR_GENERIC"))


def configure_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=5)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)


def load_configuration() -> tuple[str, int, str, str, str]:
    config_path = Path.home() / ".cryptolocker" / "config.env"
    if config_path.exists():
        load_dotenv(config_path)
    else:
        load_dotenv()
    token = os.getenv("BOT_TOKEN")
    admin_id = os.getenv("ADMIN_TELEGRAM_ID")
    db_path = os.getenv("DB_PATH")
    salt_file = os.getenv("KEY_DERIVATION_SALT_FILE")
    passphrase = os.getenv("ENCRYPTION_PASSPHRASE") or os.getenv("CRYPTOLOCKER_PASSPHRASE")
    if not token:
        raise RuntimeError("BOT_TOKEN is not configured")
    if not admin_id or not admin_id.isdigit():
        raise RuntimeError("ADMIN_TELEGRAM_ID must be numeric")
    if not db_path:
        raise RuntimeError("DB_PATH is required")
    if not salt_file:
        raise RuntimeError("KEY_DERIVATION_SALT_FILE is required")
    if not passphrase:
        raise RuntimeError("Encryption passphrase environment variable ENCRYPTION_PASSPHRASE is missing")
    return token, int(admin_id), db_path, salt_file, passphrase


async def prepare_runtime(db_path: str, salt_file: str, passphrase: str, admin_id: int) -> RuntimeContext:
    database = Database(db_path)
    await database.init()
    encryption = build_context(passphrase, salt_file)
    return RuntimeContext(db=database, encryption=encryption, admin_id=admin_id, states=StateManager())


def main() -> None:
    log_file = Path.home() / ".cryptolocker" / "cryptolocker.log"
    configure_logging(log_file)
    token, admin_id, db_path, salt_file, passphrase = load_configuration()
    runtime = asyncio.run(prepare_runtime(db_path, salt_file, passphrase, admin_id))
    application = Application.builder().token(token).build()
    application.bot_data["runtime"] = runtime

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("lang", change_language))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.add_error_handler(error_handler)

    LOGGER.info("Starting CryptoLockerBot")
    application.run_polling()


if __name__ == "__main__":
    main()
