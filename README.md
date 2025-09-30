# CryptoLockerBot

CryptoLockerBot is a secure, async Telegram password manager backed by SQLite with end-to-end encryption. Credentials are encrypted with a passphrase-derived key before touching disk, while an ergonomic Telegram UI lets you add, search, edit, remove, and display entries in English or Persian (Farsi).

## Features
- Python 3.12 bot built with `python-telegram-bot` v21 (async Application API).
- Secrets encrypted using PBKDF2-HMAC (SHA256, 240k iterations) + Fernet (`cryptography`).
- SQLite storage with WAL enabled and per-user language preferences (`en` or `fa`).
- Reply keyboard driven UX with inline keyboards for account listings and confirmations.
- Rotating file logs stored in `~/.cryptolocker/cryptolocker.log` (no plaintext passwords are logged).
- Systemd unit & guided installer for Ubuntu deployments.

## Quick Start (Recommended)
Use the installer after hosting it yourself (replace placeholder URL with the raw script location):

```bash
curl -sSL https://example.com/cryptolocker/install.sh | bash
```

The script will:
1. Prompt for the Telegram bot token, admin user ID, and encryption passphrase.
2. Install Python 3.12 + build tooling, create a project virtualenv, and install dependencies.
3. Create `~/.cryptolocker/` (chmod `700`), generate a random salt, and write `config.env` (chmod `600`).
4. Initialize the SQLite database, write `/etc/systemd/system/cryptolocker.service`, and enable the service.

After installation:

```bash
sudo systemctl start cryptolocker
journalctl -u cryptolocker -f
```

> ⚠️ **Keep your passphrase, `salt`, and `config.env` safe. Losing any of them makes stored data unrecoverable.**

## Manual Setup
1. Install Python 3.12 and system dependencies.
2. Clone this repository and create a virtual environment:
   ```bash
   python3.12 -m venv .venv
   .venv/bin/pip install --upgrade pip
   .venv/bin/pip install -r requirements.txt
   ```
3. Create `~/.cryptolocker/` (chmod `700`) and generate a random 16-byte salt at `~/.cryptolocker/salt` (chmod `600`).
4. Copy `.env.example` to either `.env` in the project root or `~/.cryptolocker/config.env`, then populate:
   - `BOT_TOKEN`
   - `ADMIN_TELEGRAM_ID`
   - `KEY_DERIVATION_SALT_FILE=~/.cryptolocker/salt`
   - `DB_PATH=~/.cryptolocker/cryptolocker.db`
   - `ENCRYPTION_PASSPHRASE=<strong passphrase>`
5. Initialize the database:
   ```bash
   PYTHONPATH=$(pwd) python3.12 - <<'PY'
   import asyncio
   from db import Database
   db = Database("~/.cryptolocker/cryptolocker.db")
   asyncio.run(db.init())
   PY
   ```
6. Run the bot:
   ```bash
   .venv/bin/python bot.py
   ```

## Telegram Commands & UX
- `/start`, `/menu` – show localized welcome and keyboard (`Add`, `Search`, `Remove`, `Edit`, `Show`).
- `/lang en`, `/lang fa` – switch language (persisted per-user).
- Inline flows for listing, editing (username/password), deleting, and showing credentials with a close button to remove the message.

## Testing
Unit tests cover encryption and database primitives using stdlib `unittest`:
```bash
python -m unittest discover tests
```

## Backup & Restore
Back up the following together:
- `~/.cryptolocker/cryptolocker.db`
- `~/.cryptolocker/salt`
- `~/.cryptolocker/config.env`

Restore them with original permissions (`config.env` & `salt` → `600`, directory → `700`). Without the original passphrase *and* salt, decryption is impossible.

## Logs
Logs write to `~/.cryptolocker/cryptolocker.log` with rotation. They include metadata only (no plaintext usernames or passwords). Tail with:
```bash
journalctl -u cryptolocker -f  # systemd
# or
tail -f ~/.cryptolocker/cryptolocker.log
```

## Contributing
- Keep new strings in `i18n.py` translated for both English and Persian.
- Avoid logging sensitive data.
- For additional flows, extend the `StateManager` to keep interactions predictable.
