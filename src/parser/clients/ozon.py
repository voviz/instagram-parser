import re
from urllib.parse import parse_qs, urlparse

# from selenium.webdriver.common.by import By
# from seleniumbase import SB

from src.parser.clients.base import BaseThirdPartyAPIClient


class OzonClient(BaseThirdPartyAPIClient):
    """
    A client to interact with Ozon's website, particularly for SKU checks.
    """

    api_name = 'OzonAPI'
    base_url = 'https://www.ozon.ru'
    FOUND_TEXT_PATTERN = r'найден[оа]? (\d+) товар[аов]?'

    # async def check_sku(self, sku: int) -> bool:
    #     """
    #     Checks the existence of a SKU on the Ozon website.
    #
    #     Args:
    #         sku (int): The SKU to check.
    #
    #     Returns:
    #         bool: True if SKU exists, False otherwise.
    #     """
    #     with SB(uc=True, headless2=True) as sb:
    #         sb.open(self.base_url + '/search/' + f'?text={sku}&from_global=true')
    #         sb.wait_for_element_present('__ozon', by=By.ID, timeout=5)
    #         page = sb.driver.page_source
    #     return bool(re.findall(self.FOUND_TEXT_PATTERN, page))

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
