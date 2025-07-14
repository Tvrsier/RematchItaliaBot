from discord.ext import commands
from app.logger import logger
from app.lib.db.queries import CommandEnum, get_command_permission

def require_role(command: CommandEnum):
    async def predicate(ctx: commands.Context):
        #check if author is admin
        if ctx.author.guild_permissions.administrator:
            return True
        guild = ctx.guild
        if not guild:
            logger.error("Command cannot be used in private messages.")
            raise commands.NoPrivateMessage("❌ Questo comando non può essere usato nei messaggi privati.")
        permissions = await get_command_permission(guild, command)
        if not permissions:
            return True
        role_ids = [perm.role_id for perm in permissions]
        if any(role.id in role_ids for role in ctx.author.roles):
            return True
        else:
            logger.warning(f"User {ctx.author.name} does not have the required role to use this command.")
            await ctx.send("You do not have permission to use this command.")
            raise commands.CheckFailure("❌ Non hai i permessi per usare questo comando.")
    return commands.check(predicate)
