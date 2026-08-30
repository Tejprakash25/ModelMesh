from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.keys import hash_api_key
from app.core.config import settings
from app.db.models import ApiKey


async def seed_dev_api_key(session: AsyncSession) -> None:
    key_hash = hash_api_key(settings.dev_api_key)
    existing = await session.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    if existing.scalar_one_or_none():
        return
    session.add(
        ApiKey(
            name="dev-key",
            key_hash=key_hash,
            key_prefix=settings.dev_api_key[:10],
            project_id="default",
            rate_limit_requests=settings.rate_limit_requests,
            rate_limit_window_seconds=settings.rate_limit_window_seconds,
            budget_usd=100.0,
        )
    )
