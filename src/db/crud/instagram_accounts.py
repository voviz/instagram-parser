from datetime import datetime, timedelta
import random

import pytz
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logs import custom_logger
from src.db.crud.proxies import get_proxy_all, ProxyTypes
from src.db.models import InstagramAccounts
from src.db.exceptions import NoAccountsDBError, NoProxyDBError


async def get_accounts_all(session: AsyncSession) -> list[InstagramAccounts]:
    result = await session.execute(select(InstagramAccounts))
    return result.scalars().all()


async def get_accounts_without_proxy(session: AsyncSession) -> list[InstagramAccounts]:
    result = await session.execute(select(InstagramAccounts).filter(InstagramAccounts.proxy == None))
    return result.scalars().all()


async def get_account(session: AsyncSession) -> InstagramAccounts:
    query = select(InstagramAccounts).filter(
        InstagramAccounts.proxy != None, InstagramAccounts.daily_usage_rate < settings.ACCOUNT_DAILY_USAGE_RATE
    )
    account_list = await session.execute(query.filter(InstagramAccounts.last_used_at == None).limit(10))
    account_list = account_list.scalars().all()

    if not account_list:
        account_list = await session.execute(query.order_by(InstagramAccounts.last_used_at).limit(10))
        account_list = account_list.scalars().all()

    if not account_list:
        await update_accounts_daily_usage_rate(session)
        raise NoAccountsDBError('No account found for parsing')

    account = random.choice(account_list)

    # Logic for updating the selected account
    if account.last_used_at and (datetime.now(pytz.utc) - account.last_used_at) >= timedelta(days=1):
        await session.execute(
            update(InstagramAccounts)
            .where(InstagramAccounts.credentials == account.credentials)
            .values(last_used_at=datetime.now(), daily_usage_rate=0)
        )
    else:
        await session.execute(
            update(InstagramAccounts)
            .where(InstagramAccounts.credentials == account.credentials)
            .values(
                last_used_at=datetime.now(),
                daily_usage_rate=InstagramAccounts.daily_usage_rate + 1
            )
        )
    await session.commit()
    return account


async def update_accounts_daily_usage_rate(session: AsyncSession) -> None:
    accounts = await get_accounts_all(session)
    for acc in accounts:
        if acc.last_used_at and (datetime.now(pytz.utc) - acc.last_used_at).days >= 1:
            await session.execute(
                update(InstagramAccounts)
                .where(InstagramAccounts.credentials == acc.credentials)
                .values(daily_usage_rate=0)
            )
        elif acc.daily_usage_rate > 0:
            await session.execute(
                update(InstagramAccounts)
                .where(InstagramAccounts.credentials == acc.credentials)
                .values(daily_usage_rate=0)
            )
    await session.commit()


async def set_proxy_for_accounts(session: AsyncSession, accounts: list[InstagramAccounts]) -> None:
    for account in accounts:
        await session.execute(
            update(InstagramAccounts)
            .where(InstagramAccounts.credentials == account.credentials)
            .values(proxy=account.proxy)
        )
    await session.commit()


async def delete_account(session: AsyncSession, account: InstagramAccounts) -> None:
    await session.delete(account)
    await session.commit()


async def add_new_accounts(session: AsyncSession) -> bool:
    # get new accs and union with proxies
    if new_accounts := await get_accounts_without_proxy(session):
        proxies = await get_proxy_all(session, ProxyTypes.parser)
        if not proxies:
            raise NoProxyDBError(ProxyTypes.parser)
        for i, acc in enumerate(new_accounts):
            acc.proxy = proxies[i % len(proxies)].proxy
        await set_proxy_for_accounts(session, new_accounts)
        custom_logger.info(f'{len(new_accounts)} new accounts added!')
        return True
    return False
