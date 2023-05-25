from tortoise.expressions import Q

from db.models import InstagramLogins


class InstagramLoginsTableDBHandler:
    @classmethod
    async def update_login(cls, login: InstagramLogins, **kwargs) -> None:
        await InstagramLogins.filter(username=login.username).update(**kwargs)

    @classmethod
    async def get_login(cls) -> InstagramLogins:
        return await InstagramLogins.filter(Q(update_at=None) | Q(is_exists=True)).order_by('update_at').first()
