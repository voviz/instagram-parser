from enum import StrEnum

from db.models import Proxies


class ProxyTypes(StrEnum):
    ozon = 'ozon'
    parser = 'parser'


class ProxiesTableDBHandler:
    @classmethod
    async def get_proxy_all(cls, proxy_type: ProxyTypes) -> list[Proxies]:
        return await Proxies.filter(type=proxy_type.value).all()
