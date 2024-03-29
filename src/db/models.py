from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class IdMixin:
    id = Column(Integer, primary_key=True)  # noqa: A003


class InstagramAccounts(Base, IdMixin):
    __tablename__ = 'instagram_accounts'

    credentials = Column(String(255), unique=True)
    cookies = Column(String(5000))
    user_agent = Column(String(255))
    proxy = Column(String(255), nullable=True)
    last_used_at = Column(type_=TIMESTAMP(timezone=True), nullable=True)
    daily_usage_rate = Column(Integer, default=0)


class InstagramLogins(Base, IdMixin):
    __tablename__ = 'instagram_logins'

    username = Column(String(255), unique=True)
    user_id = Column(BigInteger, unique=True)
    followers = Column(BigInteger, nullable=True)
    is_exists = Column(Boolean, nullable=True)
    created_at = Column(type_=TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(type_=TIMESTAMP(timezone=True), nullable=True)
    posts_updated_at = Column(type_=TIMESTAMP(timezone=True), nullable=True)


class Proxies(Base, IdMixin):
    __tablename__ = 'proxies'

    proxy = Column(String(255), unique=True)
    type = Column(String(255))  # noqa: A003


class ParserResult(Base, IdMixin):
    __tablename__ = 'parser_result'

    user_id = Column(BigInteger, ForeignKey('instagram_logins.user_id'), nullable=True)
    marketplace = Column(String(255), nullable=True)
    story_publication_date = Column(type_=TIMESTAMP(timezone=True), nullable=True)
    sku = Column(BigInteger, nullable=True)
    ad_type = Column(String(255), nullable=True)
    is_checked = Column(Boolean, default=False)
    created_at = Column(type_=TIMESTAMP(timezone=True), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('story_publication_date', 'sku'),)


class ParserResultPost(Base, IdMixin):
    __tablename__ = 'parser_result_post'

    user_id = Column(BigInteger, ForeignKey('instagram_logins.user_id'))
    post_id = Column(BigInteger, unique=True)
    link = Column(String, nullable=True)
    comments_count = Column(Integer, nullable=True)
    likes_count = Column(Integer, nullable=True)
    publication_date = Column(type_=TIMESTAMP(timezone=True))
    created_at = Column(type_=TIMESTAMP(timezone=True), default=datetime.utcnow)


class InstSkuPerPost(Base, IdMixin):
    __tablename__ = 'inst_sku_per_post'

    parser_result_post_id = Column(Integer, ForeignKey('parser_result_post.id'))
    marketplace = Column(String(255), nullable=True)
    sku = Column(BigInteger)
    is_checked = Column(Boolean, default=False)
    brand = Column(String(255), nullable=True)
    brand_id = Column(BigInteger, nullable=True)
