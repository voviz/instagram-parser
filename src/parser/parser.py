import argparse
import asyncio
import concurrent.futures
import random

import pydantic

from core.logs import custom_logger
from core.settings import settings, Settings
from db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from db.crud.instagram_logins import InstagramLoginsTableDBHandler
from db.crud.parser_result import ParserResultTableDBHandler
from db.crud.proxies import ProxiesTableDBHandler, ProxyTypes
from db.models import InstagramLogins
from parser.clients.instagram import InstagramClient
from parser.clients.utils import errors_handler_decorator
from parser.exceptions import NoProxyDBError


class Parser:
    @errors_handler_decorator
    async def on_start(self):
        custom_logger.info('Start parser ...')
        custom_logger.info('Prepare database ...')
        # get new accs and union with proxies
        if new_accounts := await InstagramAccountsTableDBHandler.get_accounts_without_proxy():
            proxies = await ProxiesTableDBHandler.get_parser_proxies_all()
            if not proxies:
                raise NoProxyDBError(ProxyTypes.parser)
            for i, acc in enumerate(new_accounts):
                acc.proxy = proxies[i % len(proxies)].proxy
            await InstagramAccountsTableDBHandler.set_proxy_for_accounts(new_accounts)
        # update usage rates for all accs
        await InstagramAccountsTableDBHandler.update_accounts_daily_usage_rate()
        custom_logger.info('Parser is ready ...')
        # return logins for update
        logins_for_update = await InstagramLoginsTableDBHandler.get_login_all()
        custom_logger.info(f'{len(logins_for_update)} logins for update found!')

        return logins_for_update

    @errors_handler_decorator
    async def collect_instagram_story_data(self, login: InstagramLogins) -> None:
        client = InstagramClient()
        # get login base info (user_id, is_exists, followers)
        if not login.user_id:
            login = await client.get_account_info_by_user_name(login.username)
            # update data in db
            await InstagramLoginsTableDBHandler.update_login(login)
        # get stories info
        data = await client.get_account_stories_by_id(login.username, login.user_id)
        # update data in result table db
        await ParserResultTableDBHandler.update_result(data)
        custom_logger.info(f'{data.username} login successfully updated!')
        # sleep for n-sec
        await asyncio.sleep(random.randint(0, settings.UPDATE_PROCESS_DELAY_MAX))

    def sync_wrapper(self, login: InstagramLogins) -> None:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.collect_instagram_story_data(login))

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
            parser.add_argument('-um', '--update_process_delay_max',
                                help='max delay (choose randomly [0:value) for update process delay')
            parser.add_argument('-as', '--account_too_many_requests_sleep',
                                help='delay after too many requests error occur')
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
            if args.account_too_many_requests_sleep:
                settings.ACCOUNT_TOO_MANY_REQUESTS_SLEEP = args.account_too_many_requests_sleep

            # on_start run
            if logins_for_update := asyncio.run(self.on_start()):
                futures = []
                with concurrent.futures.ProcessPoolExecutor(max_workers=settings.PROCESS_COUNT) as executor:
                    for login in logins_for_update:
                        new_future = executor.submit(
                            self.sync_wrapper,
                            login
                        )
                        futures.append(new_future)
                concurrent.futures.wait(futures)
            else:
                custom_logger.warning('No logins for update found!')
                custom_logger.warning('Check your db and credentials in .env file!')
        except BaseException as ex:
            custom_logger.error(ex)
