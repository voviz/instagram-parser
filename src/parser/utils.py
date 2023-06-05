from seleniumbase import get_driver

from core.logs import custom_logger
from db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from db.crud.proxies import ProxiesTableDBHandler, ProxyTypes
from parser.exceptions import NoProxyDBError


async def add_new_accounts() -> bool:
    # get new accs and union with proxies
    if new_accounts := await InstagramAccountsTableDBHandler.get_accounts_without_proxy():
        proxies = await ProxiesTableDBHandler.get_proxy_all(ProxyTypes.parser)
        if not proxies:
            raise NoProxyDBError(ProxyTypes.parser)
        for i, acc in enumerate(new_accounts):
            acc.proxy = proxies[i % len(proxies)].proxy
        await InstagramAccountsTableDBHandler.set_proxy_for_accounts(new_accounts)
        custom_logger.info('{} new accounts added!'.format(len(new_accounts)))
        return True
    return False


def check_driver_installation() -> None:
    driver = get_driver("chrome", headless=True)
    driver.get("https://www.google.com/chrome")
    driver.quit()


def chunks(lst: list, n: int):
    """
    Yield successive n-sized chunks from lst.
    @param lst: list of data
    @param n: number of chunks to separate
    @return: iterator
    """
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
