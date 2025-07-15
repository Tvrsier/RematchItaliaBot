import discord
from discord import Guild, ButtonStyle, Embed, Colour
from discord.ui import View, Select, Button
from typing import Dict

from app.lib.db.schemes import RankLinkEnum
from app.logger import logger
from lib.db.queries import link_rank


class RoleDropdown(Select):
    def __init__(
        self,
        guild: Guild,
        ranks: list[RankLinkEnum],
        current: int,
        mapping: Dict[RankLinkEnum, discord.Role],
    ):
        self.guild   = guild
        self.ranks   = ranks
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
        raw  = self.values[0]
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
        self.guild   = guild
        self.ranks   = sorted(list(RankLinkEnum), key=lambda r: r.value)
        self.mapping: Dict[RankLinkEnum, discord.Role] = {}
        self.add_item(RoleDropdown(
            guild=self.guild,
            ranks=self.ranks,
            current=0,
            mapping=self.mapping
        ))
