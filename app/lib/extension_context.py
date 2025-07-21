import datetime
from typing import Optional

from discord import TextChannel, ApplicationContext, Colour, Embed
from discord.ext.commands import Context


class RematchContext(Context):
    log_channel: Optional[TextChannel]

    async def send_log(self):
        if self.log_channel:
            if hasattr(self, 'log_message'):
                embed = Embed(
                    title=self.command.qualified_name,
                    description=self.log_message,
                    color=getattr(self, 'log_color', Colour.default()),
                    timestamp=datetime.datetime.now(datetime.UTC)
                )
                embed.set_author(name=self.author.name, icon_url=self.author.avatar.url if self.author.avatar else None)
                embed.set_footer(text="ID: " + str(self.author.id))
                await self.log_channel.send(embed=embed)


class RematchApplicationContext(ApplicationContext):
    log_channel: Optional[TextChannel]

    async def send_log(self):
        if self.log_channel:
            if hasattr(self, 'log_message'):
                embed = Embed(
                    title=self.command.qualified_name,
                    description=self.log_message,
                    color=getattr(self, 'log_color', Colour.default()),
                    timestamp=datetime.datetime.now(datetime.UTC)
                )
                embed.set_author(name=self.author.name, icon_url=self.author.avatar.url if self.author.avatar else None)
                embed.set_footer(text="ID: " + str(self.author.id))
                await self.log_channel.send(embed=embed)
