from typing import Dict, Tuple

import discord
from discord import Guild, ButtonStyle, Embed, Colour, Member
from discord.ui import View, Select, Button, button, Modal

from app.lib.db.schemes import RankLinkEnum
from app.logger import logger
from lib.db.queries import link_rank, create_platform_link, get_role
from lib.db.schemes import PlatformEnum
from rematch_tracker import ProfilePlayer, ProfileResponse, resolve_rematch_id

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.bot import RematchItaliaBot


class RoleDropdown(Select):
    def __init__(
            self,
            guild: Guild,
            ranks: list[RankLinkEnum],
            current: int,
            mapping: Dict[RankLinkEnum, discord.Role],
    ):
        self.guild = guild
        self.ranks = ranks
        self.current = current
        self.mapping = mapping

        rank = ranks[current]
        options = [
                      discord.SelectOption(label=r.name, value=str(r.id))
                      for r in guild.roles
                      if not r.is_default()
                  ][:25] or [discord.SelectOption(label="⛔ nessun ruolo", value="none")]

        super().__init__(
            placeholder=f"Scegli il ruolo per {rank.name}",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"ranklink_{rank.value}"
        )

    async def callback(self, interaction: discord.Interaction):
        rank = self.ranks[self.current]
        raw = self.values[0]
        step = self.current + 2
        role = self.guild.get_role(int(raw)) if raw != "none" else None
        self.mapping[rank] = role
        self.current += 1

        view: RankLinkView = self.view
        view.clear_items()

        if self.current < len(self.ranks):
            view.add_item(RoleDropdown(
                guild=self.guild,
                ranks=self.ranks,
                current=self.current,
                mapping=self.mapping
            ))
            embed = Embed(
                title="📊 Associa ai Rank i Ruoli del server",
                description=f"**Rank corrente:** {rank.name}",
                colour=Colour.blurple()
            )
            embed.set_footer(text=f"Rank {step}/{len(self.ranks)}")
            await interaction.response.edit_message(
                content=None,
                view=view,
                embed=embed
            )
        else:
            # noinspection PyTypeChecker
            confirm_btn = Button(label="Conferma", style=ButtonStyle.green)

            async def confirm_cb(inter: discord.Interaction):
                for r, rl in self.mapping.items():
                    logger.debug("Rank %s → Role %s", r.name, rl and rl.name)
                    rank_db = await link_rank(self.guild, rl, r)
                    if not rank_db:
                        await inter.response.send_message(
                            f"❌ Errore nel collegamento del rank **{r.name}** con il ruolo **{rl.name}**.",
                            ephemeral=True
                        )
                        return
                await inter.response.edit_message(
                    content="✅ Tutti i rank sono stati collegati correttamente!\n"
                            "Il messaggio si chiuderà tra 5 secondi",
                    view=None
                )
                view.stop()
                original = await inter.original_response()
                await original.delete(delay=5)

            confirm_btn.callback = confirm_cb
            view.add_item(confirm_btn)

            await interaction.response.edit_message(
                content="✅ Tutti i rank sono stati mappati! Premi **Conferma** per salvare.",
                view=view
            )


class RankLinkView(View):
    def __init__(self, guild: Guild, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.guild = guild
        self.ranks = sorted(list(RankLinkEnum), key=lambda r: r.value)
        self.mapping: Dict[RankLinkEnum, discord.Role] = {}
        self.add_item(RoleDropdown(
            guild=self.guild,
            ranks=self.ranks,
            current=0,
            mapping=self.mapping
        ))


class RematchLinkForm(Modal):
    def __init__(self, bot: "RematchItaliaBot", title="Rematch Link Form", *args, **kwargs):
        self.bot = bot
        # noinspection PyTypeChecker
        super().__init__(
            discord.ui.InputText(
                label="Nickname Rematch",
                placeholder="Inserisci il tuo nickname su Rematch o il tuo steam id / link all'account "
                            "se giochi da Steam",
                style=discord.InputTextStyle.long,
                required=True,
            ),
            discord.ui.InputText(
                label="Piattaforma",
                placeholder="Steam, Playstation o Xbox",
                style=discord.InputTextStyle.short,
                required=True
            ),
            title=title,
            timeout=180
        )

    async def callback(self, interaction: discord.Interaction):
        nickname = self.children[0].value.strip()
        platform = self.children[1].value.strip().lower()

        if not nickname or not platform:
            await interaction.response.send_message(
                "❌ Devi compilare tutti i campi del form.",
                ephemeral=True
            )
            return

        if platform not in ["steam", "playstation", "xbox"]:
            await interaction.response.send_message(
                "❌ Piattaforma non valida. Inserisci `Steam`, `Playstation` o `Xbox`.",
                ephemeral=True
            )
            return
        try:
            profile: ProfileResponse
            profile,  created = await get_platform_link(interaction.user, identifier=nickname,
                                                        platform=PlatformEnum(platform))
            if profile is None:
                await interaction.response.send_message(
                    "❌ Non è stato possibile trovare il tuo profilo di Rematch. "
                    "Assicurati che il nickname sia e di aver scelto la piattaforma corretta."
                    "Ti ricordo che se giochi da Steam devi inserire il tuo steam id o il link del profilo.",
                    ephemeral=True
                )
                return
            if not created:
                await interaction.response.send_message(
                    "❌ Il tuo profilo è già collegato a Rematch.",
                    ephemeral=True
                )
                return
            rank = RankLinkEnum(profile["rank"]["current_league"])

            await self.bot.update_member_rank(interaction.user, rank)
        except Exception as e:
            logger.error(f"Error updating member rank: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ Si è verificato un errore durante l'inserimento del tuo profilo. "
                "Per favore, riprova più tardi.",
                ephemeral=True
            )
            return
        await interaction.response.send_message(
            "✅ Il tuo profilo è stato collegato correttamente!\n",
            ephemeral=True
        )


class OpenFormView(View):
    def __init__(self, bot: "RematchItaliaBot", timeout: float | None = None):
        super().__init__(timeout=timeout)
        self.bot = bot

    # noinspection PyTypeChecker,PyUnusedLocal
    @button(label="Compila il form", style=discord.ButtonStyle.red, custom_id="open_form_button")
    async def open_form(self, btn: Button, interaction: discord.Interaction):
        await interaction.response.send_modal(RematchLinkForm(bot=self.bot,
                                                              title="Compila il form di collegamento a Rematch"
                                                              ))



async def get_platform_link(member: Member, identifier: str, platform: PlatformEnum) -> Tuple[ProfileResponse, bool] | None:
    profile: ProfileResponse = await resolve_rematch_id(platform=platform, identifier=identifier)
    if profile is None:
        logger.warning("Failed to resolve Rematch ID for %s on platform %s", identifier, platform.value)
        return None
    platform_link, created = await create_platform_link(member=member, profile=profile)
    if platform_link is None:
        logger.warning("There was a problem saving player information")
        return None
    return profile, created

