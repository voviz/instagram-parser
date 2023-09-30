import asyncio
import random

from aiostream import pipe, stream

from src.core.config import settings
from src.core.logs import custom_logger
from src.db.connector import async_session
from src.db.crud.instagram_accounts import add_new_accounts, update_accounts_daily_usage_rate
from src.db.crud.instagram_logins import get_login_all, update_login_list
from src.db.crud.parser_result import add_result_list
from src.db.models import InstagramLogins
from src.parser.clients.instagram import InstagramClient
from src.parser.clients.utils import errors_handler_decorator
from src.parser.exceptions import NoAccountsDBError, NoProxyDBError
from src.parser.utils import chunks


class Parser:
    def __init__(self):
        self.client = InstagramClient()
        self.loop = asyncio.get_event_loop()

    async def _retry_on_failure(self, func, *args, **kwargs):
        while True:
            try:
                return await func(*args, **kwargs)
            except (NoAccountsDBError, NoProxyDBError) as ex:
                custom_logger.warning(ex)
                if not await add_new_accounts():
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
            logins_for_update = await get_login_all(s)
            custom_logger.info(f'{len(logins_for_update)} logins for update found!')
            return logins_for_update

    @errors_handler_decorator
    async def get_login_id(self, login: InstagramLogins) -> InstagramLogins | None:
        return await self._retry_on_failure(self._internal_get_login_id, login)

    async def _internal_get_login_id(self, login: InstagramLogins) -> InstagramLogins | None:
        api_answer = await self.client.get_account_info_by_user_name(login.username)
        login.user_id = api_answer.user_id
        login.followers = api_answer.followers_number
        login.is_exists = True
        await asyncio.sleep(random.randint(0, settings.ID_UPDATE_PROCESS_DELAY_MAX_SEC))
        return login

    async def get_login_ids_in_loop(self, logins_list: list[InstagramLogins]) -> None:
        async with async_session() as s:
            for chunk in chunks(logins_list, 100):
                updated_logins = []
                xs = stream.iterate(chunk) | pipe.map(self.get_login_id, ordered=True, task_limit=5)
                async with xs.stream() as streamer:
                    async for login in streamer:
                        if login:
                            updated_logins.append(login)
                await update_login_list(s, updated_logins)
                custom_logger.info(f'ids for {len(updated_logins)} accounts updated!')

    @errors_handler_decorator
    async def collect_instagram_story_data(self, logins_list: list[InstagramLogins]) -> None:
        return await self._retry_on_failure(self._internal_collect_instagram_story_data, logins_list)

    async def _internal_collect_instagram_story_data(self, logins_list: list[InstagramLogins]) -> None:
        async with async_session as s:
            if not logins_list:
                return
            data = await self.client.get_account_stories_by_id([_.user_id for _ in logins_list])
            await add_result_list(s, data)
            await update_login_list(s, logins_list)
            custom_logger.info(f'{len(data)} logins are successfully updated!')

    def sync_wrapper_ids_update(self, logins_list: list[InstagramLogins]) -> None:
        self.loop.run_until_complete(self.get_login_ids_in_loop(logins_list))

    def sync_wrapper_reels_update(self, logins_list: list[InstagramLogins]) -> None:
        self.loop.run_until_complete(self.collect_instagram_story_data(logins_list))
