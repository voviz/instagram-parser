from datetime import datetime

import tortoise
from tortoise.expressions import Q

from core.settings import settings
from db.models import InstagramAccounts, Proxies
from parser.exceptions import NoAccountsDBError


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
        query = InstagramAccounts.filter(
            ~Q(proxy=None) & Q(daily_usage_rate__lt=settings.ACCOUNT_DAILY_USAGE_RATE)
        ).order_by('last_used_at')
        if not (account := await query.first()):
            await cls.update_accounts_daily_usage_rate()
            if not (account := await query.first()):
                raise NoAccountsDBError('No account found for parsing')
        if (datetime.now() - account.last_used_at).hour >= 24:
            # update last_used_at field
            await query.update(last_used_at=tortoise.timezone.now(),
                               daily_usage_rate=0)
        else:
            # update last_used_at field
            await query.update(last_used_at=tortoise.timezone.now(),
                               daily_usage_rate=await cls._get_account_daily_usage_rate(account) + 1)
        return account

    @classmethod
    async def _get_account_daily_usage_rate(cls, account: InstagramAccounts) -> int:
        return (await InstagramAccounts.filter(credentials=account.credentials).first()).daily_usage_rate

    @classmethod
    async def update_accounts_daily_usage_rate(cls) -> None:
        accounts = await InstagramAccounts.filter(~Q(last_used_at=None)).all()
        for acc in accounts:
            if (datetime.now() - acc.last_used_at).hour >= 24:
                # update last_used_at field
                await InstagramAccounts.filter(credentials=acc.credentials).update(last_used_at=tortoise.timezone.now(),
                                                                                   daily_usage_rate=0)

    @classmethod
    async def set_proxy_for_accounts(cls, accounts: list[tuple[InstagramAccounts, Proxies]]) -> None:
        for account, proxy in accounts:
            await InstagramAccounts.filter(credentials=account.credentials).update(proxy=proxy.proxy)
