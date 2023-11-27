import asyncio
import traceback
from asyncio import Semaphore
from datetime import datetime
import random

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from src.parser.proxy.exceptions import ProxyTooManyRequests
from src.core.logs import custom_logger, logger
from src.db.connector import get_async_sessionmaker, get_db_pool
from src.db.crud.instagram_accounts import add_new_accounts, update_accounts_daily_usage_rate
from src.db.crud.instagram_logins import get_logins_for_update, update_login_list, update_new_login_ids
from src.db.crud.parser_result import add_result_list
from src.db.crud.parser_result_posts import add_posts_result_list
from src.db.crud.inst_sku_per_post import add_inst_sku_per_post_list
from src.db.exceptions import NoAccountsDBError, NoProxyDBError
from src.db.models import InstagramLogins
from src.parser.clients.instagram import InstagramClient
from src.parser.clients.models import InstagramClientAnswer
from src.parser.utils import chunks, errors_handler


class Parser:
    RESTART_WAIT_TIME = 900
    LOGINS_CHUNK_SIZE = 30
    MAX_SLEEP_FOR_COROUTINE = 1
    MAX_COROUTINE_NUM = 3

    def __init__(self):
        self.client = InstagramClient()

    async def _retry_on_failure(self, func, async_session: AsyncSession, *args, **kwargs):
        while True:
            try:
                return await func(async_session, *args, **kwargs)
            except (NoAccountsDBError, NoProxyDBError) as ex:
                custom_logger.warning(ex)
                if not await add_new_accounts(async_session):
                    custom_logger.warning('Restart after 15 min ...')
                    await asyncio.sleep(900)
            except (
                    asyncio.TimeoutError,
                    aiohttp.client_exceptions.ClientProxyConnectionError,
                    aiohttp.ClientProxyConnectionError,
                    ProxyTooManyRequests,
            ) as ex:
                custom_logger.exception("Connection error")
                custom_logger.error(f'Connection error ({type(ex)}): {ex}')
                InstagramClient.ban_account(ex.proxy)
                await asyncio.sleep(2)

    async def on_start(self, async_session: AsyncSession) -> list[InstagramLogins]:
        return await self._retry_on_failure(self._internal_on_start, async_session)

    async def _internal_on_start(self, async_session: AsyncSession):
        await add_new_accounts(async_session)
        async with async_session() as s:
            await update_accounts_daily_usage_rate(s)
        logins_for_update = await get_logins_for_update(async_session)
        return logins_for_update

    async def _internal_get_login_id(
        self, async_session: AsyncSession, login: InstagramLogins
    ) -> InstagramLogins | None:
        api_answer = await self.client.get_info_by_user_name(async_session, login.username)
        login.user_id = api_answer.user_id
        login.followers = api_answer.followers_number
        login.is_exists = True
        return login

    @errors_handler
    async def _get_login_id(self, async_session: AsyncSession, login: InstagramLogins) -> InstagramLogins | None:
        return await self._retry_on_failure(self._internal_get_login_id, async_session, login)

    async def get_login_ids_list(self, async_session: AsyncSession) -> None:
        while True:
            if logins_without_id := [login for login in await self.on_start(async_session) if not login.user_id]:
                semaphore = Semaphore(self.MAX_COROUTINE_NUM)
                for chunk in chunks(logins_without_id , 100):
                    updated_logins = []

                    async def process_login(async_session, login):
                        async with semaphore:
                            if updated_login := await self._get_login_id(async_session, login):
                                updated_logins.append(updated_login)
                            await asyncio.sleep(random.randint(0, self.MAX_SLEEP_FOR_COROUTINE))

                    tasks = [process_login(async_session, login) for login in chunk]
                    await asyncio.gather(*tasks)

                    await update_new_login_ids(async_session, updated_logins)
                    custom_logger.info(f'ids for {len(updated_logins)} accounts updated!')
            else:
                custom_logger.warning('No ids for update found!')
                await self.handle_no_logins()

    @errors_handler
    async def _get_stories_in_chunk(self, semaphore: Semaphore, async_session: AsyncSession, logins_list: list[InstagramLogins]) -> None:
        async with semaphore:
            logger.info("Async with semaphore")
            if not logins_list:
                return
            logger.info("Get stories by id")
            data = await self._retry_on_failure(self.client.get_stories_by_id, async_session,
                                                [_.user_id for _ in logins_list])
            logger.info("adding result")
            await add_result_list(async_session, data)
            logger.info("updating login list")
            await update_login_list(async_session, logins_list)
            custom_logger.info(f'{len(data)} stories with sku found!')
            logger.info("Login list updated. Sleeping.")
        await asyncio.sleep(random.randint(0, self.MAX_SLEEP_FOR_COROUTINE))

    async def _internal_get_stories_data(self, async_session: AsyncSession, logins_list: list[InstagramLogins]) -> None:
        logger.info("Create semaphoe and gather")
        semaphore = Semaphore(self.MAX_COROUTINE_NUM)
        await asyncio.gather(*(self._get_stories_in_chunk(semaphore, async_session, chunk)
                               for chunk in chunks(logins_list, self.LOGINS_CHUNK_SIZE)))

    async def get_stories_data(self, async_session: AsyncSession) -> None:
        while True:
            logger.info("Getting logins to check")
            if logins_with_id := [login for login in await self.on_start(async_session) if login.user_id]:
                await self._internal_get_stories_data(async_session, logins_with_id)
            else:
                logger.info("No logins to check")
                custom_logger.warning('No stories for update found!')
                await self.handle_no_logins()

    @errors_handler
    async def _get_posts_by_id(self, async_session: AsyncSession, login: InstagramLogins) -> InstagramClientAnswer:
        # update login 'posts_updated_at' field
        result = await self._retry_on_failure(
            self.client.get_posts_by_id, async_session, login.user_id, login.posts_updated_at
        )
        login.posts_updated_at = datetime.now()
        return result

    async def get_posts_list_by_id(self, async_session: AsyncSession) -> None:
        while True:
            if logins_with_id := [login for login in await self.on_start(async_session) if login.user_id]:
                semaphore = Semaphore(self.MAX_COROUTINE_NUM)

                for chunk in chunks(logins_with_id, 10):
                    async def process_login(login):
                        async with semaphore:
                            if data := await self._get_posts_by_id(async_session, login):
                                # update parser_results_posts
                                result = await add_posts_result_list(async_session, data)
                                # update inst_sku_per_post
                                await add_inst_sku_per_post_list(async_session, data, result)
                                # update instagram_login
                                await update_login_list(async_session, [login])
                                # count posts
                                posts_count = len(set(p.post_id for p in data.posts_list))
                                custom_logger.info(f'{posts_count} posts with sku found!')
                            await asyncio.sleep(random.randint(0, self.MAX_SLEEP_FOR_COROUTINE))

                    tasks = [process_login(login) for login in chunk]
                    await asyncio.gather(*tasks)
            else:
                custom_logger.warning('No posts for update found!')
                await self.handle_no_logins()

    async def handle_no_logins(self):
        custom_logger.warning(f'Restart process after {self.RESTART_WAIT_TIME // 60} min ...')
        await asyncio.sleep(self.RESTART_WAIT_TIME)

    def run_async_function(self, async_function):
        db_pool = get_db_pool()
        async_session = get_async_sessionmaker(db_pool)
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(async_function(async_session))
        finally:
            loop.run_until_complete(db_pool.dispose())
