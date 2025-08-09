import asyncio
import datetime
import time
from collections import defaultdict

from discord import Cog, Colour, Embed, Member, Interaction
from typing import TYPE_CHECKING
from discord.ext import commands
from discord.ext.commands import CooldownMapping

from app.logger import logger
from app.lib.extension_context import RematchApplicationContext as ApplicationContext
from lib.db import queries

if TYPE_CHECKING:
    from app.bot import RematchItaliaBot



_LAST_CHECK: dict[tuple[int, int], float] = {}
_CHECK_TTL = 30.0

_MEMBER_LOCKS: defaultdict[tuple[int, int], asyncio.Lock] = defaultdict(asyncio.Lock)


class GeneralCog(Cog):
    def __init__(self, bot: "RematchItaliaBot"):
        self.bot = bot


    @commands.slash_command(name="ping", description="Controlla la latenza del bot.")
    async def ping(self, actx: ApplicationContext):
        """
        This command checks the bot's latency.
        It replies with the current latency in milliseconds.
        """
        latency = round(self.bot.latency * 1000)
        embed = Embed(
            title="🏓 Pong",
            description=f"Latency: {latency} ms",
            colour=Colour.blue(),
            timestamp=datetime.datetime.now(datetime.UTC)
        )
        #await actx.respond(f"🏓 Pong! Latency: {latency} ms")
        await actx.respond(embed=embed)

    @commands.slash_command(name="feedback", description="Invia un feedback agli sviluppatori.",
                            cooldown=CooldownMapping.from_cooldown(1, 21600, commands.BucketType.user))
    async def feedback(self, actx: ApplicationContext, message: str):
        """
        This command allows users to send feedback to the bot developers.
        It sends a message to the bot's log channel.
        """
        owner = self.bot.get_user(self.bot.owner_id)

        if owner is None:
            try:
                owner = await self.bot.fetch_user(self.bot.owner_id)
            except Exception as e:
                logger.error(f"Failed to fetch owner user: {e}", exc_info=True)
                await actx.respond("❌ Non sono riuscito ad inviare il tuo feedback. Per favore, riprova più tardi.")
                return

        embed = Embed(
            title=f"Feedback from {actx.author.name}#{actx.author.discriminator}",
            description=message,
            colour=Colour.green(),
            timestamp=datetime.datetime.now(datetime.UTC)
        )
        embed.set_author(name=actx.author, icon_url=actx.author.display_avatar.url)
        embed.set_footer(text=f"© Rematch Italia. All rights reserved.")

        await owner.send(
            embed=embed,
            allowed_mentions=None  # Prevents pinging the owner
        )
        await actx.respond("✅ Il tuo feedback è stato inviato. Grazie per il supporto!")

    @commands.slash_command(name="show_guild_roles", description="Mostra i ruoli della guild.")
    @commands.check_any(
        commands.has_permissions(administrator=True),
        commands.is_owner()
    )
    async def show_guild_roles(self, actx: ApplicationContext):
        """
        This command shows the roles of the guild.
        It replies with a list of roles in the guild.
        """
        guild = actx.guild
        if not guild:
            await actx.respond("❌ Questo comando non può essere usato nei messaggi privati.")
            return

        roles = [role.name for role in guild.roles if role.name != "@everyone"]
        if not roles:
            await actx.respond("⚠️ Non ci sono ruoli nella guild.")
            return

        roles_list = "\n".join(roles)
        await actx.respond(f"**Ruoli della Guild:**\n{roles_list}")

    # noinspection PyMethodMayBeStatic
    async def ensure_member_registered(self, member: Member) -> None:
        """
        Ensure that a member is registered in the bot's database.
        :param member:
            The member to ensure is registered.
        :return:
            None
        """
        try:
            member_db = await queries.get_member(member)
            if member_db is None:
                await queries.add_or_get_member(member)
        except Exception as e:
            logger.error(f"Failed to ensure member registration: {e}", exc_info=True)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.__ready__:
            self.bot.cogs_ready.ready_up("general")
            self.bot.__ready__ = True

    @Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        key = None
        try:
            if not interaction.guild or not interaction.user:
                return

            if getattr(interaction.user, "bot", False):
                return

            key = (interaction.guild.id, interaction.user.id)

            now = time.time()
            last = _LAST_CHECK.get(key, 0.0)
            if (now - last) < _CHECK_TTL:
                return

            member = interaction.guild.get_member(interaction.user.id)
            if member is None:
                try:
                    member = await interaction.guild.fetch_member(interaction.user.id)
                except Exception as e:
                    logger.error(f"Failed to fetch member {interaction.user.id} in guild {interaction.guild.id}: {e}", exc_info=True)
                    return

            lock = _MEMBER_LOCKS[key]
            async with lock:
                now2 = time.time()
                last2 = _LAST_CHECK.get(key, 0.0)
                if (now2 -last2) < _CHECK_TTL:
                    return

                await self.ensure_member_registered(member)
                _LAST_CHECK[key] = now2
        except Exception as e:
            logger.error(f"Error in on_interaction for {interaction.user.id} in guild "
                         f"{interaction.guild.id}: {e}", exc_info=True)
        finally:
            # Ensure the lock is released even if an error occurs
            if key in _MEMBER_LOCKS:
                del _MEMBER_LOCKS[key]
            else:
                logger.warning(f"Lock for {key} not found in _MEMBER_LOCKS.")


def setup(bot: "RematchItaliaBot"):
    bot.add_cog(GeneralCog(bot))
    logger.debug("GeneralCog loaded successfully.")