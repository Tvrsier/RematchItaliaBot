import asyncio
import sys
import traceback
from pathlib import Path

from discord.ext.commands import Bot
from discord import Intents, NoEntryPointError, ExtensionFailed, Activity, ActivityType, Interaction, Message
import os
from app.logger import logger
from app.lib.db import DatabaseManager
from app.lib.db.schemes import GuildSchema, PersistentViewEnum
from app.lib.extension_context import RematchContext as Context, RematchApplicationContext as ApplicationContext
from app.lib.db.queries import get_persistent_views
from app.views import RankLinkView, OpenFormView

COGS_PATH = Path("./app/cogs")
if not COGS_PATH.exists():
    COGS_PATH.mkdir(parents=True, exist_ok=True)

prefix = "rmi&"
OWNER_IDS = [int(x) for x in os.getenv("OWNER_IDS", "").split(",") if x]
COGS = [p.stem for p in COGS_PATH.glob("*.py")]

PERSISTENT_VIEW_DICT = {
    PersistentViewEnum.RANK_LINK: RankLinkView,
    PersistentViewEnum.REMATCH_FORM: OpenFormView,
}


class Ready:
    """Tiene traccia dello stato di caricamento dei cog."""

    def __init__(self):
        if COGS is None or len(COGS) == 0:
            logger.warning("No cogs found to load")
        for cog in COGS:
            setattr(self, cog, False)

    def ready_up(self, cog: str):
        setattr(self, cog, True)
        logger.info(f"{cog} is ready")

    def all_ready(self) -> bool:
        if not COGS or len(COGS) == 0:
            return True
        return all(getattr(self, cog) for cog in COGS)


class RematchItaliaBot(Bot):
    def __init__(self):
        intents = Intents.default() | Intents.message_content | Intents.members

        super().__init__(
            command_prefix=prefix,
            owner_ids=OWNER_IDS,
            intents=intents
        )
        models = {"models": ["app.lib.db.schemes"]}
        self.db = DatabaseManager("sqlite://data/rematch_italia.db", models)
        self.version = None
        self.token = os.getenv("API_KEY")
        if not self.token:
            raise RuntimeError("API_KEY not found in environment variables. Please set it in your .env file.")
        self.cogs_ready = Ready()
        self.__ready__ = False
        self.owner_ids = OWNER_IDS
        self.before_invoke(self._inject_log_channel)
        self.after_invoke(self._auto_log)

    def run(self, version: str):
        self.version = version
        logger.info("Starting Rematch Italia Bot version %s", self.version)
        logger.info(f"Running setup . . .")
        self.setup_cogs()
        logger.info("Setup complete. Running bot . . .")
        super().run(self.token, reconnect=True)

    def setup_cogs(self):
        if COGS is not None and len(COGS) != 0:
            for cog in COGS:
                try:
                    logger.debug("Loading cog: %s", cog)
                    self.load_extension(f"app.cogs.{cog}")
                except NoEntryPointError as e:
                    logger.error("Ignoring %s (load failed): %s", cog, e, exc_info=True)
                    traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
                except ExtensionFailed as e:
                    logger.error("Ignoring %s (load failed): %s", cog, e, exc_info=True)
                    traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
                except Exception as e:
                    logger.error("Ignoring %s (load failed): %s", cog, e, exc_info=True)
                    traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
                else:
                    logger.debug("Cog %s loaded successfully", cog)
                    self.cogs_ready.ready_up(cog)
        else:
            logger.warning("No cogs found to load, assuming all are ready.")
            self.__ready__ = True

    async def on_connect(self):
        await self.db.connect()
        logger.info("Connected to the database.")
        if self.auto_sync_commands:
            await self.sync_commands()
        logger.info(f"Bot {self.user} connected to Discord.")

    async def on_ready(self):
        if not self.__ready__:
            while not self.cogs_ready.all_ready():
                await asyncio.sleep(0.5)
            self.__ready__ = True
        await self.load_persistent_views()
        logger.info("Rematch Italia Bot is ready!")
        await self.change_presence(activity=Activity(type=ActivityType.watching,
                                                     name=f"{len(self.users)} users |"))

    async def get_context(self, message, *, cls=Context):
        """Override to inject log channel into context."""
        ctx = await super().get_context(message, cls=cls)
        return ctx

    async def get_application_context(
            self, interaction: Interaction, cls=ApplicationContext
    ):
        ctx = await super().get_application_context(interaction, cls=cls)
        return ctx

    # noinspection PyMethodMayBeStatic
    async def _inject_log_channel(self, ctx: Context | ApplicationContext) -> None:
        """Injects the log channel into the context if it exists."""
        if ctx.guild:
            db_guild = await GuildSchema.get_or_none(guild_id=ctx.guild.id)
            if db_guild and db_guild.log_chanel_id:
                ctx.log_channel = ctx.guild.get_channel(db_guild.log_chanel_id)
            else:
                ctx.log_channel = None
        else:
            ctx.log_channel = None

    # noinspection PyMethodMayBeStatic
    async def _auto_log(self, ctx: Context | ApplicationContext) -> None:
        """Automatically logs the command usage to the log channel."""
        await ctx.send_log()

    async def load_persistent_views(self):
        """Load persistent views from the database."""
        # This method can be used to load any persistent views that need to be restored
        # when the bot starts. For now, it is a placeholder.
        logger.info("Loading persistent views (if any) . . .")
        # Implement loading logic here if needed
        # iterate through persistent views enum
        for view in PersistentViewEnum:
            persistent_view = await get_persistent_views(view_name=view)
            if persistent_view:
                for v in persistent_view:
                    if v.view_name in PERSISTENT_VIEW_DICT:
                        # check if the message still exists
                        to_delete = False
                        message: Message | None = None
                        guild = self.get_guild(v.guild_id.guild_id)
                        if not guild:
                            logger.warning(f"Guild {v.guild_id.guild_id} not found for persistent view {v.view_name}.")
                            to_delete=True
                        channel = guild.get_channel(v.channel_id)
                        if not channel:
                            logger.warning(
                                f"Channel {v.channel_id} not found in guild {guild.name} for persistent view {v.view_name}.")
                            to_delete=True
                        try:
                            message = await channel.fetch_message(v.message_id)
                        except Exception as e:
                            logger.error(
                                f"Failed to fetch message {v.message_id} in channel {v.channel_id} for persistent view {v.view_name}: {e}")
                            to_delete=True
                        if not message:
                            logger.warning(
                                f"Message {v.message_id} not found in channel {v.channel_id} for persistent view {v.view_name}.")
                            to_delete=True
                        if to_delete:
                            logger.warning(f"Deleting persistent view {v.view_name} with message ID: {v.message_id} "
                                           f"because the message has been deleted or cannot be found.")
                            await v.delete()
                            continue
                        self.add_view(view=PERSISTENT_VIEW_DICT.get(v.view_name)(timeout=None),
                                      message_id=v.message_id)
                        logger.debug(f"Persistent view loaded: {v.view_name} with message ID: {v.message_id}")
            else:
                logger.debug(f"No persistent view found for: {view.name}")

        logger.info("Persistent views loaded successfully.")

    async def load_persistent_view(self,
                                   view_name: PersistentViewEnum,
                                   message_id: int):
        """Load a specific persistent view by name and message ID."""
        self.add_view(view=PERSISTENT_VIEW_DICT.get(view_name)(timeout=None), message_id=message_id)
