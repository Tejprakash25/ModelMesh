from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_api_key_record
from app.auth.keys import generate_api_key
from app.core.config import settings
from app.core.lifespan import get_db
from app.db.models import ApiKey, UsageLog
from app.providers.registry import MODEL_ALIASES, PROVIDERS
from app.schemas.openai import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@router.get("/providers")
async def list_providers() -> dict:
    return {
        "providers": list(PROVIDERS.keys()),
        "default": settings.default_provider,
        "fallback": settings.fallback_provider,
        "model_aliases": MODEL_ALIASES,
    }


@router.get("/usage")
async def usage_summary(
    api_key: ApiKey = Depends(get_api_key_record),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.total_tokens), 0),
            func.coalesce(func.sum(UsageLog.estimated_cost_usd), 0),
        ).where(UsageLog.api_key_id == api_key.id)
    )
    count, tokens, cost = result.one()
    return {
        "api_key_id": api_key.id,
        "request_count": count,
        "total_tokens": int(tokens),
        "estimated_cost_usd": round(float(cost), 6),
        "spent_usd": round(api_key.spent_usd, 6),
        "budget_usd": api_key.budget_usd,
    }


@router.get("/keys", response_model=list[ApiKeyResponse])
async def list_keys(
    api_key: ApiKey = Depends(get_api_key_record),
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyResponse]:
    result = await db.execute(select(ApiKey).order_by(ApiKey.id))
    keys = result.scalars().all()
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            project_id=k.project_id,
            is_active=k.is_active,
            rate_limit_requests=k.rate_limit_requests,
            budget_usd=k.budget_usd,
            spent_usd=k.spent_usd,
        )
        for k in keys
    ]


@router.post("/keys", response_model=ApiKeyCreatedResponse)
async def create_key(
    body: ApiKeyCreate,
    api_key: ApiKey = Depends(get_api_key_record),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedResponse:
    raw, key_hash, prefix = generate_api_key()
    record = ApiKey(
        name=body.name,
        key_hash=key_hash,
        key_prefix=prefix,
        project_id=body.project_id,
        rate_limit_requests=body.rate_limit_requests,
        budget_usd=body.budget_usd,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return ApiKeyCreatedResponse(
        id=record.id,
        name=record.name,
        key_prefix=record.key_prefix,
        project_id=record.project_id,
        is_active=record.is_active,
        rate_limit_requests=record.rate_limit_requests,
        budget_usd=record.budget_usd,
        spent_usd=record.spent_usd,
        api_key=raw,
    )
