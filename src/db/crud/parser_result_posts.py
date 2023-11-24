from sqlalchemy.dialects.postgresql import insert

from src.db.models import ParserResultPost
from src.parser.clients.models import InstagramClientAnswer


async def add_posts_result_list(session, result: InstagramClientAnswer) -> list[ParserResultPost]:
    async with session() as s:
        db_values_list = []
        if result.posts_list:
            for post in result.posts_list:
                db_values_list.append(
                    {
                        'post_id': post.post_id,
                        'user_id': result.user_id,
                        'link': post.url,
                        'comments_count': post.comments_count,
                        'likes_count': post.likes_count,
                        'publication_date': post.created_at,
                    }
                )

        unique_dicts = list({tuple(sorted(d.items())): d for d in db_values_list}.values())
        result_posts = []
        for values in unique_dicts:
            query = insert(ParserResultPost).values(values)
            result = await s.execute(
                query.on_conflict_do_update(
                    constraint='parser_result_post_post_id', set_={col: getattr(query.excluded, col) for col in values}
                ).returning(ParserResultPost)
            )
            result_posts.append(result.scalar())
        await s.commit()

        return result_posts
