import uuid

import structlog
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.keys import hash_api_key
from app.core.lifespan import get_db
from app.db.models import ApiKey

logger = structlog.get_logger()


async def get_api_key_record(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Use: Bearer sk-...",
        )
    raw_key = authorization.removeprefix("Bearer ").strip()
    key_hash = hash_api_key(raw_key)
    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    record = result.scalar_one_or_none()
    if record is None or not record.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    if record.budget_usd is not None and record.spent_usd >= record.budget_usd:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Budget exceeded")
    return record


def new_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:16]}"
