"""Liveness vs readiness. Readiness must fail when Postgres or Redis cannot be reached."""

import pytest
from httpx import AsyncClient

from app.config import settings
from app.core import health
from tests.conftest import test_engine


@pytest.fixture(autouse=True)
def per_test_engine(monkeypatch):
    # The app's module-level engine pools connections bound to the first event loop; every pytest-asyncio test
    # has its own loop. Use the suite's NullPool engine (same database) for the readiness probe.
    monkeypatch.setattr(health, "engine", test_engine)


@pytest.mark.asyncio
async def test_liveness_is_static(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200 and resp.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_readiness_ok_when_database_and_redis_are_reachable(client: AsyncClient):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "database": "ok", "redis": "ok"}


@pytest.mark.asyncio
async def test_readiness_503_when_redis_is_unreachable(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:1/0")
    resp = await client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json() == {"status": "not_ready", "database": "ok", "redis": "unreachable"}


@pytest.mark.asyncio
async def test_readiness_503_when_database_is_unreachable(client: AsyncClient, monkeypatch):
    async def down():
        return False

    monkeypatch.setattr(health, "_check_database", down)
    resp = await client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["database"] == "unreachable" and resp.json()["status"] == "not_ready"
    assert "postgres" not in resp.text.lower() and "password" not in resp.text.lower()   # no URL/credential leak
