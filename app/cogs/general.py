import datetime

from discord import Cog, Colour, Embed
from typing import TYPE_CHECKING
from discord.ext import commands

from app.logger import logger
from app.lib.extension_context import RematchApplicationContext as ApplicationContext

if TYPE_CHECKING:
    from app.bot import RematchItaliaBot


class GeneralCog(Cog):
    def __init__(self, bot: "RematchItaliaBot"):
        self.bot = bot


    @commands.slash_command(name="ping", description="Controlla la latenza del bot.",
                            guild_ids=[996755561829912586])
    async def ping(self, actx: ApplicationContext):
        """
        This command checks the bot's latency.
        It replies with the current latency in milliseconds.
        """
        latency = round(self.bot.latency * 1000)
        await actx.respond(f"🏓 Pong! Latency: {latency} ms")

    @commands.slash_command(name="feedback", description="Invia un feedback agli sviluppatori.",
                            guild_ids=[996755561829912586])
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
            colour=Colour.green,
            author=actx.author,
            footer=f"© Rematch Italia. All rights reserved.",
            timestamp=datetime.datetime.now(datetime.UTC)
        )

        await owner.send(
            embed=embed,
            allowed_mentions=None  # Prevents pinging the owner
        )
        await actx.respond("✅ Il tuo feedback è stato inviato. Grazie per il supporto!")


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.__ready__:
            self.bot.cogs_ready.ready_up("general")
            self.bot.__ready__ = True


def setup(bot: "RematchItaliaBot"):
    bot.add_cog(GeneralCog(bot))
    logger.debug("GeneralCog loaded successfully.")