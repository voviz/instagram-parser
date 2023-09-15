import asyncio
import random

import aiohttp
from aiohttp import TooManyRedirects
from selenium.common import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from seleniumbase import SB

from core.logs import custom_logger
from db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from db.crud.proxies import ProxyTypes, ProxiesTableDBHandler
from parser.clients.base import BaseThirdPartyAPIClient
from parser.clients.models import InstagramClientAnswer, ThirdPartyAPISource, InstagramStory, ThirdPartyAPIMediaType, \
    Marketplaces, AdType
from parser.clients.ozon import OzonClient
from parser.clients.wildberries import WildberrisClient
from parser.exceptions import AccountConfirmationRequired, \
    AccountInvalidCredentials, LoginNotExist, AccountTooManyRequests, NoProxyDBError, ProxyTooManyRequests
from parser.proxy_handler import ProxyHandler


class InstagramClient(BaseThirdPartyAPIClient):
    """
    Custom instagram API
    """
    api_name = 'InstagramAPI'
    base_url = 'https://www.instagram.com/api/v1'

    async def get_account_info_by_user_name(self, username: str) -> InstagramClientAnswer:
        try:
            # get account credentials from db
            account = await InstagramAccountsTableDBHandler.get_account()
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
                raise LoginNotExist(account_name=username)
            return InstagramClientAnswer(source=ThirdPartyAPISource.instagram,
                                         username=username,
                                         user_id=raw_data['data']['user']['id'],
                                         followers_number=raw_data['data']['user']['edge_followed_by']['count'], )
        except TooManyRedirects:
            raise AccountInvalidCredentials(account=account)
        except (aiohttp.ClientProxyConnectionError, aiohttp.ClientHttpProxyError) as ex:
            ex.proxy = account.proxy
            raise ex
        except Exception as ex:
            """
            For some reason (maybe due to inheritance) cannot handle user-types of exceptions here
            So Exception class is used
            """
            if ex.__dict__.get('status'):
                if ex.status == 400:
                    if ex.answer['message'] == 'useragent mismatch':
                        raise AccountInvalidCredentials(account=account)
                    if ex.answer['message'] in ('challenge_required', 'checkpoint_required'):
                        raise AccountConfirmationRequired(account=account)
                if ex.status == 401:
                    raise AccountTooManyRequests(account=account)
                if ex.status == 404:
                    raise LoginNotExist(account_name=username)
                if ex.status == 500:
                    raise ProxyTooManyRequests(proxy=account.proxy)
            raise ex

    async def get_account_stories_by_id(self, username: str, user_id: int) -> InstagramClientAnswer:
        try:
            # get account credentials from db
            account = await InstagramAccountsTableDBHandler.get_account()
            raw_data = await self.request(
                method=BaseThirdPartyAPIClient.HTTPMethods.GET,
                edge='feed/reels_media',
                querystring={'reel_ids': user_id},
                is_json=True,
                cookie=account.cookies,
                user_agent=account.user_agent,
                proxy=account.proxy,
            )
            stories_list = []
            # check if any reels exist
            if raw_data['reels']:
                for i in raw_data['reels'][str(user_id)]['items']:
                    if i['media_type'] == ThirdPartyAPIMediaType.photo.value:
                        story = InstagramStory(media_type=ThirdPartyAPIMediaType.photo.value,
                                               url=i['image_versions2']['candidates'][0]['url'],
                                               created_at=i['taken_at'])
                    if i['media_type'] == ThirdPartyAPIMediaType.video.value:
                        story = InstagramStory(media_type=ThirdPartyAPIMediaType.video.value,
                                               url=i['video_versions'][0]['url'],
                                               created_at=i['taken_at'])

                    # check story for sku in caption
                    if i.get('accessibility_caption'):
                        for kw in ('артикул', 'articul', 'sku'):
                            if kw in i['accessibility_caption'].lower():
                                raw_sku = i['accessibility_caption'].lower().split(kw)[1]
                                sku = ''.join([_ for _ in raw_sku if i.isdigit()])
                                story.sku = sku
                                for wb in ('wb', 'вб', 'wildberries', 'вайл'):
                                    if wb in i['accessibility_caption'].lower():
                                        story.marketplace = Marketplaces.wildberries
                                for oz in ('ozon', 'озон'):
                                    if oz in i['accessibility_caption'].lower():
                                        story.marketplace = Marketplaces.ozon
                                story.ad_type = AdType.text

                        # check marketplace if it is not defined yet
                        if story.sku and not story.marketplace:
                            result = await asyncio.gather(
                                OzonClient().check_sku(sku),
                                WildberrisClient().check_sku(sku),
                            )
                            if result[0]:
                                story.marketplace = Marketplaces.ozon
                            elif result[1]:
                                story.marketplace = Marketplaces.wildberries

                    # check story for link
                    if not story.sku and i.get('story_link_stickers'):
                        url = i['story_link_stickers'][0]['story_link']['url']
                        if 'ozon' in url or 'wildberries' in url:
                            story.url = await self._resolve_stories_link(url)
                            if 'ozon' in story.url:
                                story.marketplace = Marketplaces.ozon
                                story.sku = OzonClient.extract_sku_from_url(story.url)
                            elif 'wildberries' in story.url:
                                story.marketplace = Marketplaces.wildberries
                                story.sku = WildberrisClient.extract_sku_from_url(story.url)
                            story.ad_type = AdType.link

                    if story.sku:
                        stories_list.append(story)

            return InstagramClientAnswer(source=ThirdPartyAPISource.instagram,
                                         username=username,
                                         stories_list=stories_list)
        except TooManyRedirects:
            raise AccountInvalidCredentials(account=account)
        except (aiohttp.ClientProxyConnectionError, aiohttp.ClientHttpProxyError) as ex:
            ex.proxy = account.proxy
            raise ex
        except Exception as ex:
            """
            For some reason (maybe due to inheritance) cannot handle user-types of exceptions here
            So Exception class is used
            """
            if ex.__dict__.get('status'):
                if ex.status == 400:
                    if ex.answer['message'] == 'useragent mismatch':
                        raise AccountInvalidCredentials(account=account)
                    if ex.answer['message'] in ('challenge_required', 'checkpoint_required'):
                        raise AccountConfirmationRequired(account=account)
                if ex.status == 401:
                    raise AccountTooManyRequests(account=account)
                if ex.status == 404:
                    raise LoginNotExist(account_name=username)
                if ex.status == 500:
                    raise ProxyTooManyRequests(proxy=account.proxy)
            raise ex

    async def get_account_stories_by_id_v2(self, user_id_list: list[int]) -> list[InstagramClientAnswer]:
        try:
            # get account credentials from db
            account = await InstagramAccountsTableDBHandler.get_account()
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
                for id in raw_data['reels']:
                    stories_list = []
                    username = raw_data['reels'][id]['user']['username']
                    for item in raw_data['reels'][id]['items']:
                        if item['media_type'] == ThirdPartyAPIMediaType.photo.value:
                            story = InstagramStory(media_type=ThirdPartyAPIMediaType.photo.value,
                                                   url=item['image_versions2']['candidates'][0]['url'],
                                                   created_at=item['taken_at'])
                        if item['media_type'] == ThirdPartyAPIMediaType.video.value:
                            story = InstagramStory(media_type=ThirdPartyAPIMediaType.video.value,
                                                   url=item['video_versions'][0]['url'],
                                                   created_at=item['taken_at'])
                        # check story for sku in caption
                        if item.get('accessibility_caption'):
                            for kw in ('артикул', 'articul', 'sku'):
                                if kw in item['accessibility_caption'].lower():
                                    raw_sku = item['accessibility_caption'].lower().split(kw)[1]
                                    sku = ''.join([_ for _ in raw_sku if item.isdigit()])
                                    story.sku = sku
                                    for wb in ('wb', 'вб', 'wildberries', 'вайл'):
                                        if wb in item['accessibility_caption'].lower():
                                            story.marketplace = Marketplaces.wildberries
                                    for oz in ('ozon', 'озон'):
                                        if oz in item['accessibility_caption'].lower():
                                            story.marketplace = Marketplaces.ozon
                                    story.ad_type = AdType.text

                            # check marketplace if it is not defined yet
                            if story.sku and not story.marketplace:
                                result = await asyncio.gather(
                                    OzonClient().check_sku(sku),
                                    WildberrisClient().check_sku(sku),
                                )
                                if result[0]:
                                    story.marketplace = Marketplaces.ozon
                                elif result[1]:
                                    story.marketplace = Marketplaces.wildberries

                        # check story for link
                        if not story.sku and item.get('story_link_stickers'):
                            url = item['story_link_stickers'][0]['story_link']['url']
                            if 'ozon' in url or 'wildberries' in url:
                                try:
                                    story.url = await self._resolve_stories_link(url)
                                except NoProxyDBError as ex:
                                    raise ex
                                except WebDriverException:
                                    continue
                                except Exception as ex:
                                    if not str(ex) == 'Retry of page load timed out after 120.0 seconds!':
                                        custom_logger.error(f'{type(ex)}: {ex}')
                                        custom_logger.error('url: ' + url)
                                    continue
                                if 'ozon' in story.url:
                                    story.marketplace = Marketplaces.ozon
                                    story.sku = OzonClient.extract_sku_from_url(story.url)
                                elif 'wildberries' in story.url:
                                    story.marketplace = Marketplaces.wildberries
                                    story.sku = WildberrisClient.extract_sku_from_url(story.url)
                                story.ad_type = AdType.link

                        if story.sku:
                            stories_list.append(story)

                    stories_by_accounts.append(InstagramClientAnswer(source=ThirdPartyAPISource.instagram,
                                                                     username=username,
                                                                     stories_list=stories_list))
            return stories_by_accounts
        except TooManyRedirects:
            raise AccountInvalidCredentials(account=account)
        except (aiohttp.ClientProxyConnectionError, aiohttp.ClientHttpProxyError) as ex:
            ex.proxy = account.proxy
            raise ex
        except Exception as ex:
            """
            For some reason (maybe due to inheritance) cannot handle user-types of exceptions here
            So Exception class is used
            """
            if ex.__dict__.get('status'):
                if ex.status == 400:
                    if ex.answer['message'] == 'useragent mismatch':
                        raise AccountInvalidCredentials(account=account)
                    if ex.answer['message'] in ('challenge_required', 'checkpoint_required'):
                        raise AccountConfirmationRequired(account=account)
                if ex.status == 401:
                    raise AccountTooManyRequests(account=account)
                if ex.status == 404:
                    raise LoginNotExist(account_name=username)
                if ex.status == 500:
                    raise ProxyTooManyRequests(proxy=account.proxy)
            raise ex

    async def _resolve_stories_link(self, url: str) -> str:
        # get proxy
        ozon_proxy_list = await ProxiesTableDBHandler.get_proxy_all(ProxyTypes.ozon)
        if not ozon_proxy_list:
            raise NoProxyDBError(ProxyTypes.ozon)
        proxy = ozon_proxy_list[random.randint(0, len(ozon_proxy_list) - 1)].proxy
        # init client
        with SB(uc=True, headless2=True, proxy=ProxyHandler.convert_to_seleniumbase_format(proxy)) as sb:
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
                    for l in sb.get_unique_links():
                        if any([WildberrisClient.extract_sku_from_url(l),
                                OzonClient.extract_sku_from_url(l)]):
                            return l
                return sb.get_current_url()
            except NoSuchElementException as ex:
                # case: when timout occured after redirect
                if any([WildberrisClient.extract_sku_from_url(sb.get_current_url()),
                        OzonClient.extract_sku_from_url(sb.get_current_url())]):
                    return sb.get_current_url()
                ex.url = sb.get_current_url()
                raise ex
