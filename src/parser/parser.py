import asyncio
from datetime import datetime
import random

from src.core.logs import custom_logger
from src.db.connector import async_session
from src.db.crud.instagram_accounts import add_new_accounts, update_accounts_daily_usage_rate
from src.db.crud.instagram_logins import get_logins_for_update, update_login_list
from src.db.crud.parser_result import add_result_list
from src.db.crud.parser_result_posts import add_posts_result_list
from src.db.exceptions import NoAccountsDBError, NoProxyDBError
from src.db.models import InstagramLogins
from src.parser.clients.instagram import InstagramClient
from src.parser.clients.models import InstagramClientAnswer
from src.parser.utils import chunks, errors_handler_decorator


class Parser:
    LOGINS_CHUNK_SIZE = 30
    MAX_SLEEP_FOR_COROUTINE = 1
    MAX_COROUTINE_NUM = 5

    def __init__(self):
        self.client = InstagramClient()

    async def _retry_on_failure(self, func, *args, **kwargs):
        while True:
            try:
                return await func(*args, **kwargs)
            except (NoAccountsDBError, NoProxyDBError) as ex:
                custom_logger.warning(ex)
                async with async_session() as s:
                    if not await add_new_accounts(s):
                        custom_logger.warning('Restart after 15 min ...')
                        await asyncio.sleep(900)

    @errors_handler_decorator
    async def on_start(self) -> list[InstagramLogins]:
        return await self._retry_on_failure(self._internal_on_start)

    async def _internal_on_start(self):
        async with async_session() as s:
            custom_logger.info('Start parser ...')
            custom_logger.info('Prepare database ...')
            await add_new_accounts(s)
            await update_accounts_daily_usage_rate(s)
            custom_logger.info('Parser is ready ...')
            logins_for_update = await get_logins_for_update(s)
            custom_logger.info(f'{len(logins_for_update)} logins for update found!')
            return logins_for_update

    async def _internal_get_login_id(self, login: InstagramLogins) -> InstagramLogins | None:
        api_answer = await self.client.get_info_by_user_name(login.username)
        login.user_id = api_answer.user_id
        login.followers = api_answer.followers_number
        login.is_exists = True
        return login

    @errors_handler_decorator
    async def _get_login_id(self, login: InstagramLogins) -> InstagramLogins | None:
        return await self._retry_on_failure(self._internal_get_login_id, login)

    async def get_login_ids_list(self, logins_list: list[InstagramLogins]) -> None:
        semaphore = asyncio.Semaphore(self.MAX_COROUTINE_NUM)
        for chunk in chunks(logins_list, 100):
            updated_logins = []

            async def process_login(login):
                async with semaphore:
                    if updated_login := await self._get_login_id(login):
                        updated_logins.append(updated_login)
                    await asyncio.sleep(random.randint(0, self.MAX_SLEEP_FOR_COROUTINE))

            tasks = [process_login(login) for login in chunk]
            await asyncio.gather(*tasks)
            async with async_session() as s:
                await update_login_list(s, updated_logins)
            custom_logger.info(f'ids for {len(updated_logins)} accounts updated!')

    async def _internal_get_stories_data(self, logins_list: list[InstagramLogins]) -> None:
        @errors_handler_decorator
        async def process_login(logins_list: list[InstagramLogins]):
            async with self.semaphore:
                async with async_session() as s:
                    if not logins_list:
                        return
                    data = await self.client.get_stories_by_id([_.user_id for _ in logins_list])
                    await add_result_list(s, data)
                    await update_login_list(s, logins_list)
                    custom_logger.info(f'{len(data)} stories with sku found!')
            await asyncio.sleep(random.randint(0, self.MAX_SLEEP_FOR_COROUTINE))

        self.semaphore = asyncio.Semaphore(self.MAX_COROUTINE_NUM)
        await asyncio.gather(*(process_login(chunk) for chunk in chunks(logins_list, self.LOGINS_CHUNK_SIZE)))

    async def get_stories_data(self, logins_list: list[InstagramLogins]) -> None:
        return await self._retry_on_failure(self._internal_get_stories_data, logins_list)

    @errors_handler_decorator
    async def _get_posts_by_id(self, login: InstagramLogins) -> InstagramClientAnswer:
        # update login 'posts_updated_at' field
        result = await self._retry_on_failure(self.client.get_posts_by_id, login.user_id, login.posts_updated_at)
        login.posts_updated_at = datetime.now()
        return result

    async def get_posts_list_by_id(self, logins_list: list[InstagramLogins]) -> None:
        semaphore = asyncio.Semaphore(self.MAX_COROUTINE_NUM)
        async with async_session() as s:
            for chunk in chunks(logins_list, 10):
                posts_data = []

                async def process_login(login):
                    async with semaphore:
                        if data := await self._get_posts_by_id(login):
                            posts_data.append(data)
                        await asyncio.sleep(random.randint(0, self.MAX_SLEEP_FOR_COROUTINE))

                tasks = [process_login(login) for login in chunk]
                await asyncio.gather(*tasks)

                await add_posts_result_list(s, posts_data)
                await update_login_list(s, chunk)
                custom_logger.info(f'{len([p for p in posts_data if p.posts_list])} posts with sku found!')

    def sync_wrapper_posts_update(self, logins_list: list[InstagramLogins]) -> None:
        asyncio.new_event_loop().run_until_complete(self.get_posts_list_by_id(logins_list))

    def sync_wrapper_ids_update(self, logins_list: list[InstagramLogins]) -> None:
        asyncio.new_event_loop().run_until_complete(self.get_login_ids_list(logins_list))

    def sync_wrapper_stories_update(self, logins_list: list[InstagramLogins]) -> None:
        asyncio.new_event_loop().run_until_complete(self.get_stories_data(logins_list))
