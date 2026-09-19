import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient


def test_sync_health_check(sync_client: TestClient):
    """Test root GET /health endpoint using synchronous client."""
    response = sync_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "project_name" in data
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_async_health_check(async_client: AsyncClient):
    """Test root GET /health endpoint using asynchronous client."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "development"


@pytest.mark.asyncio
async def test_api_v1_health_check(async_client: AsyncClient):
    """Test versioned GET /api/v1/health endpoint."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_root_endpoint(sync_client: TestClient):
    """Test root welcome endpoint."""
    response = sync_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Welcome" in data["message"]
