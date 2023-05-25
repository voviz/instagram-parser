from db.models import Proxies


class ProxiesTableDBHandler:
    @classmethod
    async def get_proxies_all(cls) -> list[Proxies]:
        return await Proxies.all()