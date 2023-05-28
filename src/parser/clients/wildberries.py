from db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from parser.clients.base import BaseThirdPartyAPIClient


class WildberrisClient(BaseThirdPartyAPIClient):
    """
    Custom instagram API
    """
    api_name = 'WildberrisAPI'
    base_url = 'https://card.wb.ru'

    async def check_sku(self, sku: int) -> bool:
        # get account credentials from db
        account = await InstagramAccountsTableDBHandler.get_account()
        raw_data = await self.request(
            method=BaseThirdPartyAPIClient.HTTPMethods.GET,
            edge='cards/detail',
            querystring={'regions': '80,115,38,4,64,83,33,68,70,69,30,86,75,40,1,66,110,22,31,48,71,114',
                         'nm': str(sku)},
            is_json=True,
            proxy=account.proxy,
            user_agent=account.user_agent,
        )
        if raw_data['data']['products']:
            return True
        return False

    @staticmethod
    def extract_sku_from_url(url: str):
        if 'wildberries' in url:
            return int(url.split('/')[-2])
        return None
