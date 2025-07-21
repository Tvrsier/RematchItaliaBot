import unittest

from app.lib.db import DatabaseManager


class TestDatabaseManager(unittest.IsolatedAsyncioTestCase):
    db_url = "sqlite://../data/rematch_italia.db"
    models = {"models": ["app.lib.db.schemes"]}

    async def asyncSetUp(self):
        self.db_manager = DatabaseManager(
            db_url=self.db_url,
            modules=self.models,
            generate_schemas=False
        )
        await self.db_manager.connect()

    async def asyncTearDown(self):
        await self.db_manager.close()

    async def test_async_with(self):
        async with DatabaseManager(
                db_url=self.db_url,
                modules=self.models,
                generate_schemas=False
        ) as db_manager:
            self.assertTrue(db_manager._initialized)
        self.assertFalse(self.db_manager._initialized)
