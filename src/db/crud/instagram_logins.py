from datetime import datetime, timedelta

from sqlalchemy import select, update

from src.db.models import InstagramLogins


async def update_login(session, new_login_data: InstagramLogins) -> None:
    await session.execute(
        update(InstagramLogins)
        .where(InstagramLogins.username == new_login_data.username)
        .values(
            user_id=new_login_data.user_id,
            followers=new_login_data.followers,
            is_exists=True,
            updated_at=new_login_data.updated_at,
        )
    )
    await session.commit()


async def update_login_list(session, login_list: list[InstagramLogins]) -> None:
    for login in login_list:
        login.updated_at = datetime.now()
        await session.execute(
            update(InstagramLogins)
            .where(InstagramLogins.username == login.username)
            .values(
                updated_at=login.updated_at, user_id=login.user_id, followers=login.followers, is_exists=login.is_exists
            )
        )
    await session.commit()


async def get_login_all(session) -> list[InstagramLogins]:
    not_updated_logins_result = await session.execute(
        select(InstagramLogins).filter(InstagramLogins.updated_at == None)
    )
    not_updated_logins = not_updated_logins_result.scalars().all()

    cutoff_date = datetime.now() - timedelta(days=1)
    updated_logins_result = await session.execute(
        select(InstagramLogins)
        .where(InstagramLogins.is_exists == True, InstagramLogins.updated_at < cutoff_date)
        .order_by(InstagramLogins.updated_at)
    )
    updated_logins = updated_logins_result.scalars().all()

    not_updated_logins.extend(updated_logins)
    return not_updated_logins


async def mark_as_not_exists(session, username: str) -> None:
    await session.execute(
        update(InstagramLogins)
        .where(InstagramLogins.username == username)
        .values(is_exists=False, updated_at=datetime.now())
    )
    await session.commit()
