import asyncio
from datetime import datetime
import re

import aiohttp
from aiohttp import TooManyRedirects
from selenium.common import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from seleniumbase import SB

from src.core.logs import custom_logger
from src.parser.clients.base import BaseThirdPartyAPIClient
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
from src.parser.exceptions import (
    AccountConfirmationRequired,
    AccountInvalidCredentials,
    AccountTooManyRequests,
    BaseParserException,
    ClosedAccountError,
    LoginNotExistError,
    NoProxyDBError,
    ProxyTooManyRequests,
)
from src.parser.proxy_handler import convert_to_seleniumbase_format


class InstagramClient(BaseThirdPartyAPIClient):
    """
    Custom instagram API
    """

    api_name = 'InstagramAPI'
    base_url = 'https://www.instagram.com/api/v1'

    async def get_info_by_user_name(self, username: str) -> InstagramClientAnswer:
        try:
            account = await self._fetch_account()
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

        except BaseParserException as ex:  # : PIE786
            await self._handle_exceptions(ex, account=account, username=username)

    async def get_posts_by_id(self, user_id: int, from_datetime: datetime = None) -> InstagramClientAnswer:
        try:
            account = await self._fetch_account()
            raw_data = await self.request(
                method=BaseThirdPartyAPIClient.HTTPMethods.GET,
                edge=f'feed/user/{user_id}',
                querystring={'count': 100000},
                is_json=True,
                cookie=account.cookies,
                user_agent=account.user_agent,
                proxy=account.proxy,
            )

            if not raw_data.get('user'):
                raise LoginNotExistError(user_id=user_id)

            async def process_post(post):
                created_at = datetime.fromtimestamp(post['taken_at'])
                if from_datetime and created_at > from_datetime:
                    return []

                caption = post['caption']['text'] if post['caption'] else ''
                parsed_post = InstagramPost(post_id=post['pk'], created_at=created_at, caption=caption)
                links = find_links(caption)

                parsed_post_copies = [parsed_post.copy() for _ in links]
                await asyncio.gather(*(self._extract_sku_from_link(p, l) for p, l in zip(parsed_post_copies, links)))

                posts_with_caption = await self._extract_sku_from_caption(parsed_post, caption)

                return [p for p in ([parsed_post] + parsed_post_copies + posts_with_caption) if p.sku]

            result = await asyncio.gather(*(process_post(p) for p in raw_data['items']))

            result_list = [i for sublist in result for i in sublist]

            return InstagramClientAnswer(
                source=ThirdPartyAPISource.instagram,
                username=raw_data['user']['username'],
                user_id=user_id,
                posts_list=result_list,
            )

        except BaseParserException as ex:  # : PIE786
            await self._handle_exceptions(ex, account=account, user_id=user_id)

    async def get_stories_by_id(self, user_id_list: list[int]) -> list[InstagramClientAnswer]:  # noqa: CCR001
        try:
            account = await self._fetch_account()
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
                for reels_id in raw_data['reels']:
                    stories_list = []
                    username = raw_data['reels'][reels_id]['user']['username']
                    for item in raw_data['reels'][reels_id]['items']:
                        if not (story := self._extract_story_from_item(item)):
                            continue

                        if item.get('accessibility_caption'):
                            story_list = await self._extract_sku_from_caption(
                                story, item['accessibility_caption'].lower()
                            )
                            stories_list.extend(story_list)

                        elif item.get('story_link_stickers'):
                            await self._extract_sku_from_link(
                                story, item['story_link_stickers'][0]['story_link']['url']
                            )

                        if story.sku:
                            stories_list.append(story)

                    stories_by_accounts.append(
                        InstagramClientAnswer(
                            source=ThirdPartyAPISource.instagram, username=username, stories_list=stories_list
                        )
                    )
            return stories_by_accounts
        except BaseParserException as ex:  # : PIE786
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
        self, item: InstagramStory | InstagramPost, caption: str
    ) -> list[InstagramStory | InstagramPost]:  # : CCR001
        caption = caption.lower()

        keywords = ('артикул', 'sku', 'articul')

        skus = re.findall(r'\d{5,10}', caption) if any(keyword in caption for keyword in keywords) else []

        results = []

        for sku in skus:
            item_copy = item.copy()
            item_copy.sku = sku

            if any(wb in caption for wb in ('wb', 'вб', 'wildberries', 'вайл')):
                item_copy.marketplace = Marketplaces.wildberries
            elif any(oz in caption for oz in ('ozon', 'озон')):
                item_copy.marketplace = Marketplaces.ozon
            else:
                # If the marketplace isn't mentioned in the caption, check the SKU with WildberriesClient
                result = await WildberriesClient().check_sku(sku)
                item_copy.marketplace = Marketplaces.wildberries if result else Marketplaces.ozon

            item_copy.ad_type = AdType.text
            results.append(item_copy)

        return results

    async def _extract_sku_from_link(self, story, link):
        try:
            if not ('ozon' in link or 'wildberries' in link):
                return
            story.url = await self._resolve_stories_link(link)
            if 'ozon' in story.url:
                story.marketplace = Marketplaces.ozon
                story.sku = OzonClient.extract_sku_from_url(story.url)
            elif 'wildberries' in story.url:
                story.marketplace = Marketplaces.wildberries
                story.sku = WildberriesClient.extract_sku_from_url(story.url)
            story.ad_type = AdType.link
        except NoProxyDBError as ex:
            raise ex
        except WebDriverException:
            pass
        except Exception as ex:  # noqa: PIE786
            if str(ex) != 'Retry of page load timed out after 120.0 seconds!':
                custom_logger.error(f'{type(ex)}: {ex}')
                custom_logger.error('url: ' + link)

    async def _resolve_stories_link(self, url: str) -> str:  # noqa: CCR001
        account = await self._fetch_account()

        def sync_resolve_stories_link(url: str, proxy: str) -> str:
            # init client
            with SB(uc=True, headless2=True, proxy=convert_to_seleniumbase_format(proxy)) as sb:
                try:
                    sb.open(url)
                    # case: instagram redirect page
                    if sb.is_text_visible('Вы покидаете Instagram'):
                        redirect_button = sb.wait_for_element_present('button', by=By.TAG_NAME, timeout=5)
                        if redirect_button.text == 'Перейти по ссылке':
                            redirect_button.click()
                    # define url
                    if 'ozon.ru' in sb.get_current_url():
                        sb.wait_for_element_present('__ozon', by=By.ID, timeout=5)
                    elif 'wildberries.ru' in sb.get_current_url():
                        sb.wait_for_element_present('wrapper', by=By.CLASS_NAME, timeout=5)
                    else:
                        # case: redirect landing page
                        # check all links on the page
                        for link in sb.get_unique_links():
                            if any(
                                [WildberriesClient.extract_sku_from_url(link), OzonClient.extract_sku_from_url(link)]
                            ):
                                return link
                    return sb.get_current_url()
                except NoSuchElementException as ex:
                    # case: when timout occured after redirect
                    if any(
                        [
                            WildberriesClient.extract_sku_from_url(sb.get_current_url()),
                            OzonClient.extract_sku_from_url(sb.get_current_url()),
                        ]
                    ):
                        return sb.get_current_url()
                    ex.url = sb.get_current_url()
                    raise ex

        return await asyncio.get_running_loop().run_in_executor(None, sync_resolve_stories_link, url, account.proxy)

    async def _handle_exceptions(self, ex, **kwargs):

        if isinstance(ex, (aiohttp.ClientProxyConnectionError, aiohttp.ClientHttpProxyError)):
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
                raise error(account_name=kwargs['username'])

            if issubclass(error, ProxyTooManyRequests):
                raise error(proxy=kwargs['account'].proxy)

            raise error(account=kwargs['account'])

        raise ex
