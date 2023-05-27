import asyncio

import chromedriver_autoinstaller
import undetected_chromedriver as webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from db.crud.instagram_accounts import InstagramAccountsTableDBHandler
from parser.clients.base import BaseThirdPartyAPIClient
from parser.clients.models import InstagramClientAnswer, ThirdPartyAPISource, InstagramStory, ThirdPartyAPIMediaType, \
    Marketplaces, AdType
from parser.clients.ozon import OzonClient
from parser.clients.wildberris import WildberrisClient
from parser.exceptions import ThirdPartyApiException, AccountConfirmationRequired, InvalidCredentials
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
            return InstagramClientAnswer(source=ThirdPartyAPISource.instagram,
                                         username=username,
                                         user_id=raw_data['data']['user']['id'],
                                         followers_number=raw_data['data']['user']['edge_followed_by']['count'], )
        except ThirdPartyApiException as exc:
            if exc.status == 400:
                if exc.answer['message'] == 'useragent mismatch':
                    raise InvalidCredentials(account_name=username)
                if exc.answer['message'] in ('challenge_required', 'checkpoint_required'):
                    raise AccountConfirmationRequired(account_name=username)

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
            for i in raw_data['reels'][str(user_id)]['items']:
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
                    story.url = self._resolve_stories_link(i['story_link_stickers'][0]['story_link']['url'],
                                                           account.proxy)
                    if 'ozon' in story.url:
                        story.marketplace = Marketplaces.ozon
                    elif 'wildberries' in story.url:
                        story.marketplace = Marketplaces.wildberries
                    story.ad_type = AdType.link

                stories_list.append(story)

            return InstagramClientAnswer(source=ThirdPartyAPISource.instagram,
                                         username=username,
                                         stories_list=stories_list)
        except ThirdPartyApiException as exc:
            if exc.status == 400:
                if exc.answer['message'] == 'useragent mismatch':
                    raise InvalidCredentials(account_name=username)
                if exc.answer['message'] in ('challenge_required', 'checkpoint_required'):
                    raise AccountConfirmationRequired(account_name=username)

    def _resolve_stories_link(self, url: str, proxy: str) -> str:
        version_main = int(chromedriver_autoinstaller.get_chrome_version().split(".")[0])
        proxy = SeleniumProxyHandler(*SeleniumProxyHandler.convert_to_selenium_format(proxy))
        options = webdriver.ChromeOptions()
        options.add_argument(f'--load-extension={proxy.directory}')
        driver = webdriver.Chrome(version_main=version_main, headless=True, options=options)
        try:
            driver.get(url)
            button = driver.find_element(By.TAG_NAME, 'button')
            button.click()
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, '__ozon'))
            )
            link = driver.current_url
            return link
        except Exception as e:
            print(e)
        finally:
            driver.quit()
