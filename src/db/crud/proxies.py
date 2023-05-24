from db.models import Proxies


class ProxiesTableDBHandler:
    @classmethod
    async def get_proxy(cls) -> Proxies:
        return await Proxies.all().order_by('created_at').first()