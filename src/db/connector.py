from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.core.config import settings

DATABASE_URL = (
    f'postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}'
    f'@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}'
)

engine = create_async_engine(DATABASE_URL, connect_args={"timeout": 30}, pool_size=50, max_overflow=0)
async_session = async_sessionmaker(engine, expire_on_commit=False)
