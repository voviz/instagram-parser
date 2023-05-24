from parser.exceptions import ThirdPartyApiException, AccountConfirmationRequired, InvalidCredentials
from parser.models import InstagramClientAnswer, ThirdPartyAPISource
from src.parser.base import BaseThirdPartyAPIClient


class InstagramClient(BaseThirdPartyAPIClient):
    """
    Custom instagram API
    """
    api_name = 'InstagramAPI'
    base_url = 'https://www.instagram.com/api/v1'

    async def get_account_info_by_user_name(self, username: str) -> InstagramClientAnswer:
        try:
            raw_data = await self.request(
                method=BaseThirdPartyAPIClient.HTTPMethods.GET,
                edge='users/web_profile_info',
                querystring={'username': username},
                is_json=True,
                cookie='mid=ZDgFmgABAAGUvUCNRvZdcie-MyfY;rur=EAG,58960929738,1712929195:01f70d9ca515b3edb1a4185d37934dc3f70e78fd9abfc38238d9dc993612be6f5ace3be5;ds_user_id=58960929738;sessionid=58960929738%3AaR4R7bS1DtREbD%3A19%3AAYdVLTHnPIf4gxocet34YVFsEP-OrVGaTZXGr3o0WQ;X-MID=ZDgFmgABAAGUvUCNRvZdcie-MyfY;IG-U-RUR=NCG,58960929738,1713960516:01f7ee7c426e1d6f3fbf92e157ccffaba8efdd7f844b340c0b58e713bac01ac86a9bcf21;IG-U-DS-USER-ID=58960929738;IG-INTENDED-USER-ID=58960929738;Authorization=Bearer IGT:2:eyJkc191c2VyX2lkIjoiNTg5NjA5Mjk3MzgiLCJzZXNzaW9uaWQiOiI1ODk2MDkyOTczOCUzQWFSNFI3YlMxRHRSRWJEJTNBMTklM0FBWWRWTFRIblBJZjRneG9jZXQzNFlWRnNFUC1PclZHYVRaWEdyM28wV1EifQ==;X-IG-WWW-Claim=hmac.AR2k4BQ75eFqf8uSWXOMiL84OSh0taCGgmIOBx6oXbkwZMqn;',
                user_agent='Instagram 271.1.0.21.84 Android (25/7.1.2; 80dpi; 240x320; Asus; ASUS_Z01QD; sdm845; qcom; en_US; 324500927)',
                proxy='195.201.161.7:32305:mKMzLxn19pn4:Cvfc4LXm0d'
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
            raw_data = await self.request(
                method=BaseThirdPartyAPIClient.HTTPMethods.GET,
                edge='feed/reels_media',
                querystring={'reel_ids': user_id},
                is_json=True,
            )
            return raw_data
        except ThirdPartyApiException as exc:
            if exc.status == 400:
                if exc.answer['message'] == 'useragent mismatch':
                    raise InvalidCredentials(account_name=username)
                if exc.answer['message'] in ('challenge_required', 'checkpoint_required'):
                    raise AccountConfirmationRequired(account_name=username)
