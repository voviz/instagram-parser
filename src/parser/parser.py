import asyncio
import random

from core.logs import custom_logger
from core.settings import settings
from db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from db.crud.instagram_logins import InstagramLoginsTableDBHandler
from db.crud.parser_result import ParserResultTableDBHandler
from db.models import InstagramLogins
from parser.clients.instagram import InstagramClient
from parser.clients.utils import errors_handler_decorator
from parser.exceptions import NoAccountsDBError, NoProxyDBError
from parser.utils import add_new_accounts


class Parser:
    @errors_handler_decorator
    async def on_start(self) -> list[InstagramLogins]:
        while True:
            try:
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

    @errors_handler_decorator
    async def get_login_id(self, login: InstagramLogins) -> InstagramLogins | None:
        while True:
            try:
                client = InstagramClient()
                # get login base info (user_id, is_exists, followers)
                login = await client.get_account_info_by_user_name(login.username)
                # update data in db
                await InstagramLoginsTableDBHandler.update_login(login)
                # sleep for n-sec
                await asyncio.sleep(random.randint(0, settings.ID_UPDATE_PROCESS_DELAY_MAX_SEC))
                return login
            except NoAccountsDBError as ex:
                custom_logger.warning(ex)
                if not await add_new_accounts():
                    custom_logger.warning('Restart after 15 min ...')
                    await asyncio.sleep(900)

    async def get_login_ids_in_loop(self, logins_list: list[InstagramLogins]) -> None:
        for login in logins_list:
            await self.get_login_id(login)
            custom_logger.info(f'id of {login.username} login is successfully updated!')

    @errors_handler_decorator
    async def collect_instagram_story_data(self, logins_list: list[InstagramLogins]) -> None:
        while True:
            try:
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

    def sync_wrapper_ids_update(self, logins_list: list[InstagramLogins]) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.get_login_ids_in_loop(logins_list))

    def sync_wrapper_reels_update(self, logins_list: list[InstagramLogins]) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.collect_instagram_story_data(logins_list))
