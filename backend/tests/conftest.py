"""Shared test fixtures for the backend test suite."""

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Override env before importing app
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://injury_user:changeme_in_production@postgres:5432/injury_detection",
)

from app.database import Base, get_db
from app.main import app

# Import all models so metadata knows about them
from app.modules.users.models import User, RefreshToken  # noqa: F401
from app.modules.athletes.models import Athlete, InjuryHistory, TrainingLoadEntry  # noqa: F401
from app.modules.videos.models import Video, PoseFrame, BiomechanicalMetric  # noqa: F401

from sqlalchemy.pool import NullPool

# Test database engine
test_engine = create_async_engine(
    os.environ["DATABASE_URL"],
    echo=False,
    poolclass=NullPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test.

    Creates all tables before the test and drops them after.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client wired to the test database."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def create_test_user(
    client: AsyncClient,
    email: str = "test@example.com",
    password: str = "testpassword123",
    full_name: str = "Test User",
    role: str = "coach",
) -> dict:
    """Helper: register a user and return the response data."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": role,
        },
    )
    return response


async def login_test_user(
    client: AsyncClient,
    email: str = "test@example.com",
    password: str = "testpassword123",
) -> dict:
    """Helper: login a user and return (response, access_token)."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return response


def auth_header(access_token: str) -> dict:
    """Build an Authorization header dict."""
    return {"Authorization": f"Bearer {access_token}"}
