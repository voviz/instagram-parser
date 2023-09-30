from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from src.db.connector import async_session
from src.db.crud.instagram_accounts import get_account
from src.parser.clients.base import BaseThirdPartyAPIClient


class OzonClient(BaseThirdPartyAPIClient):
    """
    A client to interact with Ozon's website, particularly for SKU checks.
    """
    api_name = 'OzonAPI'
    base_url = 'https://www.ozon.ru'
    NOT_FOUND_TEXT = 'найден 1 товар'

    async def check_sku(self, sku: int) -> bool:
        """
        Checks the existence of a SKU on the Ozon website.

        Args:
            sku (int): The SKU to check.

        Returns:
            bool: True if SKU exists, False otherwise.
        """
        async with async_session() as s:
            account = await get_account(s)

        raw_data = await self.request(
            method=BaseThirdPartyAPIClient.HTTPMethods.GET,
            edge='search',
            querystring={'text': str(sku), 'from_global': 'true'},
            is_json=False,
            user_agent=account.user_agent
        )

        page = BeautifulSoup(raw_data, 'lxml')
        find_header = page.find(class_='yu6')

        return bool(find_header and self.NOT_FOUND_TEXT not in find_header.text.lower())

    @staticmethod
    def extract_sku_from_url(url: str) -> int | None:
        """
        Extract SKU from a given Ozon URL.

        Args:
            url (str): The URL to extract SKU from.

        Returns:
            int: The extracted SKU or None if not found.
        """
        if 'ozon' in url:
            parsed_url = urlparse(url)
            if 'product_id' in parsed_url.query:
                return int(parse_qs(parsed_url.query)['product_id'][0])
            elif '/product/' in parsed_url.path:
                return int(parsed_url.path.split('/')[-2].split('-')[-1])
        return None
