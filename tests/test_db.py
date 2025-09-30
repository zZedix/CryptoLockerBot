import asyncio
import os
import tempfile
import unittest

from db import Database


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "cryptolocker.db")
        self.database = Database(self.db_path)
        await self.database.init()
        self.user_id = 4242
        await self.database.ensure_user(self.user_id)

    async def asyncTearDown(self) -> None:
        self.temp_dir.cleanup()

    async def test_account_crud_flow(self) -> None:
        username = b"user"
        password = b"pass"
        account_name = "Email"

        account_id = await self.database.add_account(self.user_id, account_name, username, password)
        self.assertIsInstance(account_id, int)

        accounts = await self.database.list_accounts(self.user_id)
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].name, account_name)

        search_results = await self.database.search_accounts(self.user_id, "mai")
        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0].id, account_id)

        account = await self.database.get_account(account_id, self.user_id)
        self.assertIsNotNone(account)
        self.assertEqual(account.name, account_name)

        updated = await self.database.update_account_field(account_id, self.user_id, field="password", value=b"newpass")
        self.assertTrue(updated)

        deleted = await self.database.delete_account(account_id, self.user_id)
        self.assertTrue(deleted)
        remaining = await self.database.list_accounts(self.user_id)
        self.assertEqual(len(remaining), 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
