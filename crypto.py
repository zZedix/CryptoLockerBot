"""Encryption helpers for CryptoLockerBot.

This module derives per-installation encryption keys from a user-supplied
passphrase and salt, then offers convenience wrappers for encrypting and
decrypting sensitive values before they are persisted to disk.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_LOGGER = logging.getLogger(__name__)

DEFAULT_ITERATIONS: Final[int] = 240_000
_KEY_LENGTH: Final[int] = 32


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""


@dataclass(frozen=True)
class EncryptionContext:
    """Immutable container for reusable encryption parameters."""

    cipher: Fernet
    iterations: int = DEFAULT_ITERATIONS


def _ensure_bytes(data: bytes | str, *, field: str) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return data.encode("utf-8")
    raise TypeError(f"{field} must be bytes or str, got {type(data)!r}")


def load_salt(salt_path: str | Path) -> bytes:
    """Load salt bytes from disk.

    Parameters
    ----------
    salt_path: str | Path
        Path to the salt file created during installation.
    """
    path = Path(salt_path).expanduser()
    try:
        data = path.read_bytes()
    except FileNotFoundError as exc:
        raise EncryptionError(f"Salt file not found: {path}") from exc
    if len(data) < 16:
        raise EncryptionError("Salt file must contain at least 16 random bytes")
    return data


def derive_key(passphrase: str, salt: bytes, *, iterations: int = DEFAULT_ITERATIONS) -> bytes:
    """Derive a Fernet-compatible key using PBKDF2-HMAC(SHA256)."""
    if not passphrase:
        raise EncryptionError("Passphrase is required to derive encryption key")
    passphrase_bytes = passphrase.encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LENGTH,
        salt=salt,
        iterations=iterations,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase_bytes))
    return key


def build_context(passphrase: str, salt_path: str | Path, *, iterations: int = DEFAULT_ITERATIONS) -> EncryptionContext:
    """Create an `EncryptionContext` from configuration values."""
    salt = load_salt(salt_path)
    key = derive_key(passphrase, salt, iterations=iterations)
    return EncryptionContext(cipher=Fernet(key), iterations=iterations)


def encrypt(plaintext: str | bytes, context: EncryptionContext) -> bytes:
    """Encrypt plaintext, returning ciphertext bytes for storage."""
    try:
        return context.cipher.encrypt(_ensure_bytes(plaintext, field="plaintext"))
    except Exception as exc:  # pragma: no cover - cryptography internal errors are rare
        _LOGGER.error("Encryption failure: %s", exc)
        raise EncryptionError("Unable to encrypt data") from exc


def decrypt(ciphertext: bytes | str, context: EncryptionContext) -> str:
    """Decrypt ciphertext bytes and return the UTF-8 plaintext."""
    try:
        raw = context.cipher.decrypt(_ensure_bytes(ciphertext, field="ciphertext"))
        return raw.decode("utf-8")
    except InvalidToken as exc:
        _LOGGER.warning("Invalid encryption token encountered")
        raise EncryptionError("Invalid encryption token") from exc
    except Exception as exc:  # pragma: no cover - cryptography internal errors are rare
        _LOGGER.error("Decryption failure: %s", exc)
        raise EncryptionError("Unable to decrypt data") from exc


__all__ = [
    "EncryptionContext",
    "EncryptionError",
    "DEFAULT_ITERATIONS",
    "build_context",
    "derive_key",
    "encrypt",
    "decrypt",
    "load_salt",
]
