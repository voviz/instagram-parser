from typing import Any

from core.settings import settings
from db.models import InstagramAccounts


class BaseParserException(Exception):
    """Base class for all parser errors"""

    def __str__(self):
        return "Something goes wrong with parser"


class ThirdPartyApiException(BaseParserException):
    def __init__(self, api_name: str, status: str, answer: Any):
        self.api_name = api_name
        self.status = status
        self.answer = answer

    def __str__(self):
        return f'{self.api_name} non-200 response. Status [{self.status}]: {self.answer}'


class LoginNotExist(ThirdPartyApiException):
    def __init__(self, account_name: str):
        self.account_name = account_name

    def __str__(self):
        return 'Login not exist: {}'.format(self.account_name)


class AccountConfirmationRequired(ThirdPartyApiException):
    def __init__(self, account: InstagramAccounts):
        self.account = account

    def __str__(self):
        return 'For account {} auth confirmation is required'.format(self.account.credentials)


class AccountInvalidCredentials(ThirdPartyApiException):
    def __init__(self, account: InstagramAccounts):
        self.account = account

    def __str__(self):
        return 'Invalid credentials for account: {}'.format(self.account.credentials)


class AccountTooManyRequests(ThirdPartyApiException):
    def __init__(self, account: InstagramAccounts):
        self.account = account

    def __str__(self):
        return 'Too many requests from account: {0} ... Sleep for {1} secs ...'.format(self.account.credentials,
                                                                                       settings.ACCOUNT_TOO_MANY_REQUESTS_SLEEP)


class InvalidProxyFormatError(BaseParserException):
    def __init__(self, proxy: str):
        self.proxy = proxy

    def __str__(self):
        return 'Invalid format of proxy: {}'.format(self.proxy)


class NoAccountsDBError(BaseParserException):
    def __str__(self):
        return 'No accounts to work with in db ...'


class NoProxyDBError(BaseParserException):
    def __init__(self, type: str):
        self.type = type

    def __str__(self):
        return f'No proxies of type {self.type} to work with in db ...'


class NotEnoughProxyDBError(BaseParserException):
    def __init__(self, proxy_count: int, account_count: int):
        self.proxy_count = proxy_count
        self.account_count = account_count

    def __str__(self):
        return f'Not enough proxies in db ....\n' \
               f'You have to add {self.account_count // 10 - self.proxy_count} more proxies'