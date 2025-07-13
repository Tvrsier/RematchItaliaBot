import asyncio

from discord import Guild, Member
from discord.ext import commands
from typing import TYPE_CHECKING
from app.logger import logger
from lib.db import schemes

if TYPE_CHECKING:
    from app.bot import RematchItaliaBot



class DBInitCog(commands.Cog):
    def __init__(self, bot: "RematchItaliaBot"):
        self.bot = bot

    @staticmethod
    async def register_guild(guild: Guild, fetch_members: bool):
        db_guild, created = await schemes.add_or_get_guild(guild)
        if not db_guild:
            logger.error(f"Failed to register guild {guild.id} ({guild.name}) in the database.")
            return
        if created:
            logger.info(f"Registered guild {guild.id} ({guild.name}) in the database.")
        members: list[Member]
        if fetch_members:
            members = await guild.fetch_members(limit=None).flatten()
        else:
            members = guild.members
        for member in members:
            if member.bot:
                continue
            member_db, guild_member_db, created = await schemes.add_or_get_member(member)
            if not member_db:
                logger.error(f"Failed to register member {member.id} ({member.name}) in the database.")
                continue
            if created:
                logger.info(f"Registered member {member.id} ({member.name}) in the database.")

    @commands.command(name="sync_guild", hidden=True)
    @commands.is_owner()
    async def sync_guild(self, ctx: commands.Context):
        await ctx.trigger_typing()
        await ctx.message.delete()
        try:
            cached = len(ctx.guild.members)
            total = ctx.guild.member_count
            logger.debug(f"Guild {ctx.guild.name}: cache={cached} / total={total}")

            fetch_members = self.check_fetch_members(cached, total)
            await self.register_guild(ctx.guild, fetch_members)
            await ctx.send("✅ Sincronizzazione della guild completata con successo!")
        except Exception as e:
            logger.exception("Error in sync_guild", exc_info=e, stack_info=True)
            await ctx.send("❌ Si è verificato un errore durante la sincronizzazione della guild.")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild):
        logger.info(f"Bot joined guild {guild.id} ({guild.name}).")
        fetch_members = False
        await asyncio.sleep(3)
        cached = len(guild.members)
        total = guild.member_count
        logger.debug(f"Guild {guild.name}: cache={cached} / total={total}")

        fetch_members = self.check_fetch_members(cached, total)

        await self.register_guild(guild, fetch_members)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.__ready__:
            self.bot.cogs_ready.ready_up("db_init_cog")

    @staticmethod
    def check_fetch_members(cached, total) -> bool:
        if cached < total * 0.8:
            logger.warning(f"Member cache contains only the {int(cached/total*100)}%, members will be fetched")
            return True
        return False


def setup(bot: "RematchItaliaBot"):
    bot.add_cog(DBInitCog(bot))
    logger.debug("DBInitCog loaded successfully.")

