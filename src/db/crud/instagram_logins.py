import tortoise

from db.models import InstagramLogins
from parser.clients.models import InstagramClientAnswer


class InstagramLoginsTableDBHandler:
    @classmethod
    async def update_login(cls, new_login_data: InstagramClientAnswer) -> None:
        await InstagramLogins.filter(username=new_login_data.username).update(user_id=new_login_data.user_id,
                                                                              followers=new_login_data.followers_number,
                                                                              is_exists=True,
                                                                              updated_at=tortoise.timezone.now())

    @classmethod
    async def update_login_list(cls, login_list: list[InstagramLogins]) -> None:
        # update 'updated_at' field
        for login in login_list:
            login.updated_at = tortoise.timezone.now()
        await InstagramLogins.bulk_update(login_list, fields=['updated_at'])

    @classmethod
    async def get_login_all(cls) -> list[InstagramLogins]:
        not_updated_logins = await InstagramLogins.filter(updated_at=None).all()
        updated_logins = await InstagramLogins.filter(is_exists=True).all().order_by('updated_at')
        not_updated_logins.extend(updated_logins)
        return not_updated_logins

    @classmethod
    async def mark_as_not_exists(cls, username: str) -> None:
        await InstagramLogins.filter(username=username).update(is_exists=False,
                                                               updated_at=tortoise.timezone.now())
