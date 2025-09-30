"""Asynchronous SQLite helpers for CryptoLockerBot."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

import aiosqlite

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    lang TEXT CHECK(lang IN ('en','fa')) NOT NULL DEFAULT 'en'
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    username BLOB NOT NULL,
    password BLOB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY(owner_id) REFERENCES users(telegram_id) ON DELETE CASCADE
);
"""


@dataclass(slots=True)
class AccountSummary:
    id: int
    name: str


@dataclass(slots=True)
class Account:
    id: int
    owner_id: int
    name: str
    username: bytes
    password: bytes
    created_at: str
    updated_at: str


class Database:
    """High-level wrapper around the SQLite database."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(Path(db_path).expanduser())
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def init(self) -> None:
        """Initialize schema exactly once."""
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            async with aiosqlite.connect(self.db_path) as db:
                await db.executescript(SCHEMA)
                await db.commit()
            self._initialized = True

    async def _connect(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        return conn

    async def ensure_user(self, telegram_id: int) -> None:
        async with await self._connect() as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
                (telegram_id,),
            )
            await db.commit()

    async def get_user_lang(self, telegram_id: int) -> str:
        async with await self._connect() as db:
            async with db.execute(
                "SELECT lang FROM users WHERE telegram_id=?",
                (telegram_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return row["lang"] if row else "en"

    async def set_user_lang(self, telegram_id: int, lang: str) -> None:
        async with await self._connect() as db:
            await db.execute(
                "UPDATE users SET lang=? WHERE telegram_id=?",
                (lang, telegram_id),
            )
            await db.commit()

    async def add_account(self, owner_id: int, name: str, username: bytes, password: bytes) -> int:
        now = datetime.utcnow().isoformat(timespec="seconds")
        async with await self._connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO accounts (owner_id, name, username, password, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (owner_id, name, username, password, now, now),
            )
            await db.commit()
            return cursor.lastrowid

    async def list_accounts(self, owner_id: int) -> List[AccountSummary]:
        async with await self._connect() as db:
            async with db.execute(
                "SELECT id, name FROM accounts WHERE owner_id=? ORDER BY name",
                (owner_id,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [AccountSummary(id=row["id"], name=row["name"]) for row in rows]

    async def search_accounts(self, owner_id: int, query: str) -> List[AccountSummary]:
        pattern = f"%{query}%"
        async with await self._connect() as db:
            async with db.execute(
                """
                SELECT id, name FROM accounts
                WHERE owner_id=? AND LOWER(name) LIKE LOWER(?)
                ORDER BY name
                """,
                (owner_id, pattern),
            ) as cursor:
                rows = await cursor.fetchall()
        return [AccountSummary(id=row["id"], name=row["name"]) for row in rows]

    async def get_account(self, account_id: int, owner_id: int) -> Optional[Account]:
        async with await self._connect() as db:
            async with db.execute(
                """
                SELECT id, owner_id, name, username, password, created_at, updated_at
                FROM accounts WHERE id=? AND owner_id=?
                """,
                (account_id, owner_id),
            ) as cursor:
                row = await cursor.fetchone()
        if row is None:
            return None
        return Account(
            id=row["id"],
            owner_id=row["owner_id"],
            name=row["name"],
            username=row["username"],
            password=row["password"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def delete_account(self, account_id: int, owner_id: int) -> bool:
        async with await self._connect() as db:
            cursor = await db.execute(
                "DELETE FROM accounts WHERE id=? AND owner_id=?",
                (account_id, owner_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def update_account_field(self, account_id: int, owner_id: int, *, field: str, value: bytes) -> bool:
        if field not in {"username", "password"}:
            raise ValueError("Unsupported field for update")
        now = datetime.utcnow().isoformat(timespec="seconds")
        async with await self._connect() as db:
            cursor = await db.execute(
                f"UPDATE accounts SET {field}=?, updated_at=? WHERE id=? AND owner_id=?",
                (value, now, account_id, owner_id),
            )
            await db.commit()
            return cursor.rowcount > 0


__all__ = [
    "Account",
    "AccountSummary",
    "Database",
]
