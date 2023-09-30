import asyncio
import traceback

import aiohttp
from selenium.common import TimeoutException, WebDriverException

from src.core.logs import custom_logger
from src.db.connector import async_session
from src.db.crud.instagram_accounts import delete_account
from src.db.crud.instagram_logins import mark_as_not_exists
from src.parser.exceptions import (
    AccountConfirmationRequired,
    AccountInvalidCredentials,
    AccountTooManyRequests,
    LoginNotExist,
    NoProxyDBError,
    ProxyTooManyRequests,
    ThirdPartyApiException,
)


def errors_handler_decorator(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (
            asyncio.TimeoutError,
            aiohttp.ClientOSError,
            aiohttp.ClientResponseError,
            aiohttp.ServerDisconnectedError,
            aiohttp.client_exceptions.ClientProxyConnectionError,
            ConnectionResetError,
            ConnectionError,
            ConnectionAbortedError,
        ) as ex:
            custom_logger.error(f'Connection error ({type(ex)}): {ex}')
        except (aiohttp.ClientProxyConnectionError, aiohttp.ClientHttpProxyError) as ex:
            custom_logger.error(f'Cannot connect via proxy: {ex.proxy}')
        except (AccountInvalidCredentials, AccountConfirmationRequired, AccountTooManyRequests) as ex:
            await account_errors(ex)
        except LoginNotExist as ex:
            await login_errors(ex)
        except ProxyTooManyRequests as ex:
            custom_logger.warning(ex)
        except ThirdPartyApiException as ex:
            custom_logger.error(ex)
        except NoProxyDBError as ex:
            await no_proxy_db_error(ex)
        except TimeoutException as ex:
            custom_logger.error(f'Error with story link resolving process ({type(ex)}) url: {ex.url}')
        except WebDriverException as ex:
            custom_logger.error(f'Error with webdriver in story link resolving process ({type(ex)}): {ex}')
            custom_logger.error(f'Maybe something occur with "ozon" proxy....')
        except Exception as ex:
            custom_logger.error(f'Something wrong with parser ({type(ex)}): {ex}')
            custom_logger.error(traceback.print_exc())

    return wrapper


async def account_errors(ex):
    custom_logger.warning(ex)
    async with async_session() as s:
        await delete_account(s, ex.account)


async def login_errors(ex):
    async with async_session() as s:
        await mark_as_not_exists(s, ex.account_name)
    custom_logger.warning(ex)


async def no_proxy_db_error(ex):
    custom_logger.warning(ex)
    custom_logger.warning('Restart after 15 min ...')
    await asyncio.sleep(900)
