import asyncio
import traceback

import aiohttp
import re
import urllib.parse
import requests
from selenium.common import TimeoutException, WebDriverException
from seleniumbase import get_driver
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logs import custom_logger
from src.db.crud.instagram_accounts import delete_account
from src.db.crud.instagram_logins import mark_as_not_exists
from src.db.exceptions import NoProxyDBError
from src.parser.clients.exceptions import (
    AccountConfirmationRequired,
    AccountInvalidCredentials,
    AccountTooManyRequests,
    LoginNotExistError,
    ThirdPartyApiException,
)
from src.parser.clients.instagram import InstagramClient
from src.parser.proxy.exceptions import ProxyTooManyRequests


def check_driver_installation() -> None:
    custom_logger.info('Check webdriver installation ... ')
    driver = get_driver(settings.WEBDRIVER, headless=True)
    driver.get('https://www.google.com/chrome')
    driver.quit()
    custom_logger.info('End of check driver installation process ...')


def chunks(lst: list, n: int):
    """
    Yield successive n-sized chunks from lst.
    @param lst: list of data
    @param n: number of chunks to separate
    @return: iterator
    """
    for i in range(0, len(lst), n):
        yield lst[i: i + n]


def errors_handler(func):  # noqa: CCR001
    async def wrapper(self, async_session: AsyncSession, *args, **kwargs):
        try:
            return await func(self, async_session, *args, **kwargs)
        except (
            asyncio.TimeoutError,
            aiohttp.ClientOSError,
            aiohttp.ClientResponseError,
            aiohttp.ServerDisconnectedError,
            aiohttp.client_exceptions.ClientProxyConnectionError,
            aiohttp.ClientProxyConnectionError,
            aiohttp.ClientHttpProxyError,
            ProxyTooManyRequests,
            ConnectionError,
        ) as ex:
            custom_logger.error(f'Connection error ({type(ex)}): {ex}')
            InstagramClient.ban_account(ex.proxy)
        except (AccountInvalidCredentials, AccountConfirmationRequired, AccountTooManyRequests) as ex:
            await account_errors(async_session, ex)
        except LoginNotExistError as ex:
            await login_errors(async_session, ex)
        except ThirdPartyApiException as ex:
            custom_logger.error(ex)
        except NoProxyDBError as ex:
            await no_proxy_db_error(ex)
        except TimeoutException as ex:
            custom_logger.error(f'Error with story link resolving process ({type(ex)}) url: {ex.url}')
        except WebDriverException as ex:
            custom_logger.error(f'Error with webdriver in story link resolving process ({type(ex)}): {ex}')
        except Exception as ex:
            traceback.print_exc()
            custom_logger.error(f'Something wrong with parser ({type(ex)}): {ex}')

    return wrapper


async def account_errors(async_session, ex):
    custom_logger.warning(ex)
    async with async_session() as s:
        await delete_account(s, ex.account)


async def login_errors(async_session, ex):
    async with async_session() as s:
        await mark_as_not_exists(s, username=ex.username, user_id=ex.user_id)
    custom_logger.error(ex)


async def no_proxy_db_error(ex):
    custom_logger.warning(ex)
    custom_logger.warning('Restart after 15 min ...')
    await asyncio.sleep(900)


wb_sku_pattern = re.compile(r'\d{5,}')
wb_size_pattern = re.compile(r'(?<=size=)\d+')
wb_link_pattern = re.compile(r'(?:(?:(?:wb)|(?:wildberries))\.ru(?:(?:/catalog/)|(?:/product\?card=)))\d+')


def resolve_redirection_link(link):
    # logger.debug(f'RESOLVING {link}')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/39.0.2171.95 Safari/537.36'
    }
    if not link.startswith('http'):
        link = f'http://{link}'
    try:
        response = requests.get(link, timeout=15, headers=headers)
    except Exception as e:  # (TimeOut, InvalidURL, ConnectionError, MissingSchema, InvalidSchema):

        return
    sku = get_sku_from_url(response.url)
    if sku is not None:
        return int(sku)
    if len(response.history) != 0:
        sku = get_sku_from_url(response.history[0].url)
    if sku is not None:
        return int(sku)
    return get_sku_from_text(response.text)


def get_sku_from_url(link):
    link = urllib.parse.quote(link)
    return get_sku_from_text(link)


def get_sku_from_text(text):
    link_res = wb_link_pattern.findall(text)
    if link_res:
        sku = wb_sku_pattern.findall(link_res[0])
        if sku:
            return int(sku[0])