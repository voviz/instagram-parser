from tortoise.expressions import Q

from db.models import InstagramLogins
from parser.clients.models import InstagramClientAnswer


class InstagramLoginsTableDBHandler:
    @classmethod
    async def update_login(cls, new_login_data: InstagramClientAnswer) -> None:
        await InstagramLogins.filter(username=new_login_data.username).update(user_id=new_login_data.user_id,
                                                                              followers=new_login_data.followers_number)

    @classmethod
    async def get_login(cls) -> InstagramLogins:
        return await InstagramLogins.filter(Q(update_at=None) | Q(is_exists=True)).order_by('update_at').first()

    @classmethod
    async def get_login_all(cls) -> list[InstagramLogins]:
        return await InstagramLogins.filter(Q(update_at=None) | Q(is_exists=True)).all().order_by('update_at')