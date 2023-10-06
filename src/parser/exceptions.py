from typing import Any

from src.db.crud.proxies import ProxyTypes
from src.db.models import InstagramAccounts


class BaseParserException(Exception):
    """Base class for all parser errors"""

    def __str__(self):
        return 'Something goes wrong with parser'


class ThirdPartyApiException(BaseParserException):
    def __init__(self, api_name: str, status: str, answer: Any):
        self.api_name = api_name
        self.status = status
        self.answer = answer

    def __str__(self):
        return f'{self.api_name} non-200 response. Status [{self.status}]: {self.answer}'


class LoginNotExistError(ThirdPartyApiException):
    def __init__(self, username: str = None, user_id: int = None):
        self.username = username
        self.user_id = user_id

    def __str__(self):
        if self.user_id:
            return f'Login with id "{self.user_id}" does not exist'
        if self.username:
            return f'Login with username {self.username} does not exist'


class AccountConfirmationRequired(ThirdPartyApiException):
    def __init__(self, account: InstagramAccounts):
        self.account = account

    def __str__(self):
        return f'For account {self.account.credentials} auth confirmation is required'


class AccountInvalidCredentials(ThirdPartyApiException):
    def __init__(self, account: InstagramAccounts):
        self.account = account

    def __str__(self):
        return f'Invalid credentials for account: {self.account.credentials}'


class AccountTooManyRequests(ThirdPartyApiException):
    def __init__(self, account: InstagramAccounts):
        self.account = account

    def __str__(self):
        return f'Too many requests from account: {self.account.credentials} ... Delete ...'


class ClosedAccountError(ThirdPartyApiException):
    def __init__(self, user_id: int):
        self.user_id = user_id

    def __str__(self):
        return f'Cannot parse from closed login with id: {self.user_id} ... '


class ProxyTooManyRequests(ThirdPartyApiException):
    def __init__(self, proxy: str):
        self.proxy = proxy

    def __str__(self):
        return f'Too many requests from proxy: {self.proxy} ...'


class InvalidProxyFormatError(BaseParserException):
    def __init__(self, proxy: str):
        self.proxy = proxy

    def __str__(self):
        return f'Invalid format of proxy: {self.proxy}'


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
