"""M4 tests — analytics, notifications, report guards."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, register_and_login


@pytest.mark.asyncio
async def test_team_overview_empty_is_zeroed(client: AsyncClient):
    token = await register_and_login(client, "admin@test.com", "admin")
    resp = await client.get("/api/v1/analytics/team-overview", headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_athletes"] == 0
    assert data["avg_risk_score"] is None


@pytest.mark.asyncio
async def test_team_overview_requires_auth(client: AsyncClient):
    assert (await client.get("/api/v1/analytics/team-overview")).status_code == 401


@pytest.mark.asyncio
async def test_notifications_list_and_read_all(client: AsyncClient):
    token = await register_and_login(client, "coach@test.com", "coach")
    resp = await client.get("/api/v1/notifications", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    resp = await client.post("/api/v1/notifications/read-all", headers=auth_header(token))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_report_endpoints_guard_missing_video(client: AsyncClient):
    token = await register_and_login(client, "coach@test.com", "coach")
    for path in ("report.pdf", "report.xlsx"):
        resp = await client.get(f"/api/v1/videos/00000000-0000-0000-0000-000000000000/{path}",
                                headers=auth_header(token))
        assert resp.status_code in (403, 404)
