from typing import Any


class BaseParserException(Exception):
    """Base class for all parser errors"""

    def __str__(self):
        return "Something goes wrong with parser"


class EmptyResultsException(BaseParserException):
    pass


class ThirdPartyApiException(BaseParserException):
    def __init__(self, api_name: str, status: str, answer: Any):
        self.api_name = api_name
        self.status = status
        self.answer = answer

    def __str__(self):
        return f'{self.api_name} non-200 response. Status [{self.status}]: {self.answer}'


class NotFoundException(BaseParserException):
    pass


class AccountNotExist(ThirdPartyApiException):
    def __init__(self, account_name: str):
        self.account_name = account_name

    def __str__(self):
        return 'Account not exist: {}'.format(self.account_name)


class AccountConfirmationRequired(ThirdPartyApiException):
    def __init__(self, account_name: str):
        self.account_name = account_name

    def __str__(self):
        return 'For account {} auth confirmation is required'.format(self.account_name)


class InvalidCredentials(ThirdPartyApiException):
    def __init__(self, account_name: str):
        self.account_name = account_name

    def __str__(self):
        return 'Invalid credentials for account: {}'.format(self.account_name)


class AccountIsPrivate(ThirdPartyApiException):
    pass


class ThirdPartyTimeoutError(ThirdPartyApiException):
    pass


class InvalidProxyFormatError(BaseParserException):
    def __init__(self, proxy: str):
        self.proxy = proxy

    def __str__(self):
        return 'Invalid format of proxy: {}'.format(self.proxy)


class NoAccountsDBError(BaseParserException):
    pass
