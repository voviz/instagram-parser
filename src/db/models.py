from tortoise import fields
from tortoise.models import Model


class IdMixin:
    id = fields.IntField(pk=True)


class InstagramAccounts(Model, IdMixin):
    credentials = fields.CharField(max_length=255, unique=True)
    cookies = fields.CharField(max_length=5000)
    user_agent = fields.CharField(max_length=255)
    proxy = fields.CharField(max_length=255, null=True)
    last_used_at = fields.DatetimeField(null=True)
    daily_usage_rate = fields.IntField(default=0)

    class Meta:
        table = 'instagram_accounts'


class InstagramLogins(Model, IdMixin):
    username = fields.CharField(max_length=255, unique=True)
    user_id = fields.BigIntField(null=True)
    followers = fields.BigIntField(null=True)
    is_exists = fields.BooleanField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(null=True)

    class Meta:
        table = 'instagram_logins'


class Proxies(Model, IdMixin):
    proxy = fields.CharField(max_length=255, unique=True)
    type = fields.CharField(max_length=255)

    class Meta:
        table = 'proxies'


class ParserResult(Model, IdMixin):
    instagram_username = fields.CharField(max_length=255)
    marketplace = fields.CharField(max_length=255, null=True)
    story_publication_date = fields.DatetimeField(null=True)
    sku = fields.BigIntField(null=True)
    ad_type = fields.CharField(max_length=255, null=True)
    is_checked = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'parser_result'
        unique_together = ('story_publication_date', 'sku')
