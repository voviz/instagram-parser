from parser.exceptions import ThirdPartyApiException, AccountConfirmationRequired, InvalidCredentials
from parser.models import InstagramClientAnswer, ThirdPartyAPISource, InstagramStory, ThirdPartyAPIMediaType
from src.parser.base import BaseThirdPartyAPIClient
from db.crud.instagram_accounts import InstagramAccountsTableDBHandler


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
            for i in raw_data['data']['reels']['items']:
                if i['media_type'] == ThirdPartyAPIMediaType.photo:
                    story = InstagramStory(media_type=ThirdPartyAPIMediaType.photo,
                                           url=i['image_versions2'][0]['url'],
                                           created_at=i['taken_at'])
                    stories_list.append(story)
                if i['media_type'] == ThirdPartyAPIMediaType.video:
                    story = InstagramStory(media_type=ThirdPartyAPIMediaType.video,
                                           url=i['video_versions'][0]['url'],
                                           created_at=i['taken_at'])
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
