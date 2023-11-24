from datetime import datetime, timedelta

from sqlalchemy import select, update, delete

from src.db.models import InstagramLogins


async def update_login(session, new_login_data: InstagramLogins) -> None:
    stmt = select(InstagramLogins).where(InstagramLogins.user_id == new_login_data.user_id)
    old = await session.execute(stmt).first()
    if old:
        session.execute(delete(InstagramLogins).where(InstagramLogins.id == new_login_data.id))
        await session.commit()
        return
    await session.execute(
        update(InstagramLogins)
        .where(InstagramLogins.username == new_login_data.username)
        .values(
            user_id=new_login_data.user_id,
            followers=new_login_data.followers,
            is_exists=True,
            updated_at=new_login_data.updated_at,
            posts_updated_at=new_login_data.posts_updated_at,
        )
    )
    await session.commit()


async def update_new_login_ids(session, login_list: list[InstagramLogins]) -> None:
    for login in login_list:
        login.updated_at = datetime.now()
        await update_login(session, login)

async def update_login_list(session, login_list: list[InstagramLogins]) -> None:
    raw_mappings = []
    for login in login_list:
        login.updated_at = datetime.now()
        login_mapping = dict(login.__dict__)
        login_mapping.pop('_sa_instance_state', None)
        raw_mappings.append(login_mapping)

    await session.execute(update(InstagramLogins), raw_mappings)
    await session.commit()


async def get_logins_for_update(session) -> list[InstagramLogins]:
    not_updated_logins_query = await session.execute(select(InstagramLogins).filter(InstagramLogins.updated_at == None))
    not_updated_logins = not_updated_logins_query.scalars().all()

    cutoff_date = datetime.now() - timedelta(days=1)
    updated_logins_query = await session.execute(
        select(InstagramLogins)
        .where(InstagramLogins.is_exists == True, InstagramLogins.updated_at < cutoff_date)
        .order_by(InstagramLogins.updated_at)
    )
    updated_logins = updated_logins_query.scalars().all()
    not_updated_logins.extend(updated_logins)

    return not_updated_logins


async def mark_as_not_exists(session, username: str = None, user_id: int = None) -> None:
    if username:
        query = (
            update(InstagramLogins)
            .where(InstagramLogins.username == username)
            .values(is_exists=False, updated_at=datetime.now())
        )
    else:
        query = (
            update(InstagramLogins)
            .where(InstagramLogins.user_id == user_id)
            .values(is_exists=False, updated_at=datetime.now())
        )
    await session.execute(query)
    await session.commit()
