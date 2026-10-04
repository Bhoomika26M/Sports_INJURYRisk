"""Shared test fixtures — real Postgres (localhost:5433 test db), tables per test."""

import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://injury_user:changeme_in_production@localhost:5433/injury_detection_test",
)
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/1")

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import Base, get_db
from app.main import app as fastapi_app

import app.modules.users.models  # noqa: F401
import app.modules.athletes.models  # noqa: F401
import app.modules.video.models  # noqa: F401
import app.modules.risk_scoring.models  # noqa: F401
import app.modules.recommendations.models  # noqa: F401
import app.modules.notifications.models  # noqa: F401

test_engine = create_async_engine(os.environ["DATABASE_URL"], echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    from app.seed import seed_movements

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        await seed_movements(session)
        await session.commit()
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    # Redis holds state the database reset does not touch (e.g. the baseline-recompute debounce key), so a
    # previous test's key made later tests answer 429 depending on test ORDER and timing. Start each test clean.
    import redis.asyncio as _aioredis
    _r = _aioredis.from_url(os.environ["REDIS_URL"])
    await _r.flushdb()
    await (getattr(_r, "aclose", None) or _r.close)()      # aclose() only exists in redis-py >= 5.0.1

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()
    # `get_redis()` caches one client in a module global. pytest gives every test its own event loop, so a
    # client created by an earlier test is bound to a CLOSED loop ("Event loop is closed") the next time an
    # endpoint touches Redis. Production has one loop and is unaffected; drop the cached client per test.
    import app.core.deps as _deps
    pool, _deps._redis_pool = getattr(_deps, "_redis_pool", None), None
    if pool is not None:
        try:
            await (getattr(pool, "aclose", None) or pool.close)()
        except Exception:
            pass


async def register_and_login(client: AsyncClient, email: str, role: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": "testpassword123",
        "full_name": f"Test {role}", "role": role,
    })
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "testpassword123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
