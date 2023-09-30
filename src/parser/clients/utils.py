import asyncio
import traceback

import aiohttp
from selenium.common import WebDriverException, TimeoutException

from src.core.logs import custom_logger
from src.db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from src.db.crud.instagram_logins import InstagramLoginsTableDBHandler
from src.parser.exceptions import AccountConfirmationRequired, AccountInvalidCredentials, LoginNotExist, \
    AccountTooManyRequests, NoProxyDBError, ThirdPartyApiException, ProxyTooManyRequests


def errors_handler_decorator(func):
    async def wrapper(*args, **kwargs):
        try:
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
        except (AccountInvalidCredentials, AccountConfirmationRequired, AccountTooManyRequests) as ex:
            custom_logger.warning(ex)
            # delete acc from db
            await InstagramAccountsTableDBHandler.delete_account(ex.account)
        except LoginNotExist as ex:
            # mark login as not existed
            await InstagramLoginsTableDBHandler.mark_as_not_exists(ex.account_name)
            custom_logger.warning(ex)
        except ProxyTooManyRequests as ex:
            custom_logger.warning(ex)
        except ThirdPartyApiException as ex:
            custom_logger.error(ex)
        except NoProxyDBError as ex:
            custom_logger.warning(ex)
            custom_logger.warning('Restart after 15 min ...')
            await asyncio.sleep(900)
        except TimeoutException as ex:
            custom_logger.error(f'Error with story link resolving process ({type(ex)}) url: {ex.url}')
        except WebDriverException as ex:
            custom_logger.error(f'Error with webdriver in story link resolving process ({type(ex)}): {ex}')
            custom_logger.error(f'Maybe something occur with "ozon" proxy....')
        except Exception as ex:
            traceback.print_exc()
            custom_logger.error(f'Something wrong with parser ({type(ex)}): {ex}')

    return wrapper