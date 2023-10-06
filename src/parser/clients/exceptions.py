from typing import Any

from src.db.models import InstagramAccounts
from src.exceptions import BaseParserException


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
