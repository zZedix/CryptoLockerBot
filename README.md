# 🔐 CryptoLockerBot

[![GitHub](https://img.shields.io/badge/GitHub-zZedix%2FCryptoLockerBot-blue?style=flat-square&logo=github)](https://github.com/zZedix/CryptoLockerBot)
[![Python](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square&logo=python)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?style=flat-square&logo=telegram)](https://telegram.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

> **A secure, async Telegram password manager with end-to-end encryption**

CryptoLockerBot is a powerful and secure password management solution that runs entirely within Telegram. Your credentials are encrypted with a passphrase-derived key before touching disk, while an intuitive Telegram UI lets you add, search, edit, remove, and display entries in both English and Persian (Farsi).

## ✨ Features

- 🔒 **End-to-End Encryption**: PBKDF2-HMAC (SHA256, 240k iterations) + Fernet encryption
- 🐍 **Modern Python**: Built with Python 3.12 and `python-telegram-bot` v21 (async Application API)
- 💾 **SQLite Storage**: WAL mode enabled with per-user language preferences (`en` or `fa`)
- 🎨 **Intuitive UI**: Reply keyboard driven UX with inline keyboards for seamless navigation
- 📝 **Comprehensive Logging**: Rotating file logs (no plaintext passwords logged)
- 🚀 **Easy Deployment**: Systemd unit & guided installer for Ubuntu deployments
- 🌍 **Multilingual**: Full support for English and Persian languages

## 🚀 Quick Start (Recommended)

### One-Line Installation

```bash
curl -sSL https://raw.githubusercontent.com/zZedix/CryptoLockerBot/main/installer/install.sh | bash
```

The installer will:
1. 📋 Prompt for the Telegram bot token, admin user ID, and encryption passphrase
2. 🛠️ Install Python 3.12 + build tooling, create a project virtualenv, and install dependencies
3. 🔐 Create `~/.cryptolocker/` (chmod `700`), generate a random salt, and write `config.env` (chmod `600`)
4. 🗄️ Initialize the SQLite database, write systemd service, and enable the service

### After Installation

```bash
# Start the bot
sudo systemctl start cryptolocker

# Follow logs
journalctl -u cryptolocker -f
```

> ⚠️ **Security Warning**: Keep your passphrase, `salt`, and `config.env` safe. Losing any of them makes stored data unrecoverable.

## 🛠️ Manual Setup

### Prerequisites
- Python 3.12+
- Ubuntu Linux (for systemd service)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/zZedix/CryptoLockerBot.git
   cd CryptoLockerBot
   ```

2. **Create virtual environment**
   ```bash
   python3.12 -m venv .venv
   .venv/bin/pip install --upgrade pip
   .venv/bin/pip install -r requirements.txt
   ```

3. **Set up configuration**
   ```bash
   # Create config directory
   mkdir -p ~/.cryptolocker
   chmod 700 ~/.cryptolocker
   
   # Generate random salt
   python3.12 -c "import secrets; open('~/.cryptolocker/salt', 'wb').write(secrets.token_bytes(16))"
   chmod 600 ~/.cryptolocker/salt
   ```

4. **Configure environment**
   ```bash
   cp .env.example ~/.cryptolocker/config.env
   # Edit ~/.cryptolocker/config.env with your settings
   ```

5. **Initialize database**
   ```bash
   PYTHONPATH=$(pwd) python3.12 -c "
   import asyncio
   from db import Database
   db = Database('~/.cryptolocker/cryptolocker.db')
   asyncio.run(db.init())
   "
   ```

6. **Run the bot**
   ```bash
   .venv/bin/python bot.py
   ```

## 📱 Telegram Commands & Usage

### Basic Commands
- `/start`, `/menu` – Show welcome message and main keyboard
- `/lang en`, `/lang fa` – Switch between English and Persian

### Main Functions
- **➕ Add**: Add new credentials with name, username, and password
- **🔍 Search**: Search through your stored credentials
- **✏️ Edit**: Modify existing usernames or passwords
- **🗑️ Remove**: Delete credentials with confirmation
- **👁️ Show**: Display credentials with secure inline buttons

### Security Features
- All credentials are encrypted before storage
- Inline buttons for secure credential display
- Automatic message deletion after viewing
- No plaintext logging of sensitive data

## 🧪 Testing

Run the comprehensive test suite:

```bash
python -m unittest discover tests
```

Tests cover:
- Encryption/decryption functionality
- Database operations
- User state management
- Error handling

## 💾 Backup & Restore

### Backup These Files Together
- `~/.cryptolocker/cryptolocker.db` (encrypted database)
- `~/.cryptolocker/salt` (encryption salt)
- `~/.cryptolocker/config.env` (configuration)

### Restore Process
1. Restore files with original permissions:
   - `config.env` & `salt` → `600`
   - Directory → `700`
2. Start the service: `sudo systemctl start cryptolocker`

> **Important**: Without the original passphrase AND salt, decryption is impossible.

## 📊 Monitoring & Logs

### Systemd Logs
```bash
# Follow real-time logs
journalctl -u cryptolocker -f

# View recent logs
journalctl -u cryptolocker --since "1 hour ago"
```

### File Logs
```bash
# Follow log file
tail -f ~/.cryptolocker/cryptolocker.log

# View recent entries
tail -n 100 ~/.cryptolocker/cryptolocker.log
```

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

- 🌍 Keep new strings in `i18n.py` translated for both English and Persian
- 🔒 Never log sensitive data (usernames, passwords, etc.)
- 🏗️ Extend the `StateManager` for new interaction flows
- ✅ Add tests for new functionality
- 📝 Update documentation for new features

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Repository**: [https://github.com/zZedix/CryptoLockerBot](https://github.com/zZedix/CryptoLockerBot)
- **Issues**: [Report a bug or request a feature](https://github.com/zZedix/CryptoLockerBot/issues)
- **Discussions**: [Community discussions](https://github.com/zZedix/CryptoLockerBot/discussions)

---

<div align="center">
  <p>Made with ❤️ for secure password management</p>
  <p>⭐ Star this repository if you find it useful!</p>
</div>