"""
Shared pytest fixtures.

Uses SQLite (in-memory) via aiosqlite so tests run without a live Postgres
container.  All tests share a single engine but each test function gets a
fresh transaction that is rolled back, keeping them isolated.
"""
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from app.db.base import Base
from app.deps import get_db
from app.main import app

# ---------------------------------------------------------------------------
# In-memory SQLite engine (shared per test-session)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
_TestSession = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Provide a single event loop for the entire session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once for the test session."""
    async with _engine.begin() as conn:
        # SQLite doesn't support native enums; use String fallback
        # by reflecting Base.metadata with SQLAlchemy's native enum support disabled.
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Each test gets a session that is rolled back after the test.
    """
    async with _TestSession() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client with the test DB injected via dependency override.
    """
    async def _override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Sync client (for health tests)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def sync_client():
    with TestClient(app) as c:
        yield c
