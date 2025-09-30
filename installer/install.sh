#!/usr/bin/env bash
# One-line installer usage:
#   curl -sSL https://raw.githubusercontent.com/zZedix/CryptoLockerBot/main/installer/install.sh | bash
set -euo pipefail

if [[ $(uname -s) != "Linux" ]]; then
  echo "This installer currently supports Ubuntu Linux." >&2
  exit 1
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_DIR=$(cd "${SCRIPT_DIR}/.." && pwd)
USER_NAME=$(whoami)
USER_HOME=$(eval echo "~${USER_NAME}")
CONFIG_DIR="${USER_HOME}/.cryptolocker"
CONFIG_FILE="${CONFIG_DIR}/config.env"
SALT_FILE="${CONFIG_DIR}/salt"
DB_PATH="${CONFIG_DIR}/cryptolocker.db"
VENV_PATH="${PROJECT_DIR}/.venv"
PYTHON_BIN="${VENV_PATH}/bin/python"

read -r -p "Enter Telegram BOT TOKEN:" BOT_TOKEN
while [[ ! ${BOT_TOKEN} =~ ^[0-9A-Za-z:-]+$ ]]; do
  echo "Invalid token format. Try again."
  read -r -p "Enter Telegram BOT TOKEN:" BOT_TOKEN
done

read -r -p "Enter numeric ADMIN TELEGRAM ID:" ADMIN_ID
while [[ ! ${ADMIN_ID} =~ ^[0-9]+$ ]]; do
  echo "Admin ID must be numeric. Try again."
  read -r -p "Enter numeric ADMIN TELEGRAM ID:" ADMIN_ID
done

PASS_MATCH=false
while [[ ${PASS_MATCH} == false ]]; do
  read -r -s -p "Enter encryption passphrase (do NOT forget this; used to encrypt user data):" PASSPHRASE
  printf "\n"
  read -r -s -p "Confirm passphrase:" PASS_CONFIRM
  printf "\n"
  if [[ -z ${PASSPHRASE} ]]; then
    echo "Passphrase cannot be empty."
  elif [[ ${PASSPHRASE} != ${PASS_CONFIRM} ]]; then
    echo "Passphrases do not match. Try again."
  else
    PASS_MATCH=true
  fi
  unset PASS_CONFIRM
done

sudo apt-get update
sudo apt-get install -y software-properties-common
if ! command -v python3.12 >/dev/null 2>&1; then
  sudo add-apt-repository -y ppa:deadsnakes/ppa
  sudo apt-get update
fi
sudo apt-get install -y python3.12 python3.12-venv python3.12-dev build-essential pkg-config libffi-dev

if [[ ! -d ${VENV_PATH} ]]; then
  python3.12 -m venv "${VENV_PATH}"
fi
"${VENV_PATH}/bin/pip" install --upgrade pip
"${VENV_PATH}/bin/pip" install -r "${PROJECT_DIR}/requirements.txt"

umask 077
mkdir -p "${CONFIG_DIR}"
chmod 700 "${CONFIG_DIR}"

if [[ ! -f ${SALT_FILE} ]]; then
  CRYPTOLOCKER_SALT_PATH="${SALT_FILE}" "${PYTHON_BIN}" - <<'PY'
import os
import secrets
from pathlib import Path
path = Path(os.environ['CRYPTOLOCKER_SALT_PATH'])
path.parent.mkdir(parents=True, exist_ok=True)
path.write_bytes(secrets.token_bytes(16))
os.chmod(path, 0o600)
PY
else
  chmod 600 "${SALT_FILE}"
fi

cat > "${CONFIG_FILE}" <<EOF_CONF
BOT_TOKEN=${BOT_TOKEN}
ADMIN_TELEGRAM_ID=${ADMIN_ID}
KEY_DERIVATION_SALT_FILE=~/.cryptolocker/salt
DB_PATH=~/.cryptolocker/cryptolocker.db
ENCRYPTION_PASSPHRASE=${PASSPHRASE}
EOF_CONF
chmod 600 "${CONFIG_FILE}"
unset PASSPHRASE

CRYPTOLOCKER_DB_PATH="${DB_PATH}" CRYPTOLOCKER_CONFIG_DIR="${CONFIG_DIR}" PYTHONPATH="${PROJECT_DIR}" "${PYTHON_BIN}" - <<'PY'
import asyncio
import os
from db import Database

config_dir = os.environ["CRYPTOLOCKER_CONFIG_DIR"]
os.makedirs(config_dir, exist_ok=True)
db_path = os.environ["CRYPTOLOCKER_DB_PATH"]

db = Database(db_path)
asyncio.run(db.init())
PY

SERVICE_FILE=/etc/systemd/system/cryptolocker.service
sudo tee "${SERVICE_FILE}" >/dev/null <<EOF_SERVICE
[Unit]
Description=CryptoLockerBot service
After=network-online.target

[Service]
Type=simple
User=${USER_NAME}
EnvironmentFile=${CONFIG_FILE}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${VENV_PATH}/bin/python ${PROJECT_DIR}/bot.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF_SERVICE

sudo systemctl daemon-reload
sudo systemctl enable cryptolocker

echo "Installation complete. Start the bot with: sudo systemctl start cryptolocker"
echo "Follow logs: journalctl -u cryptolocker -f"
