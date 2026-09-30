"""M4 tests — analytics overview, notifications, report guards."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, create_test_user, login_test_user


async def _token(client: AsyncClient, email: str, role: str) -> str:
    await create_test_user(client, email=email, role=role, full_name=f"Test {role}")
    resp = await login_test_user(client, email=email)
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_team_overview_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/team-overview")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_team_overview_empty_is_zeroed(client: AsyncClient):
    token = await _token(client, "admin_m4@test.com", "admin")
    resp = await client.get("/api/v1/analytics/team-overview", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_athletes"] == 0
    assert data["total_videos"] == 0
    assert data["avg_risk_score"] is None


@pytest.mark.asyncio
async def test_notifications_list_empty(client: AsyncClient):
    token = await _token(client, "coach_m4@test.com", "coach")
    resp = await client.get("/api/v1/notifications", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_report_pdf_requires_scoring(client: AsyncClient):
    token = await _token(client, "coach_pdf@test.com", "coach")
    resp = await client.get(
        "/api/v1/videos/00000000-0000-0000-0000-000000000000/report.pdf",
        headers=auth_header(token),
    )
    assert resp.status_code in (404, 403)
