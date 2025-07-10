import asyncio
import atexit
import signal
from typing import Coroutine, Any, Sequence

from tortoise import Tortoise, connections, BaseDBAsyncClient


class DatabaseManager:
    _initialized = False

    def __init__(self, db_url: str, modules: dict, generate_schemas: bool = False):
        self.db_url = db_url
        self.modules = modules
        self.generate_schemas = generate_schemas

        atexit.register(self._sync_close)
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda signum, frame: self._sync_close())

    async def connect(self) -> None:
        if not self._initialized:
            await Tortoise.init(
                db_url=self.db_url,
                modules=self.modules
            )
            if self.generate_schemas:
                await Tortoise.generate_schemas()
            DatabaseManager._initialized = True

    @staticmethod
    async def close() -> None:
        await Tortoise.close_connections()
        DatabaseManager._initialized=False

    def _sync_close(self) -> None:
        try:
            # Questo crea un nuovo loop SE non c’è uno in esecuzione,
            # altrimenti usa quello corrente (e fallirà, cadendo in except).
            asyncio.run(self.close())
        except RuntimeError:
            # Se siamo già dentro un loop in esecuzione (signal handler),
            # schedula semplicemente la close sul thread loop-safe.
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(asyncio.create_task, self.close())

    @property
    def connection(self) -> BaseDBAsyncClient:
        return connections.get("default")

    async def execute_raw(self, query: str, values: list | None) -> tuple[int, Sequence[dict]]:
        return await self.connection.execute_query(query, values)

    async def execute_raw_fetch(self, query: str, values: list | None) -> list[dict]:
        return await self.connection.execute_query_dict(query, values)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, tb: Any) -> None:
        await self.close()