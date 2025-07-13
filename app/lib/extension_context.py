import datetime
from typing import Optional

from discord.ext.commands import Context
from discord import TextChannel, ApplicationContext, Colour, Embed


class RematchContext(Context):
    log_channel: Optional[TextChannel]

    async def send_log(self, message: str, color: Colour = None):
        if self.log_channel:
            embed = Embed(
                title=self.command.name,
                description=message,
                color=color or Colour.default(),
                timestamp=datetime.datetime.now(datetime.UTC)
            )
            embed.set_author(name=self.author.name, icon_url=self.author.avatar.url if self.author.avatar else None)
            embed.set_footer(text="ID: " + str(self.author.id))
            await self.log_channel.send(embed=embed)

class RematchApplicationContext(ApplicationContext):
    log_channel: Optional[TextChannel]


    async def send_log(self, message: str, color: Colour = None):
        if self.log_channel:
            embed = Embed(
                title=self.command.name,
                description=message,
                color=color or Colour.default(),
                timestamp=datetime.datetime.now(datetime.UTC)
            )
            embed.set_author(name=self.author.name, icon_url=self.author.avatar.url if self.author.avatar else None)
            embed.set_footer(text="ID: " + str(self.author.id))
            await self.log_channel.send(embed=embed)