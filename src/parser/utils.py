import asyncio
import functools
import random

import aiohttp
from selenium.common import TimeoutException, WebDriverException
from seleniumbase import get_driver

from src.core.config import settings
from src.core.logs import custom_logger
from src.db.connector import async_session
from src.db.crud.instagram_accounts import delete_account
from src.db.crud.instagram_logins import mark_as_not_exists
from src.db.exceptions import NoProxyDBError
from src.parser.clients.exceptions import AccountInvalidCredentials, LoginNotExistError, ThirdPartyApiException, \
    AccountConfirmationRequired, AccountTooManyRequests
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


def errors_handler_decorator(func):  # noqa: CCR001

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (
                asyncio.TimeoutError,
                aiohttp.ClientOSError,
                aiohttp.ClientResponseError,
                aiohttp.ServerDisconnectedError,
                aiohttp.client_exceptions.ClientProxyConnectionError,
                ConnectionError,
                aiohttp.ClientProxyConnectionError,
                aiohttp.ClientHttpProxyError,
                ProxyTooManyRequests,
        ) as ex:
            custom_logger.error(f'Connection error ({type(ex)}): {ex}')
            await asyncio.sleep(random.randint(2, 5))
        except (AccountInvalidCredentials, AccountConfirmationRequired, AccountTooManyRequests) as ex:
            await account_errors(ex)
        except LoginNotExistError as ex:
            await login_errors(ex)
        except ThirdPartyApiException as ex:
            custom_logger.error(ex)
        except NoProxyDBError as ex:
            await no_proxy_db_error(ex)
        except TimeoutException as ex:
            custom_logger.error(f'Error with story link resolving process ({type(ex)}) url: {ex.url}')
        except WebDriverException as ex:
            custom_logger.error(f'Error with webdriver in story link resolving process ({type(ex)}): {ex}')
        except Exception as ex:  # noqa: PIE786
            custom_logger.error(f'Something wrong with parser ({type(ex)}): {ex}')

    return wrapper


async def account_errors(ex):
    custom_logger.warning(ex)
    async with async_session() as s:
        await delete_account(s, ex.account)


async def login_errors(ex):
    async with async_session() as s:
        await mark_as_not_exists(s, username=ex.username, user_id=ex.user_id)
    custom_logger.error(ex)


async def no_proxy_db_error(ex):
    custom_logger.warning(ex)
    custom_logger.warning('Restart after 15 min ...')
    await asyncio.sleep(900)
