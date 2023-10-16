from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncEngine, create_async_engine

from src.core.config import settings


DATABASE_URL = (
    f'postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}'
    f'@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}'
)


def get_db_pool():
    return create_async_engine(DATABASE_URL, connect_args={'timeout': 30}, pool_size=50, max_overflow=0)


def get_async_sessionmaker(engine: AsyncEngine):
    return async_sessionmaker(engine, expire_on_commit=False)
