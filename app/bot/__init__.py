import asyncio
import sys
import traceback
from pathlib import Path

from discord.ext.commands import Bot
from discord import Intents, NoEntryPointError, ExtensionFailed, Activity, ActivityType
import os
from app.logger import logger
from lib.db import DatabaseManager

COGS_PATH = Path("./app/cogs")
if not COGS_PATH.exists():
    COGS_PATH.mkdir(parents=True, exist_ok=True)

prefix = "rmi&"
OWNER_IDS = [int(x) for x in os.getenv("OWNER_IDS", "").split(",") if x]
COGS = [p.stem for p in COGS_PATH.glob("*.py")]

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
        models = {"models": ["lib.db.schemes"]}
        self.db = DatabaseManager("sqlite://data/rematch_italia.db", models)
        self.version = None
        # Ora legge il token dal .env
        self.token = os.getenv("API_KEY")
        if not self.token:
            raise RuntimeError("API_KEY not found in environment variables. Please set it in your .env file.")
        self.cogs_ready = Ready()
        self.__ready__ = False
        self.owner_ids = OWNER_IDS

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
            self.__ready__=True

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
        logger.info("Rematch Italia Bot is ready!")
        await self.change_presence(activity=Activity(type=ActivityType.watching,
                                                     name=f"{len(self.users)} users |"))
