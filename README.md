# RematchItaliaBot 🕹️🇮🇹

RematchItaliaBot is a Python-based application designed to manage and track rematch events, likely for a gaming or community platform. It features database integration, logging, and modular components for extensibility.

![Python Version](https://img.shields.io/badge/python-3.8--3.12-blue?logo=python)

## Features ✨
- 🧩 Modular bot architecture (cogs, checks, views)
- 🗄️ Database management (SQLite)
- 📋 Logging system
- 🔁 Rematch tracking and management
- 🛡️ Error handling

## Project Structure 🗂️
```
app/                # Main application package
  bot/              # Bot initialization and logic
  checks/           # Custom checks
  cogs/             # Bot cogs (extensions)
  lib/              # Libraries (db, logger, etc.)
  rematch_tracker/  # Rematch tracking logic
  views/            # UI components (if any)
data/               # Database files
logs/               # Log files
test/               # Unit tests
info.py             # Project info
launcher.py         # Entry point
```

## Code Structure & Key Concepts 🧠

### Cog Loading and the `Ready` Class
The bot uses a modular architecture where features are split into "cogs" (extensions). The `Ready` class in `app/bot/__init__.py` dynamically tracks which cogs have finished loading:
- When the bot starts, it scans the `app/cogs/` directory for Python files and treats each as a cog.
- For each cog, an attribute is created in the `Ready` instance to track its readiness.
- The `ready_up(cog)` method marks a cog as loaded, and `all_ready()` checks if all cogs are ready.

This approach allows the bot to ensure all features are initialized before handling events, and makes it easy to add or remove features by simply adding/removing cog files.

### Persistent Views
The bot uses a dictionary (`PERSISTENT_VIEW_DICT`) to map persistent view types (like forms or UI components) to their implementation classes. This enables the bot to restore interactive UI elements after a restart, improving user experience.

### The `RematchItaliaBot` Main Class
The heart of the project is the `RematchItaliaBot` class (in `app/bot/__init__.py`), which extends the Discord.py `Bot` class. Its main responsibilities are:
- **Initialization:** Sets up Discord intents, loads environment variables, initializes the database, and prepares cogs (modular features).
- **Custom Run Logic:** The `run(version)` method logs startup info, loads cogs, and starts the bot with reconnect support.
- **Cog Management:** The `setup_cogs()` method loads all cogs from the `app/cogs/` directory, handling errors gracefully and tracking readiness.
- **Event Handling:** Implements `on_connect` (database connection, command sync) and `on_ready` (waits for all cogs, loads persistent views, sets bot presence).
- **Context & Logging:** Injects a log channel into command contexts and automatically logs command usage.
- **Persistent Views:** Loads interactive UI elements from the database to restore state after restarts.

This class orchestrates the bot's startup, extension loading, database integration, and event lifecycle, making it the central point for understanding how the bot operates.

### Critical Parts of the `RematchItaliaBot` Class ⚙️

The `RematchItaliaBot` class is the core of the application, and several parts may be challenging for new contributors. Below are the most critical mechanisms, with the corresponding function or method names you can search for in `app/bot/__init__.py`:

- **Database Integration:**
  - Initialization: `self.db = DatabaseManager(...)` in the `__init__` method
  - Async connection: `async def on_connect(self)`

- **Dynamic Cog Loading:**
  - Method: `def setup_cogs(self)`

- **Persistent Views Restoration:**
  - Method: `async def load_persistent_views(self)`

- **Context and Logging Injection:**
  - Methods: `async def _inject_log_channel(self, ctx)` and `async def _auto_log(self, ctx)`

- **Event Synchronization:**
  - Method: `async def on_ready(self)`

> To quickly navigate in PyCharm, use the "Navigate > Symbol..." feature (Ctrl+Alt+Shift+N) and type the function or method name above.

These mechanisms provide robustness, modularity, and maintainability, but may require careful reading for those unfamiliar with advanced Discord.py patterns or asynchronous Python.

### Deep Dive: Critical Parts of the `RematchItaliaBot` Class with Code Examples 🧩

Below are the most important mechanisms of the `RematchItaliaBot` class, with direct code excerpts and explanations to help you understand how each part works:

#### 1. Database Integration
```python
# In __init__
self.db = DatabaseManager("sqlite://data/rematch_italia.db", models)
...
async def on_connect(self):
    await self.db.connect()
    logger.info("Connected to the database.")
    if self.auto_sync_commands:
        await self.sync_commands()
    logger.info(f"Bot {self.user} connected to Discord.")
```
- The bot uses a `DatabaseManager` for persistent storage. The connection is established asynchronously when the bot connects to Discord.

#### 2. Dynamic Cog Loading
```python
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
```
- This method loads all bot extensions (cogs) dynamically and tracks their readiness, handling errors gracefully.

#### 3. Persistent Views Restoration
```python
async def load_persistent_views(self):
    """Load persistent views from the database."""
    # Implementation loads UI elements so they persist after restarts
```
- Ensures Discord UI components (views) are restored after a bot restart.

#### 4. Context and Logging Injection
```python
async def _inject_log_channel(self, ctx: Context | ApplicationContext) -> None:
    if ctx.guild:
        db_guild = await GuildSchema.get_or_none(guild_id=ctx.guild.id)
        if db_guild and db_guild.log_chanel_id:
            ctx.log_channel = ctx.guild.get_channel(db_guild.log_chanel_id)
        else:
            ctx.log_channel = None
    else:
        ctx.log_channel = None

async def _auto_log(self, ctx: Context | ApplicationContext) -> None:
    await ctx.send_log()
```
- These methods inject a log channel into every command context and automatically log command usage.

#### 5. Event Synchronization
```python
async def on_ready(self):
    if not self.__ready__:
        while not self.cogs_ready.all_ready():
            await asyncio.sleep(0.5)
        self.__ready__ = True
    await self.load_persistent_views()
    logger.info("Rematch Italia Bot is ready!")
    await self.change_presence(activity=Activity(type=ActivityType.watching,
                                                 name=f"{len(self.users)} users |"))
```
- Waits for all cogs to be loaded before declaring the bot ready, then loads persistent views and sets the bot's presence.

## Understanding the Logging System 📝

The logging system in `app/logger/__init__.py` is designed to provide detailed, context-rich logs for both debugging and monitoring. Here’s how it works and why it might be confusing at first glance:

### Key Components
- **Log Directory and File:**
  - Logs are stored in a `logs/` directory, with the main file being `rematch_italia.log`. The directory is created automatically if it doesn't exist.
- **ClassNameFilter:**
  - This custom logging filter inspects the call stack to determine the class name and relative file path for each log record. It adds these as `classname` and `relpath` attributes, so logs show exactly where a message originated (e.g., `app.cogs.manager.Manager.some_method()`).
- **SmartClassFormatter:**
  - A custom formatter that ensures the class name is always included in the log output if available, making logs more readable and traceable.
- **Handlers:**
  - Logs are written both to the console and to a rotating file handler (rotates at midnight, keeps 5 backups). This ensures you have persistent logs for later review and real-time feedback in the console.
- **Log Format:**
  - The format includes timestamp, log level, relative path, class name, function name, message, and line number:
    ```
    %(asctime)s - [%(levelname)s] - %(relpath)s.%(classname)s.%(funcName)s(): %(message)s {%(lineno)d}
    ```

### Example Log Output
```
2025-07-23 12:34:56,789 - [INFO] - app.cogs.manager.Manager.some_method(): Some log message {42}
```

### Why This Matters
- **Traceability:** You can see exactly which class, method, and file produced each log message.
- **Debugging:** If something goes wrong, you can quickly locate the source in your codebase.
- **Cross-Platform:** The filter normalizes file paths for Windows and Unix systems.

### How to Use
- Use the `logger` object (imported from `app.logger`) in your code:
  ```python
  from app.logger import logger
  logger.info("This is an info message!")
  logger.error("Something went wrong!")
  ```
- All logs will automatically include the extra context provided by the filter and formatter.

## How to Use Database Queries and Schemes 📦

The combination of `app/lib/db/queries.py` and `app/lib/db/schemes.py` allows you to interact with the database in a clean, reusable, and asynchronous way using Tortoise ORM models and helper functions.

### 1. Define Data Models (schemes.py)
In `schemes.py`, you define your database tables as Python classes using Tortoise ORM. For example:
```python
class GuildSchema(models.Model):
    guild_id = fields.BigIntField(primary_key=True, unique=True)
    name = fields.CharField(max_length=255, null=True)
    # ... other fields ...

class MemberSchema(models.Model):
    discord_id = fields.BigIntField(primary_key=True, unique=True)
    username = fields.CharField(max_length=255, null=True)
    # ... other fields ...
```
These classes represent the structure of your tables and are used throughout your codebase.

### 2. Write Query Functions (queries.py)
In `queries.py`, you write async functions that use these models to fetch, create, or update records. For example:
```python
async def add_or_get_guild(guild: Guild) -> tuple[GuildSchema, bool]:
    db_guild, created = await GuildSchema.get_or_create(
        guild_id=guild.id,
        defaults={
            "name": guild.name,
            "icon_hash": str(guild.icon.url) if guild.icon else None,
            "owner_id": guild.owner_id if guild.owner_id else None,
        }
    )
    if not created and db_guild.name != guild.name:
        db_guild.name = guild.name
        await db_guild.save()
    return db_guild, created

async def add_or_get_member(member: Member) -> tuple[MemberSchema, GuildMemberSchema | None, bool]:
    db_member, created = await MemberSchema.get_or_create(
        discord_id=member.id,
        defaults={
            "username": member.name,
            "discriminator": member.discriminator,
            "avatar_hash": str(member.avatar.url) if member.avatar else None,
            "is_bot": member.bot,
            "updated_at": datetime.datetime.now(datetime.UTC)
        }
    )
    # ... update logic if not created ...
    return db_member, guild_member_db, created
```
These functions abstract away the details of database access, making your codebase easier to maintain.

### 3. Use Queries in Your Bot or Cogs
To use these queries, simply import and call them with the appropriate Discord.py objects:
```python
from app.lib.db.queries import add_or_get_member

# Inside an async function:
db_member, guild_member_db, created = await add_or_get_member(member)
```
You can then use the returned ORM model instances to access or update fields, and call `.save()` to persist changes.

### Summary
- Define your data structure in `schemes.py` using Tortoise ORM models.
- Write async query functions in `queries.py` to fetch, create, or update data.
- Use these query functions in your cogs or bot logic to interact with the database in a clean, reusable way.

## Setup 🚀
1. **Clone the repository**
2. **Install dependencies** (if any, e.g. `pip install -r requirements.txt`)
3. **Configure the bot** (edit config files or environment variables as needed)
4. **Run the bot**
   ```bash
   python launcher.py
   ```

## Testing 🧪
Run unit tests with:
```bash
python -m unittest discover test
```

## License 📄

This project is licensed under the MIT License.

---
*Feel free to update this README with more specific details about your project, usage, and configuration.*
