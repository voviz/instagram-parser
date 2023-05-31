from core.logs import custom_logger
from db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from db.crud.proxies import ProxiesTableDBHandler, ProxyTypes
from parser.exceptions import NoProxyDBError, NotEnoughProxyDBError


def add_new_accounts() -> bool:
    # get new accs and union with proxies
    if new_accounts := await InstagramAccountsTableDBHandler.get_accounts_without_proxy():
        proxies = await ProxiesTableDBHandler.get_proxy_all(ProxyTypes.parser)
        if not proxies:
            raise NoProxyDBError(ProxyTypes.parser)
        if len(new_accounts) // len(proxies) > 10:
            raise NotEnoughProxyDBError(len(new_accounts), len(proxies))
        for i, acc in enumerate(new_accounts):
            acc.proxy = proxies[i % len(proxies)].proxy
        await InstagramAccountsTableDBHandler.set_proxy_for_accounts(new_accounts)
        custom_logger.info('{} new accounts added!'.format(len(new_accounts)))
        return True
    return False