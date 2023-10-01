from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.db.models import ParserResult
from src.parser.clients.models import InstagramClientAnswer


async def add_result(session, login: InstagramClientAnswer) -> None:
    if login.stories_list:
        for story in login.stories_list:
            result = ParserResult(
                instagram_username=login.username,
                marketplace=story.marketplace.value,
                story_publication_date=story.created_at,
                sku=story.sku,
                ad_type=story.ad_type.value,
            )
            session.add(result)
        await session.commit()


async def add_result_list(session, login_list: list[InstagramClientAnswer]) -> None:
    result_list = []
    for login in login_list:
        if login.stories_list:
            for story in login.stories_list:
                result_list.append(
                    {
                        'instagram_username': login.username,
                        'marketplace': story.marketplace.value,
                        'story_publication_date': story.created_at,
                        'sku': story.sku,
                        'ad_type': story.ad_type.value,
                    }
                )

    if result_list:
        # If using PostgreSQL, consider on_conflict_do_nothing for ignoring conflicts.
        await session.execute(insert(ParserResult).values(result_list).on_conflict_do_nothing())
        await session.commit()


async def get_result_by_username(session, username: str) -> ParserResult:
    result = await session.execute(select(ParserResult).where(ParserResult.instagram_username == username))
    return result.scalars().first()
