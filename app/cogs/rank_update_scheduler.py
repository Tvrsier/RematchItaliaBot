import os
from typing import TYPE_CHECKING

from discord import Cog, User, Guild
from discord.ext import commands, tasks
from app.logger import logger
from app.lib.db.queries import get_platform_to_update, check_guild_rank
from app.lib.db.schemes import PlatformLink, PlatformEnum, RankLinkEnum
from app.rematch_tracker import get_rematch_profile
from rematch_tracker import ProfileResponse

RANK_UPDATE_SCHEDULER_INTERVAL = int(os.getenv("RANK_UPDATE_SCHEDULER_INTERVAL", "1800"))

if TYPE_CHECKING:
    from app.bot import RematchItaliaBot

class RankUpdateScheduler(Cog):
    """
    This class is responsible for scheduling rank updates.
    It uses a background task to periodically check and update ranks for members.
    """

    def __init__(self, bot: "RematchItaliaBot"):
        self.bot = bot
        self._updater_loop.start()

    def cog_unload(self):
        """
        This method is called when the cog is unloaded.
        It cancels the background task.
        """
        self._updater_loop.cancel()

    async def _fetch_users(self, discord_ids: list[int]) -> list[User]:
        ret = []
        for uid in discord_ids:
            user = self.bot.get_user(uid)
            if user is None:
                user = await self.bot.fetch_user(uid)
            ret.append(user)
        return ret

    # noinspection PyMethodMayBeStatic
    async def _fetch_rematch_profile(self, platform_links: list[PlatformLink]) -> dict[int, RankLinkEnum]:
        """
        This method fetches the Rematch profile for the given platform links.
        It checkes if the rank retrieved from the rematch API is different from the cached rank.
        If it is not different, the object will be removed from the list.
        :rtype: dict[int, RankLinkEnum]
        :param platform_links:
        :return: A list of PlatformLink that has to be updated
        """
        ret = {}
        logger.info(f"Fetching Rematch profiles for {len(platform_links)} members...")
        original_links = platform_links.copy()
        for link in platform_links:
            platform = link.platform.value if link.platform != PlatformEnum.PSN else "psn"
            platform_id = link.platform_id
            try:
                profile: ProfileResponse = await get_rematch_profile(platform=platform, platform_id=platform_id)
                if profile is None:
                    logger.warning(f"Failed to fetch Rematch profile for {platform}/{platform_id}")
                    continue
                rank = RankLinkEnum(profile["rank"]["current_league"])
                if rank != link.cached_rank:
                    ret[link.discord_id.discord_id] = rank
                    logger.debug(f"Rank set for update for {link.discord_id.discord_id}: {rank}")
                else:
                    original_links.remove(link)
            except Exception as e:
                logger.error(f"Error fetching Rematch profile for {platform}/{platform_id}: {e}", exc_info=True)
                continue
        logger.info("Rematch profiles had been fetched.")
        logger.debug(f"Ranks will be updated for {len(ret)}/{len(platform_links)} members.")
        return ret

    # noinspection PyMethodMayBeStatic
    async def _get_mutual_guilds(self, users: list[User]) -> dict[User, list[Guild]]:
        """
        This method retrieves the mutual guilds for the given users.
        The method does not return the guilds where the role to rank link is not beeing set.
        :rtype: list[Guild]
        :param users:
        :return: A list of Guilds where the users are members.
        """
        member_guilds_map = {}
        for user in users:
            guilds = []
            for guild in user.mutual_guilds:
                if not await check_guild_rank(guild):
                    continue
                guilds.append(guild)
            if guilds:
                logger.debug(f"User {user.id} has {len(guilds)} mutual guilds with ranks.")
                member_guilds_map[user] = guilds

        logger.info(f"Found mutual guilds for {len(member_guilds_map)} users.")
        return member_guilds_map

    async def _update_member_ranks(
            self,
            member_guilds_map: dict[User, list[Guild]],
            to_update: dict[int, RankLinkEnum]
    ) -> None:
        """
        This method updates the ranks for members in the given guilds.
        It iterates over the member-guilds map and updates the rank for each member in each guild.
        :param member_guilds_map:
            A dictionary mapping users to their mutual guilds.
        :param to_update:
            A dictionary mapping user IDs to their new ranks.
        :return:
            None
        """
        logger.info("Starting to update member ranks...")
        for user, guilds in member_guilds_map.items():
            if user.id not in to_update:
                logger.debug(f"User {user.id} has no rank to update.")
                continue
            rank = to_update[user.id]
            logger.info(f"Updating rank for user {user.id} to {rank.name} in {len(guilds)} guilds.")
            for guild in guilds:
                try:
                    member = guild.get_member(user.id)
                    if member is None:
                        try:
                            member = await guild.fetch_member(user.id)
                        except Exception as e:
                            logger.error(f"Failed to fetch member {user.id} in guild {guild.id}: {e}", exc_info=True)
                            continue
                    await self.bot.update_member_rank(member, rank)
                    logger.debug(f"Updated rank for user {user.id} in guild {guild.id}.")
                except Exception as e:
                    logger.error(f"Failed to update rank for user {user.id} in guild {guild.id}: {e}", exc_info=True)

    @tasks.loop(seconds=RANK_UPDATE_SCHEDULER_INTERVAL)
    async def _updater_loop(self):
        """
        This method runs periodically to update ranks for members.
        It checks if the bot is ready and then calls the update method.
        """
        if not self.bot.__ready__:
            return

        logger.info("Running rank update scheduler...")
        platform_links = await get_platform_to_update()
        logger.debug(f"Checking ranks of {len(platform_links)} members...")

        to_update = await self._fetch_rematch_profile(platform_links)
        discord_ids = list(to_update.keys())
        users = await self._fetch_users(discord_ids)
        if not users:
            logger.info("No users to update ranks for.")
            return
        member_guilds_map = await self._get_mutual_guilds(users)
        await self._update_member_ranks(member_guilds_map, to_update)
        logger.info("Rank update scheduler completed.")


    @_updater_loop.before_loop
    async def before_updater_loop(self):
        """
        This method runs before the loop starts.
        It waits until the bot is ready.
        """
        await self.bot.wait_until_ready()
        logger.info("Rank update scheduler is ready.")

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.__ready__:
            self.bot.cogs_ready.ready_up("manager")


def setup(bot: "RematchItaliaBot"):
    """
    This function is called when the cog is loaded.
    It adds the RankUpdateScheduler cog to the bot.
    """
    bot.add_cog(RankUpdateScheduler(bot))
    logger.debug("RankUpdateScheduler cog has been loaded.")