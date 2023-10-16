from src.exceptions import BaseParserException
from src.parser.clients.exceptions import ThirdPartyApiException


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
