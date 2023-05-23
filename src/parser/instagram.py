from src.parser.base import BaseThirdPartyAPIClient


class InstagramClient(BaseThirdPartyAPIClient):
    """
    Custom instagram API
    """
    api_name = 'InstagramAPI'
    base_url = 'https://www.instagram.com/api/v1/'

    async def get_account_info_by_user_name(self, username: str):
        raw_data = await self.request(
            method=BaseThirdPartyAPIClient.HTTPMethods.GET,
            edge='users/web_profile_info',
            querystring={'username': username},
            is_json=True,
        )
        return raw_data

    async def get_account_stories_by_id(self, id: int):
        pass
