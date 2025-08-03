from discord.ext import commands

from app.lib.db.queries import CommandEnum, get_command_permission
from app.logger import logger
from app.lib.extension_context import RematchContext as Context, RematchApplicationContext as ApplicationContext


def require_role(command: CommandEnum):
    async def predicate(ctx: Context | ApplicationContext):
        # check if author is admin
        if ctx.author.guild_permissions.administrator:
            return True
        guild = ctx.guild
        if not guild:
            logger.error("Command cannot be used in private messages.")
            raise commands.NoPrivateMessage("Questo comando non può essere usato nei messaggi privati.")
        permissions = await get_command_permission(guild, command)
        if not permissions:
            raise commands.MissingPermissions(
                "❌ Non hai i permessi per usare questo comando"
            )
        role_ids = [perm.role_id for perm in permissions]
        if any(role.id in role_ids for role in ctx.author.roles):
            return True
        else:
            raise commands.MissingPermissions(
                "❌ Non hai i permessi per usare questo comando"
            )

    return commands.check(predicate)
