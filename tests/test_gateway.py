import pytest
import pytest_asyncio
from contextlib import asynccontextmanager
from fakeredis import aioredis as fakeredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.keys import hash_api_key
from app.core import lifespan as lifespan_module
from app.db.base import Base
from app.db.models import ApiKey
from app.main import app

TEST_DB = "sqlite+aiosqlite:///:memory:"
TEST_KEY = "sk-test-key-for-pytest-only"


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(TEST_DB, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    redis = fakeredis.FakeRedis(decode_responses=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        session.add(
            ApiKey(
                name="test",
                key_hash=hash_api_key(TEST_KEY),
                key_prefix=TEST_KEY[:10],
                rate_limit_requests=5,
                rate_limit_window_seconds=60,
                budget_usd=10.0,
            )
        )
        await session.commit()

    lifespan_module.engine = engine
    lifespan_module.SessionLocal = session_factory
    lifespan_module.redis_client = redis

    @asynccontextmanager
    async def noop_lifespan(_app):
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = noop_lifespan

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.router.lifespan_context = original_lifespan
    await engine.dispose()
    lifespan_module.redis_client = None


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_auth_required(client: AsyncClient):
    r = await client.post("/v1/chat/completions", json={"model": "gpt-4o-mini", "messages": []})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_chat_completions_mock(client: AsyncClient):
    r = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {TEST_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello gateway"}],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "mock-primary" in data["choices"][0]["message"]["content"]
    assert data["usage"]["total_tokens"] > 0


@pytest.mark.asyncio
async def test_rate_limit(client: AsyncClient):
    headers = {"Authorization": f"Bearer {TEST_KEY}"}
    for i in range(5):
        r = await client.post(
            "/v1/chat/completions",
            headers=headers,
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": f"rate test unique {i}"}],
            },
        )
        assert r.status_code == 200
    r = await client.post(
        "/v1/chat/completions",
        headers=headers,
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "rate test overflow"}]},
    )
    assert r.status_code == 429


@pytest.mark.asyncio
async def test_fallback_on_primary_failure(client: AsyncClient):
    r = await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {TEST_KEY}"},
        json={
            "model": "fail",
            "messages": [{"role": "user", "content": "trigger fallback"}],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["fallback_used"] is True
    assert "mock-fallback" in data["choices"][0]["message"]["content"]


@pytest.mark.asyncio
async def test_usage_logged(client: AsyncClient):
    await client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {TEST_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "usage log test unique"}],
        },
    )
    r = await client.get("/usage", headers={"Authorization": f"Bearer {TEST_KEY}"})
    assert r.status_code == 200
    assert r.json()["request_count"] >= 1


@pytest.mark.asyncio
async def test_cache_hit(client: AsyncClient):
    headers = {"Authorization": f"Bearer {TEST_KEY}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "cache unique message xyz"}],
    }
    r1 = await client.post("/v1/chat/completions", headers=headers, json=payload)
    r2 = await client.post("/v1/chat/completions", headers=headers, json=payload)
    assert r1.json()["cached"] is False
    assert r2.json()["cached"] is True
