import random

import tortoise
from tortoise.expressions import Q

from core.settings import settings
from db.models import InstagramAccounts
from parser.exceptions import NoAccountsDBError


class InstagramAccountsTableDBHandler:
    @classmethod
    async def get_accounts_all(cls) -> list[InstagramAccounts]:
        return await InstagramAccounts.all()

    @classmethod
    async def get_accounts_without_proxy(cls) -> list[InstagramAccounts]:
        return await InstagramAccounts.filter(proxy=None).all()

    @classmethod
    async def get_account(cls) -> InstagramAccounts:
        query = InstagramAccounts.filter(
            ~Q(proxy=None) & Q(daily_usage_rate__lt=settings.ACCOUNT_DAILY_USAGE_RATE)
        )
        # filter not used accs
        if not (account_list := await query.filter(last_used_at=None).limit(10).all()):
            account_list = await query.order_by('last_used_at').limit(10).all()
            if not account_list:
                await cls.update_accounts_daily_usage_rate()
                raise NoAccountsDBError('No account found for parsing')
        # to add randomness to db
        account = account_list[random.randint(0, len(account_list) - 1)]
        if account.last_used_at and (tortoise.timezone.now() - account.last_used_at).seconds // 3600 >= 24:
            # update last_used_at field
            await InstagramAccounts.filter(credentials=account.credentials).update(last_used_at=tortoise.timezone.now(),
                                                                                   daily_usage_rate=0)
        else:
            # update last_used_at field
            await InstagramAccounts.filter(credentials=account.credentials).update(last_used_at=tortoise.timezone.now(),
                                                                                   daily_usage_rate=await cls._get_account_daily_usage_rate(
                                                                                       account) + 1)
        return account

    @classmethod
    async def _get_account_daily_usage_rate(cls, account: InstagramAccounts) -> int:
        return (await InstagramAccounts.filter(credentials=account.credentials).first()).daily_usage_rate

    @classmethod
    async def update_accounts_daily_usage_rate(cls) -> None:
        accounts = await InstagramAccounts.filter(~Q(last_used_at=None)).all()
        for acc in accounts:
            if acc.last_used_at and (tortoise.timezone.now() - acc.last_used_at).seconds // 3600 >= 24:
                # update last_used_at field
                await InstagramAccounts.filter(credentials=acc.credentials).update(last_used_at=tortoise.timezone.now(),
                                                                                   daily_usage_rate=0)

    @classmethod
    async def set_proxy_for_accounts(cls, accounts: list[InstagramAccounts]) -> None:
        if accounts:
            await InstagramAccounts.bulk_update(accounts, ['proxy'])

    @classmethod
    async def delete_account(cls, account: InstagramAccounts) -> None:
        await account.delete()
