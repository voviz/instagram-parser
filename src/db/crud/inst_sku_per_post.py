from sqlalchemy.dialects.postgresql import insert

from src.db.models import InstSkuPerPost, ParserResultPost
from src.parser.clients.models import InstagramClientAnswer


async def add_inst_sku_per_post_list(session, result: InstagramClientAnswer, result_post_db: list[ParserResultPost]) -> None:
    db_values_list = []
    post_id_to_id_mapping = {p.post_id: p.id for p in result_post_db}
    if result.posts_list:
        for post in result.posts_list:
            db_values_list.append(
                {
                    'parser_result_post_id': post_id_to_id_mapping[post.post_id],
                    'marketplace': post.marketplace.value,
                    'sku': int(post.sku),
                    'brand': post.brand,
                    'brand_id': post.brand_id,
                }
            )

    if db_values_list:
        # If using PostgreSQL, consider on_conflict_do_nothing for ignoring conflicts.
        await session.execute(insert(InstSkuPerPost).values(db_values_list).on_conflict_do_nothing())
        await session.commit()
