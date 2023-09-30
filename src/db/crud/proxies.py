from enum import Enum

from sqlalchemy import select

from src.db.models import Proxies


class ProxyTypes(Enum):
    ozon = 'ozon'
    parser = 'parser'


async def get_proxy_all(session, proxy_type: ProxyTypes) -> list[Proxies]:
    result = await session.execute(select(Proxies).where(Proxies.type == proxy_type.value))
    return result.scalars().all()
