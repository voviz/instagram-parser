import json
from enum import StrEnum
from typing import Any

import aiohttp as aiohttp

from parser.proxy_handler import ProxyHandler
from parser.exceptions import ThirdPartyApiException


class BaseThirdPartyAPIClient:
    """
    Base class provides async request to some third-party API defined in subclass.
    Also it performs basic response codes/errors handling.
    """
    api_name = ''
    headers = {"accept": "*/*",
               "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"}
    base_url = ''

    class HTTPMethods(StrEnum):
        GET = 'GET'
        POST = 'POST'
        PUT = 'PUT'
        PATCH = 'PATCH'
        DELETE = 'DELETE'

    async def request(self, method: HTTPMethods, edge: str,
                      is_json: bool = True, querystring: dict = None,
                      payload: Any = None, proxy: str = None,
                      user_agent: str = None, cookie: str = None) -> str:
        if user_agent:
            self.headers.update({'user-agent': user_agent})
        if cookie:
            self.headers.update({'cookie': cookie})
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.request(
                    method=method.value,
                    url='/'.join((self.base_url, edge)),
                    proxy=ProxyHandler.convert_to_aiohttp_format(proxy),
                    params=querystring,
                    json=payload,
            ) as res:
                return await self._clean_response(res, is_json=is_json)

    async def _clean_response(self, res, is_json: bool) -> str:
        try:
            if res.status != 200:
                if res.content_type == 'application/json':
                    answer = await res.json()
                else:
                    answer = await res.text()
                raise ThirdPartyApiException(api_name=self.api_name, answer=answer, status=res.status)
            response = await res.json() if is_json else await res.text()
            return response
        except (json.decoder.JSONDecodeError, aiohttp.client_exceptions.ContentTypeError) as exc:
            raise ThirdPartyApiException(api_name=self.api_name, answer=exc, status=res.status)
