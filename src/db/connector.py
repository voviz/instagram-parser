import asyncio

from tortoise import Tortoise

from src.core.config import settings


class DatabaseConnector:
    @classmethod
    def sync_init(cls):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(cls.async_init())

    @classmethod
    async def async_init(cls):
        await Tortoise.init(
            db_url=f'asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@'
                   f'{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}',
            modules={'models': ['db.models']},
        )
        # Generate the schema
        # safe=True - generate schema if not exists in db
        await Tortoise.generate_schemas(safe=True)

    @classmethod
    async def close(self):
        await Tortoise.close_connections()
