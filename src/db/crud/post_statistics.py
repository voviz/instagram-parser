from sqlalchemy.dialects.postgresql import insert

from src.db.models import PostStatistics
from src.parser.clients.models import InstagramClientAnswer


async def add_post_statistics_list(session, result_list: list[InstagramClientAnswer]) -> None:
    db_values_list = []
    for result in result_list:
        if result.posts_list:
            for post in result.posts_list:
                db_values_list.append(
                    {
                        'post_id': result.post_id,
                        'link': post.url,
                        'comments_count': post.comments_count,
                        'likes_count': post.likes_count,
                    }
                )

    if db_values_list:
        # If using PostgreSQL, consider on_conflict_do_nothing for ignoring conflicts.
        await session.execute(insert(PostStatistics).values(db_values_list).on_conflict_do_nothing())
        await session.commit()
