from typing import TYPE_CHECKING

from discord import OptionChoice
from discord import SlashCommandGroup, Option, Role, slash_command, TextChannel, Colour, Embed
from discord.ext import commands

from app.checks import require_role
from app.lib.db.queries import CommandEnum, add_command_permission, remove_command_permission, set_guild_log_channel
from app.lib.db.schemes import RankLinkEnum
from app.lib.extension_context import RematchApplicationContext as ApplicationContext
from app.logger import logger
from app.views import RankLinkView
from lib.db.queries import link_rank, create_persistent_view
from lib.db.schemes import PersistentViewEnum
from views import OpenFormView

if TYPE_CHECKING:
    from app.bot import RematchItaliaBot

COMMAND_CHOICES = [OptionChoice(c.name, c.value) for c in CommandEnum]
RANK_CHOICES = [OptionChoice(r.name, str(r.value)) for r in RankLinkEnum]
VIEW_ENUM_CHOICES = [OptionChoice(v.name, v.value) for v in PersistentViewEnum]


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
                choices=COMMAND_CHOICES
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
    )
    @commands.check_any(
        commands.has_guild_permissions(administrator=True),
        require_role(CommandEnum.SET_LOG_CHANNEL)
    )
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

    @slash_command(
        name="rematch_form",
        description="Imposta il modulo di link account Rematch.",
        guild_ids=[996755561829912586]
    )
    @commands.guild_only()
    @commands.check_any(
        commands.has_guild_permissions(administrator=True),
        require_role(CommandEnum.REMATCH_FORM)
    )
    async def setup_form(
            self,
            actx: ApplicationContext,
            channel: Option(
                TextChannel,
                "Canale in cui inviare il modulo di link account Rematch.",
                required=True
            ),
            content: Option(
                str,
                "Contenuto del modulo di link account Rematch.",
                required=True,
                default="Ciao! Per favore, collega il tuo account Rematch al tuo account Discord."
            )
    ):
        ch: TextChannel = channel
        embed = Embed(
            title="📋 Compila il Form",
            description=content,
            colour=Colour.blurple()
        )
        embed.set_footer(text="© Rematch Italia, all rights reserved.")

        view = OpenFormView(bot=self.bot)

        msg = await ch.send(embed=embed, view=view)
        actx.__setattr__("msg", msg)
        actx.__setattr__("ch", ch)
        actx.__setattr__("view", PersistentViewEnum.REMATCH_FORM)
        actx.log_message = f"{actx.author.mention} set up the Rematch form in {ch.mention}."
        actx.log_color = Colour.green()
        await actx.respond(f"✅ Modulo di link account Rematch impostato in {ch.mention}.", ephemeral=True)

    @setup_form.after_invoke
    async def require_role_after_invoke(self, actx: ApplicationContext):
        persistent_view = await create_persistent_view(actx.__getattribute__("view"), guild=actx.guild,
                                                       channel=actx.__getattribute__("ch"),
                                                       message=actx.__getattribute__("msg"))
        logger.debug(f"Persistent view created: {persistent_view.id} ")

    @slash_command(
        name="load_persistent_view",
        description="Carica una vista persistente (NOTA! da usare solo se la vista non è stata "
                    "caricata automaticamente).",
        guild_ids=[996755561829912586]
    )
    @commands.guild_only()
    @commands.check_any(
        commands.has_guild_permissions(administrator=True),
        require_role(CommandEnum.LOAD_PERSISTENT_VIEW)
    )
    async def load_persistent_view(self,
                                   actx: ApplicationContext,
                                   view_name: Option(
                                       str,
                                       "Nome della vista persistente da caricare",
                                       choices=VIEW_ENUM_CHOICES,
                                   ),
                                   message_id: Option(
                                       str,
                                       "ID del messaggio da cui caricare la vista",
                                       required=True
                                   ),
                                   channel_id: Option(
                                       str,
                                       "ID del canale in cui si trova il messaggio. "
                                       "Lascia vuoto per usare il canale corrente",
                                       required=False,
                                   )
                                   ):
        message_id = int(message_id)
        channel_id = int(channel_id) if channel_id else None
        view_enum = PersistentViewEnum(view_name)
        channel = actx.guild.get_channel(channel_id) if channel_id else actx.channel
        persistent_view = await create_persistent_view(view_enum, actx.guild, channel, message_id)
        if persistent_view:
            await self.bot.load_persistent_view(view_enum, message_id)
            actx.log_message = f"{actx.author.mention} loaded persistent view `{view_enum.name}` " \
                               f"from message {message_id} in {channel.mention}."
            actx.log_color = Colour.green()
            await actx.respond(f"✅ Vista persistente `{view_enum.name}` caricata con successo dal messaggio "
                               f"{message_id} in {channel.mention}.", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.__ready__:
            self.bot.cogs_ready.ready_up("manager")


def setup(bot: "RematchItaliaBot"):
    bot.add_cog(Manager(bot))
    logger.debug("Manager loaded successfully")
