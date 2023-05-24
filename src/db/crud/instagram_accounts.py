import tortoise

from db.models import InstagramAccounts


class InstagramAccountsTableDBHandler:
    @classmethod
    async def get_all_instagram_accounts(cls) -> list[InstagramAccounts]:
        return await InstagramAccounts.all()

    @classmethod
    async def get_instagram_account(cls) -> InstagramAccounts:
        query = InstagramAccounts.all().order_by('last_used_at')
        # update last_used_at field
        await query.update(last_used_at=tortoise.timezone.now())
        return await query.first()

    @classmethod
    async def mark_as_banned(cls, account: InstagramAccounts) -> None:
        await InstagramAccounts.filter(credentials=account.credentials).update(is_banned=True)