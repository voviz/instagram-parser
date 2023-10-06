import random
from enum import Enum

from sqlalchemy import select

from src.db.models import Proxies


class ProxyTypes(Enum):
    ozon = 'ozon'
    parser = 'parser'


async def get_proxy_all(session, proxy_type: ProxyTypes) -> list[Proxies]:
    result = await session.execute(select(Proxies).where(Proxies.type == proxy_type.value))
    return result.scalars().all()


async def get_random_proxy(session, proxy_type: ProxyTypes) -> Proxies:
    query = await session.execute(select(Proxies).where(Proxies.type == proxy_type.value))
    result = query.scalars().all()
    return result[random.randint(0, len(result))]