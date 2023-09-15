import bs4

from db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from parser.clients.base import BaseThirdPartyAPIClient


class OzonClient(BaseThirdPartyAPIClient):
    """
    Custom instagram API
    """
    api_name = 'OzonAPI'
    base_url = 'https://www.ozon.ru'

    async def check_sku(self, sku: int) -> bool:
        # get account credentials from db
        account = await InstagramAccountsTableDBHandler.get_account()
        raw_data = await self.request(
            method=BaseThirdPartyAPIClient.HTTPMethods.GET.value,
            edge='search',
            querystring={'text': str(sku), 'from_global': 'true'},
            is_json=False,
            # do not use proxy due to only Russia region works correctly
            user_agent=account.user_agent,
        )
        # find categories links on the page
        page = bs4.BeautifulSoup(raw_data, 'lxml')
        find_header = page.find(class_='yu6')
        if find_header and 'найден 1 товар' not in find_header.text.lower():
            return True
        return False

    @staticmethod
    def extract_sku_from_url(url: str):
        if 'ozon' in url:
            if 'product_id' in url:
                return int(url.split('product_id=')[1])
            if '/product/' in url:
                return int(url.split('/')[-2].split('-')[-1])
        return None
