import asyncio
import logging

from tortoise import Tortoise

from src.core.settings import settings

log = logging.getLogger(__name__)


class DatabaseConnector:
    def __init__(self):
        self._sync_init()

    async def _async_init(self):
        await Tortoise.init(
            db_url=f'asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@'
                   f'{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}',
            modules={'models': ['db.models']},
        )
        # Generate the schema
        # safe=True - generate schema if not exists in db
        await Tortoise.generate_schemas(safe=True)

    def _sync_init(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._async_init())


database_connector = DatabaseConnector()
