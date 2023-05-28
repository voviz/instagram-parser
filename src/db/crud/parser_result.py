from db.models import ParserResult
from parser.clients.models import InstagramClientAnswer


class ParserResultTableDBHandler:
    @classmethod
    async def update_result(cls, login: InstagramClientAnswer) -> None:
        if login.stories_list:
            for story in login.stories_list:
                if story.sku:
                    await ParserResult.update_or_create(instagram_username=login.username,
                                                        marketplace=story.marketplace,
                                                        story_publication_date=story.created_at,
                                                        sku=story.sku,
                                                        ad_type=story.ad_type,
                                                        defaults={'marketplace': story.marketplace,
                                                                  'story_publication_date': story.created_at,
                                                                  'sku': story.sku,
                                                                  'ad_type': story.ad_type, })
                    break

    @classmethod
    async def get_result_by_username(cls, username: str) -> ParserResult:
        return await ParserResult.filter(instagram_username=username).first()

