from db.models import ParserResult
from parser.clients.models import InstagramClientAnswer


class ParserResultTableDBHandler:
    @classmethod
    async def add_result(cls, login: InstagramClientAnswer) -> None:
        if login.stories_list:
            for story in login.stories_list:
                await ParserResult.create(instagram_username=login.username,
                                          marketplace=story.marketplace.value,
                                          story_publication_date=story.created_at,
                                          sku=story.sku,
                                          ad_type=story.ad_type.value,)

    @classmethod
    async def get_result_by_username(cls, username: str) -> ParserResult:
        return await ParserResult.filter(instagram_username=username).first()
