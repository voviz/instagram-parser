import tortoise
from tortoise.expressions import Q

from db.models import InstagramAccounts


class InstagramAccountsTableDBHandler:
    @classmethod
    async def get_accounts_all(cls) -> list[InstagramAccounts]:
        return await InstagramAccounts.all()

    @classmethod
    async def get_accounts_without_proxy(cls) -> list[InstagramAccounts]:
        return await InstagramAccounts.filter(proxy=None).all()

    async def delete_account(self, account: InstagramAccounts) -> None:
        await account.delete()

    @classmethod
    async def get_account(cls) -> InstagramAccounts:
        query = InstagramAccounts.filter(proxy=~Q(proxy=None)).order_by('last_used_at')
        # update last_used_at field
        await query.update(last_used_at=tortoise.timezone.now())
        return await query.first()