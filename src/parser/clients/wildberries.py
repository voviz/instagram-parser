from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from src.parser.clients.models import InstagramStory, InstagramPost
from src.db.crud.instagram_accounts import get_account
from src.parser.clients.base import BaseThirdPartyAPIClient


class WildberriesClient(BaseThirdPartyAPIClient):
    """
    A client to interact with Wildberries' website, particularly for SKU checks.
    """

    api_name = 'WildberrisAPI'
    base_url = 'https://card.wb.ru'
    regions = '80,115,38,4,64,83,33,68,70,69,30,86,75,40,1,66,110,22,31,48,71,114'

    async def check_sku(self, async_session: AsyncSession, item: InstagramStory | InstagramPost) -> bool:
        """
        Checks the existence of a SKU on the Wildberries website.

        Args:
            item (int): The item with SKU to check
        Returns:
            bool: True if SKU exists, False otherwise.
        """
        async with async_session() as s:
            account = await get_account(s)

        raw_data = await self.request(
            method=BaseThirdPartyAPIClient.HTTPMethods.GET,
            edge='cards/detail',
            querystring={
                'regions': self.regions,
                'nm': str(item.sku),
            },
            is_json=True,
            proxy=account.proxy,
            user_agent=account.user_agent,
        )

        if products := raw_data.get('data', {}).get('products'):
            item.brand = products[0].get('brand')
            item.brand_id = products[0].get('brandId')

        return bool(products)

    @staticmethod
    def extract_sku_from_url(url: str) -> int | None:
        """
        Extract SKU from a given Wildberries URL.

        Args:
            url (str): The URL to extract SKU from.

        Returns:
            int: The extracted SKU or None if not found.
        """
        if 'wildberries' in url:
            parsed_url = urlparse(url)
            if '/catalog/' in parsed_url.path:
                return int(parsed_url.path.split('/catalog/')[1].split('/')[0])
        return None
