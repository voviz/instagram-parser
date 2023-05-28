import asyncio

import chromedriver_autoinstaller
import undetected_chromedriver as webdriver
from aiohttp import TooManyRedirects
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from db.crud.proxies import ProxiesTableDBHandler, ProxyTypes
from parser.clients.base import BaseThirdPartyAPIClient
from parser.clients.models import InstagramClientAnswer, ThirdPartyAPISource, InstagramStory, ThirdPartyAPIMediaType, \
    Marketplaces, AdType
from parser.clients.ozon import OzonClient
from parser.clients.wildberries import WildberrisClient
from parser.exceptions import AccountConfirmationRequired, \
    AccountInvalidCredentials, LoginNotExist, AccountTooManyRequests, NoProxyDBError
from parser.proxy_handler import SeleniumProxyHandler


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
                # make reverse iteration in order to find the last story with link
                for i in reversed(raw_data['reels'][str(user_id)]['items']):
                    if i['media_type'] == ThirdPartyAPIMediaType.photo:
                        story = InstagramStory(media_type=ThirdPartyAPIMediaType.photo,
                                               url=i['image_versions2']['candidates'][0]['url'],
                                               created_at=i['taken_at'])
                    if i['media_type'] == ThirdPartyAPIMediaType.video:
                        story = InstagramStory(media_type=ThirdPartyAPIMediaType.video,
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
                        break

            return InstagramClientAnswer(source=ThirdPartyAPISource.instagram,
                                         username=username,
                                         stories_list=stories_list)
        except TooManyRedirects:
            raise AccountInvalidCredentials(account=account)
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
            raise ex

    async def _resolve_stories_link(self, url: str) -> str:
        version_main = int(chromedriver_autoinstaller.get_chrome_version().split(".")[0])
        ozon_proxy = await ProxiesTableDBHandler.get_ozon_proxy()
        if not ozon_proxy:
            raise NoProxyDBError(ProxyTypes.ozon)
        selenium_proxy = SeleniumProxyHandler(*SeleniumProxyHandler.convert_to_selenium_format(ozon_proxy.proxy))
        options = webdriver.ChromeOptions()
        options.add_argument(f'--load-extension={selenium_proxy.directory}')
        driver = webdriver.Chrome(version_main=version_main, headless=True, options=options)
        try:
            driver.get(url)
            if 'ozon' in driver.current_url:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, '__ozon'))
                )
            else:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, 'product-page'))
                    )
                except TimeoutException:
                    # case: when landing site occured before ozon redirect
                    button = driver.find_element(By.TAG_NAME, 'button')
                    button.click()
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, 'product-page'))
                    )
            link = driver.current_url
            return link
        except TimeoutException as ex:
            ex.url = driver.current_url
            raise ex
        finally:
            driver.quit()
