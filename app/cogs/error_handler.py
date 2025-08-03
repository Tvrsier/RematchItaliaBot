from typing import TYPE_CHECKING

from discord.ext import commands

from app.logger import logger
from app.lib.extension_context import RematchContext as Context, RematchApplicationContext as ApplicationContext

if TYPE_CHECKING:
    from app.bot import RematchItaliaBot


class ErrorHandler(commands.Cog):
    def __init__(self, bot: "RematchItaliaBot"):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: commands.CommandError):
        if hasattr(ctx.command, "on_error"):
            return

        if isinstance(error, commands.NotOwner):
            await ctx.reply("❌ Mi dispiace, solo il proprietario del bot può eseguire questo comando.")

        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ Non hai i permessi necessari per eseguire questo comando.")

    @commands.Cog.listener()
    async def on_application_command_error(self, actx: ApplicationContext, error: commands.CommandError):
        if hasattr(actx.command, "on_error"):
            return

        if isinstance(error, commands.NotOwner):
            await actx.respond("❌ Mi dispiace, solo il proprietario del bot può eseguire questo comando.", ephemeral=True)
        elif isinstance(error, commands.MissingPermissions):
            await actx.respond("❌ Non hai i permessi necessari per eseguire questo comando.", ephemeral=True)
        else:
            logger.error(f"Unhandled error in application command: {error}", exc_info=True, stack_info=True)
            await actx.respond("❌ Al momento questo comando non è disponibile.", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.__ready__:
            self.bot.cogs_ready.ready_up("error_handler")


def setup(bot: "RematchItaliaBot"):
    bot.add_cog(ErrorHandler(bot))
    logger.debug("ErrorHandler loaded successfully.")
