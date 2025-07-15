from discord import SlashCommandGroup, Option, Role, slash_command, TextChannel, Colour, Embed
from discord.ext import commands
from typing import TYPE_CHECKING
from app.logger import logger
from app.lib.db.queries import CommandEnum, add_command_permission, remove_command_permission, set_guild_log_channel
from discord import OptionChoice
from app.lib.extension_context import RematchApplicationContext as ApplicationContext
from app.checks import require_role
from app.views import RankLinkView
from app.lib.db.schemes import RankLinkEnum
from lib.db.queries import link_rank

if TYPE_CHECKING:
    from app.bot import RematchItaliaBot


COMMAND_CHOICES = [OptionChoice(c.name, c.value) for c in CommandEnum]
RANK_CHOICES = [OptionChoice(r.name, str(r.value)) for r in RankLinkEnum]


class Manager(commands.Cog):
    def __init__(self, bot: "RematchItaliaBot"):
        self.bot = bot

    perms = SlashCommandGroup(
        name="perm",
        description="Gestione dei permessi per i comandi.",
        guild_ids=[996755561829912586]
    )

    rank = SlashCommandGroup(
        name="rank",
        description="Gestione del rank system.",
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
            actx.log_message = f"{actx.author.mention} gave role `{role.name}` " \
                                f"permission for command {command_enum.name}."
            actx.color = Colour.green()
        else:
            await actx.respond(f"❌ Errore nell'aggiunta del permesso per il comando `{command_enum.name}` al ruolo "
                               f"`{role.name}`.", epheral=True)
            actx.log_message = f"{actx.author.mention} failed to give permission {command_enum.name} " \
                                f"to `{role.name}`"
            actx.color = Colour.red()



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
            actx.log_message = f"{actx.author.mention} removed role `{role.name}` " \
                                f"permission for command {command_enum.name}."
            actx.color = Colour.green()
        else:
            await actx.respond(f"❌ Errore nella rimozione del permesso per il comando `{command_enum.name}` dal ruolo "
                               f"`{role.name}`.", ephemeral=True)
            actx.log_message = f"{actx.author.mention} failed to remove permission {command_enum.name} " \
                                f"from `{role.name}`"
            actx.color = Colour.red()

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

    @rank.command(
        name="link",
        description="Collega i ruoli ai rank."
    )
    @commands.guild_only()
    @commands.check_any(
        commands.has_guild_permissions(administrator=True),
        require_role(CommandEnum.RANK_LINK)
    )
    async def link_rank(
            self,
            actx: ApplicationContext,
            rank: Option(
                str,
                "Seleziona il rank da associare",
                required=False,
                choices=RANK_CHOICES
            ) = None,
            role: Option(
                Role,
                "Ruolo da associare al rank",
                required=False
            ) = None
    ):
        if rank is None and role is None:
            view = RankLinkView(actx.guild)
            embed = Embed(
                title="📊 Associa ai Rank i Ruoli del server",
                description="Clicca sui pulsanti per associare i ruoli ai rank.\n"
                            f"**Rank corrente:** {view.ranks[0].name}",
                colour=Colour.blurple()
            )
            embed.set_footer(text=f"Rank 1/{len(view.ranks)}")
            await actx.respond(
                content=None,
                view=view,
                embed=embed
            )
            return
        if (rank is None) ^ (role is None):
            await actx.respond("❌ Devi specificare sia il rank che il ruolo da associare.", ephemeral=True)
            return

        rank_enum = RankLinkEnum(int(rank))
        success, created = await link_rank(actx.guild, role, rank_enum)
        if success:
            verb = "collegato" if created else "aggiornato"
            await actx.respond(f"✅ Ruolo `{role.name}` {verb} al rank `{rank_enum.name}`.", ephemeral=True)
        else:
            await actx.respond(f"❌ Errore nel collegamento del ruolo `{role.name}` al rank `{rank_enum.name}`.",
                               ephemeral=True)
        actx.log_message = f"{actx.author.mention} used command `/rank link`"
        actx.log_color = Colour.green() if success else Colour.red()



    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.__ready__:
            self.bot.cogs_ready.ready_up("manager")


def setup(bot: "RematchItaliaBot"):
    bot.add_cog(Manager(bot))
    logger.debug("Manager loaded successfully")

