from datetime import datetime, timedelta
import random

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.models import InstagramAccounts
from src.parser.exceptions import NoAccountsDBError


async def get_accounts_all(session: AsyncSession) -> list[InstagramAccounts]:
    result = await session.execute(select(InstagramAccounts))
    return result.scalars().all()


async def get_accounts_without_proxy(session) -> list[InstagramAccounts]:
    result = await session.execute(select(InstagramAccounts).filter(InstagramAccounts.proxy == None))
    return result.scalars().all()


async def get_account(session) -> InstagramAccounts:
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
    if account.last_used_at and (datetime.now() - account.last_used_at) >= timedelta(days=1):
        await session.execute(
            update(InstagramAccounts)
            .where(InstagramAccounts.credentials == account.credentials)
            .values(last_used_at=datetime.now(), daily_usage_rate=0)
        )
    else:
        daily_rate = await _get_account_daily_usage_rate(session, account)
        await session.execute(
            update(InstagramAccounts)
            .where(InstagramAccounts.credentials == account.credentials)
            .values(last_used_at=datetime.now(), daily_usage_rate=daily_rate + 1)
        )
    await session.commit()
    return account


async def _get_account_daily_usage_rate(session, account: InstagramAccounts) -> int:
    result = await session.execute(
        select(InstagramAccounts.daily_usage_rate).where(InstagramAccounts.credentials == account.credentials)
    )
    return result.scalar()


async def update_accounts_daily_usage_rate(session) -> None:
    accounts = await get_accounts_all(session)
    for acc in accounts:
        if acc.last_used_at and (datetime.now() - acc.last_used_at).days >= 1:
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


async def set_proxy_for_accounts(session, accounts: list[InstagramAccounts]) -> None:
    for account in accounts:
        await session.execute(
            update(InstagramAccounts)
            .where(InstagramAccounts.credentials == account.credentials)
            .values(proxy=account.proxy)
        )
    await session.commit()


async def delete_account(session, account: InstagramAccounts) -> None:
    await session.delete(account)
    await session.commit()
