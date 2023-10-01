from enum import Enum
import json
from typing import Any

import aiohttp

from src.parser.exceptions import ThirdPartyApiException
from src.parser.proxy_handler import convert_to_aiohttp_format


class BaseThirdPartyAPIClient:
    """
    Base class provides async request to some third-party API defined in subclass.
    Also it performs basic response codes/errors handling.
    """

    api_name = ''
    headers: dict[str, str] = {'accept': '*/*', 'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'}
    base_url = ''

    class HTTPMethods(Enum):
        GET = 'GET'
        POST = 'POST'
        PUT = 'PUT'
        PATCH = 'PATCH'
        DELETE = 'DELETE'

    async def request(
        self,
        method: HTTPMethods,
        edge: str,
        is_json: bool = True,
        querystring: dict = None,
        payload: Any = None,
        proxy: str = None,
        user_agent: str = None,
        cookie: str = None,
    ) -> str:
        current_headers = self.headers.copy()

        if user_agent:
            current_headers.update({'user-agent': user_agent})
        if cookie:
            current_headers.update({'cookie': cookie})

        async with aiohttp.ClientSession(headers=current_headers) as session, session.request(
            method=method.value,
            url='/'.join((self.base_url, edge)),
            proxy=convert_to_aiohttp_format(proxy),
            params=querystring,
            json=payload,
        ) as res:
            return await self._clean_response(res, is_json=is_json)

    async def _clean_response(self, res, is_json: bool) -> str:
        try:
            if res.status != 200:
                content = await (res.json() if res.content_type == 'application/json' else res.text())
                raise ThirdPartyApiException(api_name=self.api_name, answer=content, status=res.status)

            return await (res.json() if is_json else res.text())
        except (json.decoder.JSONDecodeError, aiohttp.client_exceptions.ContentTypeError) as exc:
            raise ThirdPartyApiException(api_name=self.api_name, answer=str(exc), status=res.status)
