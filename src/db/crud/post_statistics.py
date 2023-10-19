from sqlalchemy.dialects.postgresql import insert

from src.db.models import PostStatistics
from src.parser.clients.models import InstagramClientAnswer


async def add_post_statistics_list(session, result: InstagramClientAnswer) -> None:
    db_values_list = []
    if result.posts_list:
        for post in result.posts_list:
            db_values_list.append(
                {
                    'post_id': post.post_id,
                    'link': post.url,
                    'comments_count': post.comments_count,
                    'likes_count': post.likes_count,
                }
            )

    unique_dicts = list({tuple(sorted(d.items())): d for d in db_values_list}.values())
    for values in unique_dicts:
        query = insert(PostStatistics).values(values)
        await session.execute(
            query.on_conflict_do_update(
                constraint='post_statistics_pk', set_={col: getattr(query.excluded, col) for col in values}
            )
        )
    await session.commit()
