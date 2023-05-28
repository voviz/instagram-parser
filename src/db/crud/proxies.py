from enum import StrEnum

from db.models import Proxies


class ProxyTypes(StrEnum):
    ozon = 'ozon'
    parser = 'parser'


class ProxiesTableDBHandler:
    @classmethod
    async def get_parser_proxies_all(cls) -> list[Proxies]:
        return await Proxies.filter(type=ProxyTypes.parser.value).all()

    @classmethod
    async def get_ozon_proxy(cls) -> Proxies:
        return await Proxies.filter(type=ProxyTypes.ozon.value).first()
