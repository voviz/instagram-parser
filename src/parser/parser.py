import asyncio
import concurrent.futures
import random

import tortoise

from core.logs import custom_logger
from core.settings import settings
from db.connector import DatabaseConnector
from db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from db.crud.instagram_logins import InstagramLoginsTableDBHandler
from db.crud.proxies import ProxiesTableDBHandler
from db.models import InstagramLogins
from parser.clients.instagram import InstagramClient
from parser.clients.utils import errors_handler_decorator


class Parser:
    @errors_handler_decorator
    async def on_start(self):
        custom_logger.info('Start parser ...')
        custom_logger.info('Prepare database ...')
        # get new accs and union with proxies
        new_accounts = await InstagramAccountsTableDBHandler.get_accounts_without_proxy()
        proxies = await ProxiesTableDBHandler.get_proxies_all()
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
        if not login.user_id:
            login = await client.get_account_info_by_user_name(login.username)
        data = await client.get_account_stories_by_id(login.username, login.user_id)
        # update data in db
        await InstagramLoginsTableDBHandler.update_login(data)
        custom_logger.info(f'{data.username} login successfully updated!')
        # sleep for n-sec
        await asyncio.sleep(random.randint(0, settings.UPDATE_PROCESS_DELAY_MAX))

    def sync_wrapper(self, login: InstagramLogins) -> None:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.collect_instagram_story_data(login))

    def run(self):
        # on_start run
        logins_for_update = asyncio.run(self.on_start())
        futures = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
            for login in logins_for_update:
                new_future = executor.submit(
                    self.sync_wrapper,
                    login
                )
                futures.append(new_future)
        concurrent.futures.wait(futures)
