from datetime import datetime

from pydantic import BaseModel, Field
from enum import Enum


class ThirdPartyAPISource(Enum):
    """
    Defines available api sources for third party APIs.
    """
    instagram = 'instagram'


class ThirdPartyAPIMediaType(Enum):
    """
    Defines available media types from third party APIs.
    """
    unknown = 0
    photo = 1
    video = 2
    audio = 3
    gif = 4


class AdType(Enum):
    """
    Defines available types of adverts.
    """
    text = 'text'
    link = 'link'


class Marketplaces(Enum):
    """
    Defines available media types from third party APIs.
    """
    ozon = 'ozon'
    wildberries = 'wildberries'


class InstagramStory(BaseModel):
    media_type: ThirdPartyAPIMediaType = Field(default=ThirdPartyAPIMediaType.unknown)
    url: str
    created_at: datetime = Field(default=None)
    external_url: str = Field(default=None)
    sku: int = Field(default=None)
    marketplace: Marketplaces = Field(default=None)
    ad_type: AdType = Field(default=None)


class ThirdPartyAPIClientAnswer(BaseModel):
    source: ThirdPartyAPISource


class InstagramClientAnswer(ThirdPartyAPIClientAnswer):
    """
    Response from Instagram API.
    """
    user_id: int = Field(default=None)
    username: str
    followers_number: int = Field(default=None)
    stories_list: list[InstagramStory] = Field(default_factory=list)
