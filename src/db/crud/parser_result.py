from db.models import ParserResult


class ParserResultTableDBHandler:
    @classmethod
    async def update_result(cls, login: ParserResult, **kwargs) -> None:
        await ParserResult.update_or_create(login.instagram_username, **kwargs, defaults={**kwargs})
