from typing import TYPE_CHECKING

from discord.ext import commands

from app.logger import logger

if TYPE_CHECKING:
    from app.bot import RematchItaliaBot


class ErrorHandler(commands.Cog):
    def __init__(self, bot: "RematchItaliaBot"):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if hasattr(ctx.command, "on_error"):
            return

        if isinstance(error, commands.NotOwner):
            await ctx.reply("❌ Mi dispiace, solo il proprietario del bot può eseguire questo comando.")

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.__ready__:
            self.bot.cogs_ready.ready_up("error_handler")


def setup(bot: "RematchItaliaBot"):
    bot.add_cog(ErrorHandler(bot))
    logger.debug("ErrorHandler loaded successfully.")
