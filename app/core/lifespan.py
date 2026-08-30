from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import Base
from app.db import models  # noqa: F401
from app.services.seed import seed_dev_api_key


engine = create_async_engine(settings.database_url, echo=settings.debug)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
redis_client: aioredis.Redis | None = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


def get_redis() -> aioredis.Redis:
    if redis_client is None:
        raise RuntimeError("Redis not initialized")
    return redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    setup_logging()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    async with SessionLocal() as session:
        await seed_dev_api_key(session)
        await session.commit()
    yield
    if redis_client:
        await redis_client.aclose()
    await engine.dispose()
