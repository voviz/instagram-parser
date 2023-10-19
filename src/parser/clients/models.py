from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ThirdPartyAPISource(str, Enum):
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
    carousel = 5


class AdType(str, Enum):
    """
    Defines available types of adverts.
    """

    text = 'text'
    link = 'link'


class Marketplaces(str, Enum):
    """
    Defines available media types from third party APIs.
    """

    ozon = 'ozon'
    wildberries = 'wildberries'


class InstagramStory(BaseModel):
    media_type: ThirdPartyAPIMediaType = Field(default=ThirdPartyAPIMediaType.unknown)
    url: str
    created_at: datetime = Field(default=None)
    sku: int = Field(default=None)
    marketplace: Marketplaces = Field(default=None)
    ad_type: AdType = Field(default=None)
    brand: str = Field(default=None)
    brand_id: int = Field(default=None)


class InstagramPost(BaseModel):
    media_type: ThirdPartyAPIMediaType = Field(default=ThirdPartyAPIMediaType.unknown)
    post_id: int = Field(default=None)
    created_at: datetime = Field(default=None)
    url: str = Field(default=None)
    caption: str = Field(default=None)
    sku: int = Field(default=None)
    marketplace: Marketplaces = Field(default=None)
    ad_type: AdType = Field(default=None)
    likes_count: int = Field(default=None)
    comments_count: int = Field(default=None)
    brand: str = Field(default=None)
    brand_id: int = Field(default=None)


class ThirdPartyAPIClientAnswer(BaseModel):
    source: ThirdPartyAPISource = Field(default=ThirdPartyAPISource.instagram)


class InstagramClientAnswer(ThirdPartyAPIClientAnswer):
    """
    Response from Instagram API.
    """

    user_id: int = Field(default=None)
    username: str
    followers_number: int = Field(default=None)
    stories_list: list[InstagramStory] = Field(default_factory=list)
    posts_list: list[InstagramPost] = Field(default_factory=list)
