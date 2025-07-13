from discord import SlashCommandGroup, Option, Role, slash_command, TextChannel, Colour
from discord.ext import commands
from typing import TYPE_CHECKING
from app.logger import logger
from app.lib.db.schemes import CommandEnum, add_command_permission, remove_command_permission, set_guild_log_channel
from discord import OptionChoice
from app.lib.extension_context import RematchApplicationContext as ApplicationContext

if TYPE_CHECKING:
    from app.bot import RematchItaliaBot


COMMAND_CHOICES = [OptionChoice(c.name, c.value) for c in CommandEnum]


class Manager(commands.Cog):
    def __init__(self, bot: "RematchItaliaBot"):
        self.bot = bot

    perms = SlashCommandGroup(
        name="perm",
        description="Gestione dei permessi per i comandi.",
        guild_ids=[996755561829912586]
    )

    @perms.command(
        name="add",
        description="Aggiungi un permesso per un comando specifico.",
    )
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def add_permission(
            self,
            actx: ApplicationContext,
            command: Option(
                str,
                "Seleziona il comando",
                choices = COMMAND_CHOICES
            ),
            role: Option(Role, "Ruolo a cui concedere il permesso")
    ):
        command_enum = CommandEnum(command)
        guild = actx.guild
        command_permission = await add_command_permission(guild, command_enum, role.id)
        if command_permission:
            await actx.respond(f"✅ Permesso aggiunto per il comando `{command_enum.name}` al ruolo `{role.name}`.",
                               ephemeral=True)
            await actx.send_log(f"{actx.author.mention} gave role `{role.name}` "
                                f"permission for command {command_enum.name}.", color=Colour.green())
        else:
            await actx.respond(f"❌ Errore nell'aggiunta del permesso per il comando `{command_enum.name}` al ruolo "
                               f"`{role.name}`.", epheral=True)
            await actx.send_log(f"{actx.author.mention} failed to give permission {command_enum.name} "
                                f"to `{role.name}`", color=Colour.red())



    @perms.command(
        name="remove",
        description="Rimuovi un permesso per un comando specifico.",
    )
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def remove_permission(
            self,
            actx: ApplicationContext,
            command: Option(
                str,
                "Seleziona il comando",
                choices=COMMAND_CHOICES
            ),
            role: Option(Role, "Ruolo da cui rimuovere il permesso")
    ):
        command_enum = CommandEnum(command)
        guild = actx.guild
        success = await remove_command_permission(guild, command_enum, role.id)
        if success:
            await actx.respond(f"✅ Permesso rimosso per il comando `{command_enum.name}` dal ruolo `{role.name}`.",
                               ephemeral=True)
            await actx.send_log(f"{actx.author.mention} removed role `{role.name}` "
                                f"permission for command {command_enum.name}.", color=Colour.green())
        else:
            await actx.respond(f"❌ Errore nella rimozione del permesso per il comando `{command_enum.name}` dal ruolo "
                               f"`{role.name}`.", ephemeral=True)
            await actx.send_log(f"{actx.author.mention} failed to give permission {command_enum.name} "
                                f"to `{role.name}`", color=Colour.red())

    @slash_command(
        name="log_channel",
        description="Imposta il canale di log per i comandi.",
        guild_ids=[996755561829912586]
    )
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def log_channel(
            self,
            actx: ApplicationContext,
            channel: Option(
                TextChannel,
                "Scegli il canale di log"
            )
    ):
        guild = actx.guild
        success = await set_guild_log_channel(guild, channel)
        if success:
            await actx.respond(f"✅ Canale di log impostato su {channel.mention}.", ephemeral=True)
        else:
            await actx.respond("❌ Errore nell'impostazione del canale di log.", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.__ready__:
            self.bot.cogs_ready.ready_up("manager")


def setup(bot: "RematchItaliaBot"):
    bot.add_cog(Manager(bot))
    logger.debug("Manager loaded successfully")

