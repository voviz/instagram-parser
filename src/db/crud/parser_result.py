from sqlalchemy.dialects.postgresql import insert

from src.db.models import ParserResult
from src.parser.clients.models import InstagramClientAnswer


async def add_result_list(session, result_list: list[InstagramClientAnswer]) -> None:
    db_values_list = []
    for result in result_list:
        if result.stories_list:
            for story in result.stories_list:
                db_values_list.append(
                    {
                        'instagram_username': result.username,
                        'marketplace': story.marketplace.value,
                        'publication_date': story.created_at,
                        'sku': story.sku,
                        'ad_type': story.ad_type.value,
                    }
                )

    if db_values_list:
        # If using PostgreSQL, consider on_conflict_do_nothing for ignoring conflicts.
        await session.execute(insert(ParserResult).values(db_values_list).on_conflict_do_nothing())
        await session.commit()
