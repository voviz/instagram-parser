from db.models import Proxies


class ProxiesTableDBHandler:
    @classmethod
    async def get_parser_proxies_all(cls) -> list[Proxies]:
        return await Proxies.filter(type='parser').all()

    @classmethod
    async def get_ozon_proxy(cls) -> Proxies:
        return await Proxies.filter(type='ozon').first()