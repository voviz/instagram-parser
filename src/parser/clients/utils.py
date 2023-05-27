import asyncio

import aiohttp
from selenium.common import WebDriverException

from core.logs import custom_logger
from db.connector import DatabaseConnector
from db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from db.crud.instagram_logins import InstagramLoginsTableDBHandler
from parser.exceptions import AccountConfirmationRequired, AccountInvalidCredentials, LoginNotExist


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
                aiohttp.TooManyRedirects,
                ConnectionResetError,
                ConnectionError,
                ConnectionAbortedError) as ex:
            custom_logger.error(f'Connection error ({type(ex)}): {ex}')
        except (AccountInvalidCredentials, AccountConfirmationRequired) as ex:
            # delete acc from db
            await InstagramAccountsTableDBHandler.delete_account(ex.account)
            custom_logger.error(ex)
        except LoginNotExist as ex:
            # mark login as not existed
            await InstagramLoginsTableDBHandler.mark_as_not_exists(ex.account_name)
            custom_logger.error(ex)
        except WebDriverException as ex:
            custom_logger.error(f'Error with story link resolving process ({type(ex)}): {ex}')
        except Exception as ex:
            custom_logger.error(f'Something wrong with parser ({type(ex)}): {ex}')
        finally:
            # close db connection
            await DatabaseConnector().close()

    return wrapper