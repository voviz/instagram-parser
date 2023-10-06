from src.db.crud.proxies import ProxyTypes
from src.exceptions import BaseParserException


class NoAccountsDBError(BaseParserException):
    def __str__(self):
        return 'No accounts to work with in db ...'


class NoProxyDBError(BaseParserException):
    def __init__(self, proxy_type: ProxyTypes):
        self.proxy_type = proxy_type

    def __str__(self):
        if self.proxy_type == ProxyTypes.parser:
            return f'No proxies of type {self.proxy_type}! Cannot add new accounts in db ...'
        else:
            return f'No proxies of type {self.proxy_type} to work with in db ...'


class NotEnoughProxyDBError(BaseParserException):
    def __init__(self, account_count: int, proxy_count: int):
        self.proxy_count = proxy_count
        self.account_count = account_count

    def __str__(self):
        return (
            f'Not enough proxies in db ....\n'
            f'Cannot add new accounts in db ...'
            f'You have to add {self.account_count // 10 - self.proxy_count} more proxies'
        )