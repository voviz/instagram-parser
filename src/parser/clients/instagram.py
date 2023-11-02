import asyncio
import urllib.parse
from datetime import datetime
import re
from time import sleep

import aiohttp
from aiohttp import TooManyRedirects
import pytz
from selenium.common import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from seleniumbase import SB
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logs import custom_logger, logger
from src.db.crud.instagram_accounts import get_account
from src.db.exceptions import NoProxyDBError
from src.parser.clients.base import BaseThirdPartyAPIClient
from src.parser.clients.exceptions import (
    AccountConfirmationRequired,
    AccountInvalidCredentials,
    AccountTooManyRequests,
    ClosedAccountError,
    LoginNotExistError,
)
from src.parser.clients.models import (
    AdType,
    InstagramClientAnswer,
    InstagramPost,
    InstagramStory,
    Marketplaces,
    ThirdPartyAPIMediaType,
    ThirdPartyAPISource,
)
from src.parser.clients.ozon import OzonClient
from src.parser.clients.utils import find_links
from src.parser.clients.wildberries import WildberriesClient
from src.parser.proxy.exceptions import ProxyTooManyRequests


class InstagramClient(BaseThirdPartyAPIClient):
    """
    Custom instagram API
    """

    api_name = 'InstagramAPI'
    base_url = 'https://www.instagram.com/api/v1'

    ACCOUNT_BAN_TIME_SEC = 5
    account_banned_list = {}

    def __init__(self):
        self.ozon = OzonClient()
        self.wildberries = WildberriesClient()

    async def get_info_by_user_name(self, async_session: AsyncSession, username: str) -> InstagramClientAnswer:
        try:
            account = await self._fetch_account(async_session)
            raw_data = await self.request(
                method=BaseThirdPartyAPIClient.HTTPMethods.GET,
                edge='users/web_profile_info',
                querystring={'username': username},
                is_json=True,
                cookie=account.cookies,
                user_agent=account.user_agent,
                proxy=account.proxy,
            )
            if not raw_data['data']['user']:
                raise LoginNotExistError(username=username)
            return InstagramClientAnswer(
                source=ThirdPartyAPISource.instagram,
                username=username,
                user_id=raw_data['data']['user']['id'],
                followers_number=raw_data['data']['user']['edge_followed_by']['count'],
            )

        except Exception as ex:
            await self._handle_exceptions(ex, account=account, username=username)

    async def _process_post(self, async_session: AsyncSession, post: dict, from_datetime: datetime = None):
        created_at = datetime.fromtimestamp(post['taken_at'], tz=pytz.utc)
        if from_datetime and created_at > from_datetime:
            return []

        caption = post['caption']['text'] if post['caption'] else ''
        comments_count = post['comment_count']
        likes_count = post['like_count']
        url = 'https://www.instagram.com/p/' + post['code']

        parsed_post_base = InstagramPost(
            post_id=post['pk'],
            created_at=created_at,
            caption=caption,
            likes_count=likes_count,
            comments_count=comments_count,
            url=url,
        )
        links = find_links(caption)
        parsed_post_copies = [parsed_post_base.model_copy() for _ in links]

        await asyncio.gather(*(self._extract_sku_from_link(p, l) for p, l in zip(parsed_post_copies, links)))
        posts_with_caption = await self._extract_sku_from_caption(
            async_session=async_session, item=parsed_post_base, caption=caption
        )

        return [p for p in (parsed_post_copies + posts_with_caption) if p.sku]

    async def get_posts_by_id(
        self, async_session: AsyncSession, user_id: int, from_datetime: datetime = None
    ) -> InstagramClientAnswer:
        try:
            result_list = []
            next_max_id = None
            while len(result_list) < 500:
                account = await self._fetch_account(async_session)
                raw_data = await self.request(
                    method=BaseThirdPartyAPIClient.HTTPMethods.GET,
                    edge=f'feed/user/{user_id}',
                    querystring={'count': 100} if not next_max_id else {'count': 100, 'max_id': next_max_id},
                    is_json=True,
                    cookie=account.cookies,
                    user_agent=account.user_agent,
                    proxy=account.proxy,
                )

                if not raw_data.get('user'):
                    raise LoginNotExistError(user_id=user_id)

                result = await asyncio.gather(
                    *(self._process_post(async_session, p, from_datetime) for p in raw_data['items'])
                )

                result_list.extend([i for sublist in result for i in sublist])

                if not raw_data['more_available']:
                    break

                next_max_id = raw_data['next_max_id']

            return InstagramClientAnswer(
                source=ThirdPartyAPISource.instagram,
                username=raw_data['user']['username'],
                user_id=user_id,
                posts_list=result_list,
            )

        except Exception as ex:
            await self._handle_exceptions(ex, account=account, user_id=user_id)

    async def get_stories_by_id(
        self, async_session: AsyncSession, user_id_list: list[int]
    ) -> list[InstagramClientAnswer]:
        try:
            account = await self._fetch_account(async_session)
            querystring = ''.join([f'reel_ids={_}&' for _ in user_id_list])
            raw_data = await self.request(
                method=BaseThirdPartyAPIClient.HTTPMethods.GET,
                edge=f'feed/reels_media?{querystring}',
                is_json=True,
                cookie=account.cookies,
                user_agent=account.user_agent,
                proxy=account.proxy,
            )
            stories_by_accounts = []
            if raw_data['reels']:
                for user_id in raw_data['reels']:
                    stories_list = []
                    username = raw_data['reels'][user_id]['user']['username']
                    for item in raw_data['reels'][user_id]['items']:
                        if not (story := self._extract_story_from_item(item)):
                            continue

                        # text in story
                        if item.get('accessibility_caption'):
                            story_list = await self._extract_sku_from_caption(
                                async_session=async_session, item=story, caption=item['accessibility_caption'].lower()
                            )
                            stories_list.extend(story_list)

                        # link sticker in story
                        elif item.get('story_link_stickers'):
                            await self._extract_sku_from_link(
                                story, item['story_link_stickers'][0]['story_link']['url']
                            )

                        if story.sku:
                            stories_list.append(story)

                    stories_by_accounts.append(
                        InstagramClientAnswer(
                            source=ThirdPartyAPISource.instagram,
                            username=username,
                            stories_list=stories_list,
                            user_id=user_id
                        )
                    )
            return stories_by_accounts
        except Exception as ex:
            await self._handle_exceptions(ex, account=account)

    def _extract_story_from_item(self, item):
        if item['media_type'] == ThirdPartyAPIMediaType.photo.value:
            return InstagramStory(
                media_type=ThirdPartyAPIMediaType.photo.value,
                url=item['image_versions2']['candidates'][0]['url'],
                created_at=item['taken_at'],
            )
        elif item['media_type'] == ThirdPartyAPIMediaType.video.value:
            return InstagramStory(
                media_type=ThirdPartyAPIMediaType.video.value,
                url=item['video_versions'][0]['url'],
                created_at=item['taken_at'],
            )
        return None

    async def _extract_sku_from_caption(
        self, async_session: AsyncSession, item: InstagramStory | InstagramPost, caption: str
    ) -> list[InstagramStory | InstagramPost]:
        caption = caption.lower()

        keywords = ('артикул', 'sku', 'articul')

        skus = re.findall(r'\d{5,10}', caption) if any(keyword in caption for keyword in keywords) else []

        results = []

        for sku in skus:
            item_copy = item.model_copy()
            item_copy.sku = sku

            if any(oz in caption for oz in ('ozon', 'озон')):
                item_copy.marketplace = Marketplaces.ozon
            elif await self.wildberries.check_sku(async_session, item_copy):
                item_copy.marketplace = Marketplaces.wildberries
            item_copy.ad_type = AdType.text
            if item_copy.marketplace and item_copy.sku:
                results.append(item_copy)

        return results

    async def _extract_sku_from_link(self, story, url):
        try:
            decoded_url = urllib.parse.unquote(url)
            if 'https://l.instagram.com/?u=' in decoded_url:
                decoded_url = decoded_url.split('https://l.instagram.com/?u=')[1]
            story.url = decoded_url
            if 'ozon.ru' in story.url:
                story.marketplace = Marketplaces.ozon
                story.sku = self.ozon.extract_sku_from_url(story.url)
            elif 'wildberries.ru' in story.url:
                story.marketplace = Marketplaces.wildberries
                story.sku = self.wildberries.extract_sku_from_url(story.url)
            else:
                story.url = await self._resolve_stories_link(url)
                if 'ozon.ru' in story.url:
                    story.marketplace = Marketplaces.ozon
                    story.sku = self.ozon.extract_sku_from_url(story.url)
                elif 'wildberries.ru' in story.url:
                    story.marketplace = Marketplaces.wildberries
                    story.sku = self.wildberries.extract_sku_from_url(story.url)
                    if story.sku:
                        logger.info(f"{decoded_url}")
            story.ad_type = AdType.link
        except NoProxyDBError as ex:
            raise ex
        except WebDriverException:
            pass
        except Exception as ex:
            if str(ex) != 'Retry of page load timed out after 120.0 seconds!':
                custom_logger.error(f'{type(ex)}: {ex}')
                custom_logger.error('url: ' + url)

    async def _resolve_stories_link(self, url: str) -> str:
        def sync_resolve_stories_link(url: str) -> str:
            # init client
            with SB(uc=True, headless2=True, browser=settings.WEBDRIVER) as sb:
                try:
                    sb.open(url)
                    # case: instagram redirect page
                    if sb.is_text_visible('Вы покидаете Instagram'):
                        redirect_button = sb.wait_for_element_present('button', by=By.TAG_NAME, timeout=5)
                        if redirect_button.text == 'Перейти по ссылке':
                            redirect_button.click()
                    # define url
                    while True:
                        if 'ozon.ru' in sb.get_current_url():
                            sb.wait_for_element_present('__ozon', by=By.ID, timeout=5)
                            break
                        elif 'wildberries.ru' in sb.get_current_url():
                            sb.wait_for_element_present('wrapper', by=By.CLASS_NAME, timeout=5)
                            break
                        else:
                            # case: redirect landing page

                            # check all redirect links/buttons
                            for _ in ['Перейти', 'перейти', 'Открыть', 'открыть']:
                                if redirect_button := sb.driver.find_elements(by=By.PARTIAL_LINK_TEXT, value=_):
                                    redirect_button[0].click()
                                    continue

                            # wait for 5 secs
                            sleep(5)
                            if 'ozon.ru' in sb.get_current_url() or 'wildberries.ru' in sb.get_current_url():
                                continue
                            break

                    return sb.get_current_url()
                except NoSuchElementException as ex:
                    # case: when timout occured after redirect
                    if any(
                        [
                            self.wildberries.extract_sku_from_url(sb.get_current_url()),
                            self.ozon.extract_sku_from_url(sb.get_current_url()),
                        ]
                    ):
                        return sb.get_current_url()
                    ex.url = sb.get_current_url()
                    raise ex

        return await asyncio.get_running_loop().run_in_executor(None, sync_resolve_stories_link, url)

    async def _handle_exceptions(self, ex, **kwargs):

        if isinstance(
            ex,
            (
                aiohttp.ClientProxyConnectionError,
                aiohttp.ClientHttpProxyError,
                aiohttp.ServerDisconnectedError,
                aiohttp.ClientOSError,
                asyncio.TimeoutError,
            ),
        ):
            ex.proxy = kwargs['account'].proxy
            raise ex

        if isinstance(ex, TooManyRedirects):
            raise AccountInvalidCredentials(account=kwargs['account'])

        if hasattr(ex, 'status'):
            messages = {
                400: {
                    'useragent mismatch': AccountInvalidCredentials,
                    'challenge_required': AccountConfirmationRequired,
                    'checkpoint_required': AccountConfirmationRequired,
                    'Not authorized to view user': ClosedAccountError,
                },
                401: AccountTooManyRequests,
                404: LoginNotExistError,
                500: ProxyTooManyRequests,
            }

            error = messages[ex.status]
            if ex.status == 400:
                error = error[ex.answer['message']]

            if issubclass(error, ClosedAccountError):
                raise error(user_id=kwargs['user_id'])

            if issubclass(error, LoginNotExistError):
                raise error(username=kwargs['username'])

            if issubclass(error, (ProxyTooManyRequests, AccountTooManyRequests)):
                raise error(proxy=kwargs['account'].proxy)

            raise error(account=kwargs['account'])

        raise ex

    @classmethod
    async def _fetch_account(cls, async_session: AsyncSession):
        async with async_session() as s:
            while True:
                account = await get_account(s)
                if (
                    account.proxy in cls.account_banned_list
                    and (datetime.now(pytz.utc) - cls.account_banned_list[account.proxy]).seconds
                    > cls.ACCOUNT_BAN_TIME_SEC
                    or account.proxy not in cls.account_banned_list
                ):
                    return account

    @classmethod
    def ban_account(cls, proxy: str):
        cls.account_banned_list.update({proxy: datetime.now(pytz.utc)})
