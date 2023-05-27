from typing import Any

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


class InvalidProxyFormatError(BaseParserException):
    def __init__(self, proxy: str):
        self.proxy = proxy

    def __str__(self):
        return 'Invalid format of proxy: {}'.format(self.proxy)


class NoAccountsDBError(BaseParserException):
    pass
