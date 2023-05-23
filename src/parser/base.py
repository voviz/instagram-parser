import json
from typing import Any
from enum import StrEnum

import aiohttp as aiohttp

from src.parser.exceptions import EmptyResultsException, ThirdPartyTimeoutError, \
    ThirdPartyApiException, NotFoundException


class BaseThirdPartyAPIClient:
    """
    Base class provides async request to some third-party API defined in subclass.
    Also it performs basic response codes/errors handling.
    """
    api_name = ''
    headers = {}
    base_url = ''

    class HTTPMethods(StrEnum):
        GET = 'GET'
        POST = 'POST'
        PUT = 'PUT'
        PATCH = 'PATCH'
        DELETE = 'DELETE'

    async def request(self, method: HTTPMethods, edge: str, is_json: bool = True,
                      proxy: str = None, querystring: dict = None, payload: Any = None) -> str:
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.request(
                    method=method.value,
                    url='/'.join((self.base_url, edge)),
                    proxy=proxy,
                    params=querystring,
                    json=payload,
            ) as res:
                return await self._clean_response(res, is_json=is_json)

    async def _clean_response(self, res, is_json: bool) -> str:
        response_cleaned = ''
        try:
            if res.status == 404:
                raise NotFoundException(f'{self.api_name} found nothing')
            if res.status == 500:
                raise EmptyResultsException(f'{self.api_name} found nothing')
            if res.status == 504:
                raise ThirdPartyTimeoutError(f'{self.api_name} timeout')
            if res.status != 200:
                raise ThirdPartyApiException(
                    f'{self.api_name} non-200 response. Res [{res.status}] ({res}): {response_cleaned}')

            response_cleaned = await res.json() if is_json else res.text()
        except (json.decoder.JSONDecodeError, aiohttp.client_exceptions.ContentTypeError):
            raise ThirdPartyApiException(
                f'{self.api_name} non-JSON response: Res [{res.status}] ({res}): {response_cleaned}')

        return response_cleaned