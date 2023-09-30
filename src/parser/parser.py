import asyncio
import random

from aiostream import stream, pipe

from src.core.logs import custom_logger
from src.core.config import settings
from src.db.connector import DatabaseConnector
from src.db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from src.db.crud.instagram_logins import InstagramLoginsTableDBHandler
from src.db.crud.parser_result import ParserResultTableDBHandler
from src.db.models import InstagramLogins
from src.parser.clients.instagram import InstagramClient
from src.parser.clients.utils import errors_handler_decorator
from src.parser.exceptions import NoAccountsDBError, NoProxyDBError
from src.parser.utils import add_new_accounts, chunks


class Parser:
    @errors_handler_decorator
    async def on_start(self) -> list[InstagramLogins]:
        while True:
            try:
                # init db
                await DatabaseConnector().async_init()
                custom_logger.info('Start parser ...')
                custom_logger.info('Prepare database ...')
                # get new accs and union with proxies
                await add_new_accounts()
                # update usage rates for all accs
                await InstagramAccountsTableDBHandler.update_accounts_daily_usage_rate()
                custom_logger.info('Parser is ready ...')
                # return logins for update
                logins_for_update = await InstagramLoginsTableDBHandler.get_login_all()
                custom_logger.info(f'{len(logins_for_update)} logins for update found!')
                return logins_for_update
            except NoProxyDBError as ex:
                custom_logger.warning(ex)
                custom_logger.warning('Restart after 15 min ...')
                await asyncio.sleep(900)
            finally:
                # close db connection
                await DatabaseConnector().close()

    @errors_handler_decorator
    async def get_login_id(self, login: InstagramLogins) -> InstagramLogins | None:
        while True:
            try:
                client = InstagramClient()
                # get login base info (user_id, is_exists, followers)
                api_answer = await client.get_account_info_by_user_name(login.username)
                # update login id and followers number
                login.user_id = api_answer.user_id
                login.followers = api_answer.followers_number
                login.is_exists = True
                # sleep for n-sec
                await asyncio.sleep(random.randint(0, settings.ID_UPDATE_PROCESS_DELAY_MAX_SEC))
                return login
            except NoAccountsDBError as ex:
                custom_logger.warning(ex)
                if not await add_new_accounts():
                    custom_logger.warning('Restart after 15 min ...')
                    await asyncio.sleep(900)

    async def get_login_ids_in_loop(self, logins_list: list[InstagramLogins]) -> None:
        # init db
        await DatabaseConnector().async_init()
        for chunk in chunks(logins_list, 100):
            updated_logins = []
            xs = stream.iterate(chunk) | pipe.map(self.get_login_id, ordered=True, task_limit=5)
            async with xs.stream() as streamer:
                async for login in streamer:
                    if login:
                        updated_logins.append(login)
            await InstagramLoginsTableDBHandler.update_login_list(updated_logins)
            custom_logger.info(f'ids for {len(updated_logins)} accounts updated!')
        # close db connection
        await DatabaseConnector().close()

    @errors_handler_decorator
    async def collect_instagram_story_data(self, logins_list: list[InstagramLogins]) -> None:
        while True:
            try:
                # init db
                await DatabaseConnector().async_init()
                if not logins_list:
                    return
                client = InstagramClient()
                # get stories info
                data = await client.get_account_stories_by_id_v2([_.user_id for _ in logins_list])
                # update data in result table db
                await ParserResultTableDBHandler.add_result_list(data)
                # mark logins as updated
                await InstagramLoginsTableDBHandler.update_login_list(logins_list)
                custom_logger.info(f'{len(data)} logins are successfully updated!')
                break
            except NoAccountsDBError as ex:
                custom_logger.warning(ex)
                if not await add_new_accounts():
                    custom_logger.warning('Restart after 15 min ...')
                    await asyncio.sleep(900)
            finally:
                # close db connection
                await DatabaseConnector().close()

    def sync_wrapper_ids_update(self, logins_list: list[InstagramLogins]) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.get_login_ids_in_loop(logins_list))

    def sync_wrapper_reels_update(self, logins_list: list[InstagramLogins]) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.collect_instagram_story_data(logins_list))
