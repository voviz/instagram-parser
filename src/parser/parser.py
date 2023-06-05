import argparse
import asyncio
import concurrent.futures
import random
import time
from aiostream import stream, pipe

from core.logs import custom_logger
from core.settings import settings, Settings
from db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from db.crud.instagram_logins import InstagramLoginsTableDBHandler
from db.crud.parser_result import ParserResultTableDBHandler
from db.models import InstagramLogins
from parser.clients.instagram import InstagramClient
from parser.clients.models import InstagramClientAnswer
from parser.clients.utils import errors_handler_decorator
from parser.exceptions import NoAccountsDBError, NoProxyDBError, NotEnoughProxyDBError
from parser.utils import add_new_accounts, chunks, check_driver_installation


class Parser:
    @errors_handler_decorator
    async def on_start(self):
        while True:
            try:
                custom_logger.info('Start parser ...')
                custom_logger.info('Prepare database ...')
                # check webdriver installation
                check_driver_installation()
                # get new accs and union with proxies
                await add_new_accounts()
                # update usage rates for all accs
                await InstagramAccountsTableDBHandler.update_accounts_daily_usage_rate()
                custom_logger.info('Parser is ready ...')
                # return logins for update
                logins_for_update = await InstagramLoginsTableDBHandler.get_login_all()
                custom_logger.info(f'{len(logins_for_update)} logins for update found!')
                return logins_for_update
            except (NoProxyDBError, NotEnoughProxyDBError) as ex:
                custom_logger.warning(ex)
                custom_logger.warning('Restart after 15 min ...')
                await asyncio.sleep(900)

    @errors_handler_decorator
    async def get_login_id(self, login: InstagramLogins) -> InstagramClientAnswer | None:
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
        xs = stream.iterate(logins_list) | pipe.map(self.collect_instagram_story_data, ordered=True, task_limit=5)
        async with xs.stream() as streamer:
            async for login in streamer:
                if login:
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

    def run(self):
        try:
            # load vars to settings
            settings = Settings()
            # parse cmd args
            parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
            parser.add_argument('-db_host', help='db host address')
            parser.add_argument('-db_port', help='db host port')
            parser.add_argument('-db_user', help='db host user')
            parser.add_argument('-db_password', help='db host password')
            parser.add_argument('-ar', '--account_daily_usage_rate', help='each account max daily usage rate')
            parser.add_argument('-pc', '--process_count', help='number of parallel process')
            parser.add_argument('-cr', '--chunks_in_requests_count',
                                help='number of chunks to split update reels process')
            parser.add_argument('-um', '--update_process_delay_max',
                                help='max delay (choose randomly [0:value) for update process delay')
            parser.add_argument('-rs', '--parser_between_restarts_sleep_sec',
                                help='number of users to update via one request to instagram')
            args = parser.parse_args()
            if args.db_host:
                settings.POSTGRES_HOST = args.db_host
            if args.db_port:
                settings.POSTGRES_PORT = args.db_port
            if args.db_user:
                settings.POSTGRES_USER = args.db_user
            if args.db_password:
                settings.POSTGRES_PASSWORD = args.db_password
            if args.account_daily_usage_rate:
                settings.ACCOUNT_DAILY_USAGE_RATE = args.account_daily_usage_rate
            if args.process_count:
                settings.PROCESS_COUNT = args.process_count
            if args.update_process_delay_max:
                settings.UPDATE_PROCESS_DELAY_MAX = args.update_process_delay_max

            while True:
                # on_start run
                if logins_for_update := asyncio.run(self.on_start()):
                    with concurrent.futures.ProcessPoolExecutor(max_workers=settings.PROCESS_COUNT) as executor:
                        # extract logins with id and split it to chunk of 30 elems size
                        logins_with_id = list(chunks([login for login in logins_for_update if login.user_id], 30))
                        futures = [executor.submit(self.sync_wrapper_reels_update, chunk) for chunk in
                                   logins_with_id]
                        # add separate process to update new logins without ids
                        logins_without_id = [login for login in logins_for_update if not login.user_id]
                        futures.append(executor.submit(self.sync_wrapper_ids_update, logins_without_id))
                        # wait for all process to finish
                        for future in concurrent.futures.as_completed(futures):
                            future.result()
                    custom_logger.info(f'All {len(logins_for_update)} logins updated!')
                    custom_logger.info(f'Automatic restart of the parser after '
                                       f'{settings.PARSER_BETWEEN_RESTARTS_SLEEP_SEC} secs ...')
                    time.sleep(settings.PARSER_BETWEEN_RESTARTS_SLEEP_SEC)
                else:
                    custom_logger.warning('No logins for update found!')
                    custom_logger.warning('Check your db and credentials in .env file!')
                    custom_logger.warning('Restart after 15 min ...')
                    time.sleep(900)
        except BaseException as ex:
            custom_logger.error(ex)
