class BaseParserException(Exception):
    """Base class for all parser errors"""

    def __str__(self):
        return "Something goes wrong with parser"


class EmptyResultsException(BaseParserException):
    pass


class ThirdPartyApiException(BaseParserException):
    pass


class NotFoundException(BaseParserException):
    pass


class AccountNotExist(ThirdPartyApiException):
    def __init__(self, account_name: str):
        self.account_name = account_name

    def __str__(self):
        return 'Account not exist: {}'.format(self.account_name)


class AccountIsPrivate(ThirdPartyApiException):
    pass


class ThirdPartyTimeoutError(ThirdPartyApiException):
    pass
