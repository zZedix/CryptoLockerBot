"""Localization utilities for CryptoLockerBot."""
from __future__ import annotations

from typing import Dict

LANG_EN = {
    "WELCOME": "Welcome to CryptoLocker — your Telegram password manager.",
    "MENU_HINT": "Choose an action:",
    "ASK_ADD_NAME": "Send a short name for this account (e.g., Gmail, Work VPN).",
    "ASK_ADD_USERNAME": "Send the username for {name}.",
    "ASK_ADD_PASSWORD": "Send the password for {name}.",
    "ADDED_SUCCESS": "Saved ✅ — your credentials for {name} were stored.",
    "ASK_SEARCH": "Send the name to search for.",
    "NO_MATCH": "No entries found for '{q}'.",
    "SHOW_HEADER": "Your saved accounts:",
    "NO_ACCOUNTS": "You have not saved any accounts yet.",
    "INVALID_NAME": "Name must be between 1 and 64 characters.",
    "INVALID_CREDENTIAL": "Value must be between 1 and 512 characters.",
    "PROMPT_REMOVE": "Select an account to remove.",
    "PROMPT_EDIT": "Select an account to edit.",
    "PROMPT_SHOW": "Select an account to display.",
    "SEARCH_RESULTS": "Select a result:",
    "ASK_NEW_USERNAME": "Send the new username for {name}.",
    "ASK_NEW_PASSWORD": "Send the new password for {name}.",
    "BTN_EDIT_USERNAME": "Change username",
    "BTN_EDIT_PASSWORD": "Change password",
    "ASK_REMOVE_CONFIRM": "Are you sure you want to permanently delete {name}? This cannot be undone.",
    "REMOVED_SUCCESS": "{name} removed.",
    "EDIT_CHOOSE_FIELD": "Do you want to change the username or password for {name}?",
    "EDIT_SUCCESS": "{field} updated for {name}.",
    "LANG_CHANGED_EN": "Language switched to English.",
    "LANG_CHANGED_FA": "Language switched to Persian.",
    "NOT_ADMIN": "You are not the bot admin.",
    "ERR_GENERIC": "Something went wrong. Please try again.",
    "BTN_ADD": "Add",
    "BTN_SEARCH": "Search",
    "BTN_REMOVE": "Remove",
    "BTN_EDIT": "Edit",
    "BTN_SHOW": "Show",
    "BTN_YES_DELETE": "Yes, delete",
    "BTN_NO_CANCEL": "No, cancel",
    "BTN_CLOSE": "Close",
}

LANG_FA = {
    "WELCOME": "خوش اومدی به CryptoLocker — مدیر پسورد تو در تلگرام.",
    "MENU_HINT": "یکی از گزینه‌ها را انتخاب کن:",
    "ASK_ADD_NAME": "یک نام کوتاه برای اکانت بفرست (مثال: Gmail، VPN کار).",
    "ASK_ADD_USERNAME": "نام کاربری برای {name} را ارسال کن.",
    "ASK_ADD_PASSWORD": "رمز عبور برای {name} را ارسال کن.",
    "ADDED_SUCCESS": "ذخیره شد ✅ — اطلاعات {name} ثبت شد.",
    "ASK_SEARCH": "اسم مورد نظر برای جستجو را بفرست.",
    "NO_MATCH": "موردی با '{q}' پیدا نشد.",
    "SHOW_HEADER": "اکانت‌های ذخیره‌شده:",
    "NO_ACCOUNTS": "هنوز هیچ اکانتی ذخیره نکرده‌ای.",
    "INVALID_NAME": "نام باید بین ۱ تا ۶۴ کاراکتر باشد.",
    "INVALID_CREDENTIAL": "مقدار باید بین ۱ تا ۵۱۲ کاراکتر باشد.",
    "PROMPT_REMOVE": "اکانتی که می‌خوای حذف کنی را انتخاب کن.",
    "PROMPT_EDIT": "اکانتی که می‌خوای ویرایش کنی را انتخاب کن.",
    "PROMPT_SHOW": "اکانتی که می‌خوای ببینی را انتخاب کن.",
    "SEARCH_RESULTS": "یکی از نتایج را انتخاب کن:",
    "ASK_NEW_USERNAME": "نام‌کاربری جدید برای {name} را بفرست.",
    "ASK_NEW_PASSWORD": "رمز جدید برای {name} را بفرست.",
    "BTN_EDIT_USERNAME": "تغییر نام‌کاربری",
    "BTN_EDIT_PASSWORD": "تغییر رمز",
    "ASK_REMOVE_CONFIRM": "مطمئنی می‌خوای {name} را حذف کنی؟ این عمل قابل بازگشت نیست.",
    "REMOVED_SUCCESS": "{name} حذف شد.",
    "EDIT_CHOOSE_FIELD": "می‌خوای نام‌کاربری را تغییر بدی یا رمز را؟",
    "EDIT_SUCCESS": "{field} برای {name} به‌روز شد.",
    "LANG_CHANGED_EN": "زبان به انگلیسی تغییر کرد.",
    "LANG_CHANGED_FA": "زبان به فارسی تغییر کرد.",
    "NOT_ADMIN": "تو ادمین بات نیستی.",
    "ERR_GENERIC": "مشکلی پیش اومد. دوباره تلاش کن.",
    "BTN_ADD": "افزودن",
    "BTN_SEARCH": "جستجو",
    "BTN_REMOVE": "حذف",
    "BTN_EDIT": "ویرایش",
    "BTN_SHOW": "نمایش",
    "BTN_YES_DELETE": "بله، حذف شود",
    "BTN_NO_CANCEL": "خیر، انصراف",
    "BTN_CLOSE": "بستن",
}

STRINGS: Dict[str, Dict[str, str]] = {
    "en": LANG_EN,
    "fa": LANG_FA,
}

SUPPORTED_LANGS = tuple(STRINGS.keys())
DEFAULT_LANG = "en"


def t(lang: str, key: str, /, **kwargs) -> str:
    """Translate *key* into *lang*, falling back to English."""
    table = STRINGS.get(lang, STRINGS[DEFAULT_LANG])
    template = table.get(key) or STRINGS[DEFAULT_LANG].get(key) or key
    return template.format(**kwargs)


__all__ = ["t", "SUPPORTED_LANGS", "DEFAULT_LANG", "STRINGS"]
