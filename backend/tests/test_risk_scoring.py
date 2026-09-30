"""Risk scoring endpoint tests — validation, RBAC, insufficient-baseline path."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, create_test_user, login_test_user


async def _register_and_login(client: AsyncClient, email: str, role: str) -> str:
    await create_test_user(client, email=email, role=role, full_name=f"Test {role}")
    resp = await login_test_user(client, email=email)
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_compute_risk_score_breakdown_is_transparent():
    """Unit: breakdown components sum (capped) to overall_score."""
    from app.modules.risk_scoring.scoring import compute_risk_score

    result = compute_risk_score([80.0, 85.0, 90.0], 85.0, True)
    breakdown = result["score_breakdown"]
    expected_base = min(70.0, sum([80.0, 85.0, 90.0]) / 3 * 0.7)
    assert breakdown.movement_anomaly.points == round(expected_base, 1)
    assert breakdown.asymmetry_flag.points == 15.0
    assert breakdown.prior_injury_flag.points == 15.0
    assert result["overall_score"] == round(min(100.0, expected_base + 30.0), 1)
    assert result["risk_category"] in ("low", "moderate", "high", "critical")


@pytest.mark.asyncio
async def test_baseline_recompute_rejects_invalid_movement_type(client: AsyncClient):
    """Invalid movement_type enum — 422 before any DB/redis work."""
    token = await _register_and_login(client, "admin_risk@test.com", "admin")
    resp = await client.post(
        "/api/v1/baselines/recompute",
        json={"movement_type": "not_a_real_movement"},
        headers=auth_header(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_baseline_recompute_requires_privileged_role(client: AsyncClient):
    """Coach cannot recompute baselines — 403."""
    token = await _register_and_login(client, "coach_risk@test.com", "coach")
    resp = await client.post(
        "/api/v1/baselines/recompute",
        json={"movement_type": "squatting"},
        headers=auth_header(token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_risk_score_requires_auth(client: AsyncClient):
    """No token on risk-score — 401."""
    resp = await client.get("/api/v1/videos/00000000-0000-0000-0000-000000000000/risk-score")
    assert resp.status_code == 401
