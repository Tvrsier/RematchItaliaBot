import datetime
import unittest
from types import SimpleNamespace

from tortoise import Tortoise

from app.lib.db.schemes import add_guild, GuildSchema, add_member, MemberSchema, GuildMemberSchema


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
        guild = await add_guild(fake_guild)
        exists = await GuildSchema.exists(guild_id=1234)
        self.assertTrue(exists, "The GuildSchema has been created")

        db = await GuildSchema.get(guild_id=1234)
        self.assertEqual(db.name, "TestGuild")
        self.assertEqual(db.owner_id, 1111)

    async def test_add_member_creates_both_models(self):
        fake_guild = SimpleNamespace(
            id=9999,
            name="G",
            icon=None,
            owner_id=None,
        )

        await add_guild(fake_guild)

        fake_member = SimpleNamespace(
            id=5555,
            name="User",
            discriminator="user",
            avatar=None,
            bot=False,
            guild = fake_guild,
            joined_at = datetime.datetime.now(datetime.UTC)
        )
        member_db, guild_member_db, created = await add_member(fake_member)
        self.assertTrue(created, "Member was created")
        self.assertTrue(
            await MemberSchema.exists(discord_id=5555),
            "MemberSchema not found"
        )
        self.assertTrue(
            await GuildMemberSchema.exists(guild_id=9999, discord_id=5555),
            "GuildMemberSchema non trovato"
        )


if __name__ == '__main__':
    unittest.main()
