from datetime import datetime

from pydantic import BaseModel, Field
from enum import StrEnum, IntEnum


class ThirdPartyAPISource(StrEnum):
    """
    Defines available media types from third party APIs.
    """
    instagram = 'instagram'
    ozon = 'ozon'
    wildberries = 'wildberries'


class ThirdPartyAPIMediaType(IntEnum):
    """
    Defines available media types from third party APIs.
    """
    unknown = 0
    photo = 1
    video = 2
    audio = 3
    gif = 4


class InstagramStory(BaseModel):
    media_type: ThirdPartyAPIMediaType = Field(default=ThirdPartyAPIMediaType.unknown)
    url: str
    created_at: datetime = Field(default=None)


class ThirdPartyAPIClientAnswer(BaseModel):
    source: ThirdPartyAPISource


class InstagramClientAnswer(ThirdPartyAPIClientAnswer):
    """
    Response from Instagram API.
    """
    user_id: int = Field(default=None)
    username: str
    stories_list: list[InstagramStory] = Field(default_factory=list)
