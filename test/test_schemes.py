import dotenv
dotenv.load_dotenv("../.env")

import unittest
from types import SimpleNamespace

from tortoise import Tortoise

from app.lib.db.queries import *


# noinspection PyTypeChecker
class TestSchemes(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await Tortoise.init(
            db_url="sqlite://:memory:",
            modules={"models": ["app.lib.db.schemes"]}
        )
        await Tortoise.generate_schemas()

    async def asyncTearDown(self):
        await Tortoise.close_connections()

    async def test_add_guild_creates_record(self):
        fake_guild = SimpleNamespace(
            id=1234,
            name="TestGuild",
            icon=None,
            owner_id=1111,
        )
        guild = await add_or_get_guild(fake_guild)
        exists = await GuildSchema.exists(guild_id=1234)
        self.assertTrue(exists, "The GuildSchema has been created")

        db = await GuildSchema.get(guild_id=1234)
        self.assertEqual(db.name, "TestGuild")
        self.assertEqual(db.owner_id, 1111)

    # noinspection PyTypeChecker
    async def test_add_member_creates_both_models(self):
        fake_guild = SimpleNamespace(
            id=9999,
            name="G",
            icon=None,
            owner_id=None,
        )

        await add_or_get_guild(fake_guild)

        fake_member = SimpleNamespace(
            id=5555,
            name="User",
            discriminator="user",
            avatar=None,
            bot=False,
            guild=fake_guild,
            joined_at=datetime.datetime.now(datetime.UTC)
        )
        member_db, guild_member_db, created = await add_or_get_member(fake_member)
        self.assertTrue(created, "Member was created")
        self.assertTrue(
            await MemberSchema.exists(discord_id=5555),
            "MemberSchema not found"
        )
        self.assertTrue(
            await GuildMemberSchema.exists(guild_id=9999, discord_id=5555),
            "GuildMemberSchema non trovato"
        )

    # noinspection PyTypeChecker
    async def test_add_command_permission(self):
        fake_guild = SimpleNamespace(
            id=8888,
            name="TestGuild",
            icon=None,
            owner_id=2222,
        )
        await add_or_get_guild(fake_guild)

        command = CommandEnum.SYNC_GUILD
        role_id = 3333

        # Assuming a function to add command permission exists
        await add_command_permission(fake_guild, command, role_id)

        permissions = await get_command_permission(fake_guild, command)
        self.assertIsNotNone(permissions, "Permissions should not be None")

    async def test_add_rank_link(self):
        fake_guild = SimpleNamespace(
            id=8888,
            name="TestGuild",
            icon=None,
            owner_id=2222,
        )
        await add_or_get_guild(fake_guild)
        rank = RankLinkEnum.ORO
        fake_role = SimpleNamespace(
            id=4444,
            name="TestRole"
        )
        rank_db, created = await link_rank(fake_guild, fake_role, rank)
        self.assertTrue(created, "Rank link should be created")
        self.assertTrue(
            await Rank.exists(guild_id=8888, name=rank.name, role_id=4444),
            "RankLinkSchema not found"
        )

    # noinspection PyTypeChecker
    async def test_get_platform_to_update_returns_old_links(self):
        fake_guild = SimpleNamespace(
            id=12345,
            name="GuildForUpdate",
            icon=None,
            owner_id=54321,
        )
        await add_or_get_guild(fake_guild)
        fake_member = SimpleNamespace(
            id=67890,
            name="MemberForUpdate",
            discriminator="0002",
            avatar=None,
            bot=False,
            guild=fake_guild,
            joined_at=datetime.datetime.now(datetime.UTC)
        )
        await add_or_get_member(fake_member)
        member_db = await MemberSchema.get(discord_id=67890)

        # Create two PlatformLinks: one old, one recent
        old_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=45)
        recent_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=10)

        await PlatformLink.create(
            discord_id=member_db,
            platform_id="old_123",
            platform="playstation",
            cached_rank=RankLinkEnum.ORO,
            last_checked=old_time,
            rematch_display_name="OldUser"
        )
        await PlatformLink.create(
            discord_id=member_db,
            platform_id="recent_123",
            platform="playstation",
            cached_rank=RankLinkEnum.ORO,
            last_checked=recent_time,
            rematch_display_name="RecentUser"
        )


        # Only the old one should be returned
        links = await get_platform_to_update()
        platform_ids = [link.platform_id for link in links]
        self.assertIn("old_123", platform_ids)
        self.assertNotIn("recent_123", platform_ids)


if __name__ == '__main__':
    unittest.main()
