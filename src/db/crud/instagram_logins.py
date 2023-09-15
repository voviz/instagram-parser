from datetime import timedelta

import tortoise
from tortoise.expressions import Q

from db.models import InstagramLogins
from parser.clients.models import InstagramClientAnswer


class InstagramLoginsTableDBHandler:
    @classmethod
    async def update_login(cls, new_login_data: InstagramLogins) -> None:
        await InstagramLogins.filter(username=new_login_data.username).update(user_id=new_login_data.user_id,
                                                                              followers=new_login_data.followers,
                                                                              is_exists=True,
                                                                              updated_at=new_login_data.updated_at)

    @classmethod
    async def update_login_list(cls, login_list: list[InstagramLogins]) -> None:
        # update 'updated_at' field
        for login in login_list:
            login.updated_at = tortoise.timezone.now()
            await cls.update_login(login)
        # await InstagramLogins.bulk_update(login_list, fields=['updated_at', 'user_id', 'followers', 'is_exists'])

    @classmethod
    async def get_login_all(cls) -> list[InstagramLogins]:
        not_updated_logins = await InstagramLogins.filter(updated_at=None).all()
        updated_logins = await InstagramLogins.filter(
            Q(is_exists=True) & Q(updated_at__lt=tortoise.timezone.now() - timedelta(days=1))
        ).all().order_by('updated_at')
        not_updated_logins.extend(updated_logins)
        return not_updated_logins

    @classmethod
    async def mark_as_not_exists(cls, username: str) -> None:
        await InstagramLogins.filter(username=username).update(is_exists=False,
                                                               updated_at=tortoise.timezone.now())
