import asyncio

import aiohttp
from selenium.common import WebDriverException, TimeoutException

from core.logs import custom_logger
from core.settings import settings
from db.connector import DatabaseConnector
from db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from db.crud.instagram_logins import InstagramLoginsTableDBHandler
from parser.exceptions import AccountConfirmationRequired, AccountInvalidCredentials, LoginNotExist, \
    AccountTooManyRequests, NoAccountsDBError, NoProxyDBError


def errors_handler_decorator(func):
    async def wrapper(*args, **kwargs):
        try:
            # init db
            await DatabaseConnector().async_init()
            res = await func(*args, **kwargs)
            return res
        except (asyncio.TimeoutError,
                aiohttp.ClientOSError,
                aiohttp.ClientResponseError,
                aiohttp.ServerDisconnectedError,
                aiohttp.client_exceptions.ClientProxyConnectionError,
                ConnectionResetError,
                ConnectionError,
                ConnectionAbortedError) as ex:
            custom_logger.error(f'Connection error ({type(ex)}): {ex}')
        except (aiohttp.ClientProxyConnectionError, aiohttp.ClientHttpProxyError) as ex:
            custom_logger.error(f'Cannot connect via proxy: {ex.proxy}')
        except (AccountInvalidCredentials, AccountConfirmationRequired) as ex:
            # delete acc from db
            await InstagramAccountsTableDBHandler.delete_account(ex.account)
            custom_logger.warning(ex)
        except LoginNotExist as ex:
            # mark login as not existed
            await InstagramLoginsTableDBHandler.mark_as_not_exists(ex.account_name)
            custom_logger.warning(ex)
        except AccountTooManyRequests as ex:
            custom_logger.warning(ex)
            await asyncio.sleep(settings.ACCOUNT_TOO_MANY_REQUESTS_SLEEP)
        except (NoAccountsDBError, NoProxyDBError) as ex:
            custom_logger.warning(ex)
            await asyncio.sleep(1800)
        except TimeoutException as ex:
            custom_logger.error(f'Error with story link resolving process ({type(ex)}) url: {ex.url}')
        except WebDriverException as ex:
            custom_logger.error(f'Error with webdriver in story link resolving process ({type(ex)}): {ex}')
            custom_logger.error(f'Maybe something occur with "ozon" proxy....')
        except Exception as ex:
            custom_logger.error(f'Something wrong with parser ({type(ex)}): {ex}')
        finally:
            # close db connection
            await DatabaseConnector().close()

    return wrapper