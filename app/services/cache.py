import hashlib
import json
import time

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.lifespan import get_redis
from app.db.models import ApiKey


async def check_rate_limit(api_key: ApiKey, redis: aioredis.Redis) -> None:
    key = f"ratelimit:{api_key.id}"
    now = time.time()
    window = api_key.rate_limit_window_seconds
    limit = api_key.rate_limit_requests
    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, now - window)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window + 1)
    _, _, count, _ = await pipe.execute()
    if count > limit:
        from fastapi import HTTPException

        raise HTTPException(status_code=429, detail="Rate limit exceeded")


def cache_key(model: str, messages: list[dict]) -> str:
    payload = json.dumps({"model": model, "messages": messages}, sort_keys=True)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"cache:{digest}"


async def get_cached_response(redis: aioredis.Redis, key: str) -> dict | None:
    if not settings.cache_enabled:
        return None
    raw = await redis.get(key)
    if raw:
        return json.loads(raw)
    return None


async def set_cached_response(redis: aioredis.Redis, key: str, response: dict) -> None:
    if settings.cache_enabled:
        await redis.setex(key, settings.cache_ttl_seconds, json.dumps(response))
