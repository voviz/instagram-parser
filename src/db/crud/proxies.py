from enum import Enum

from src.db.models import Proxies


class ProxyTypes(Enum):
    ozon = 'ozon'
    parser = 'parser'


class ProxiesTableDBHandler:
    @classmethod
    async def get_proxy_all(cls, proxy_type: ProxyTypes) -> list[Proxies]:
        return await Proxies.filter(type=proxy_type.value).all()
