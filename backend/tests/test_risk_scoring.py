"""Risk scoring tests — validation, RBAC, breakdown transparency."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, register_and_login


@pytest.mark.asyncio
async def test_compute_risk_score_breakdown_is_transparent():
    from app.modules.risk_scoring.scoring import compute_risk_score

    result = compute_risk_score([80.0, 85.0, 90.0], 85.0, True, acwr=1.8, rpe_trend=0.2)
    breakdown = result["score_breakdown"]
    expected_base = min(70.0, sum([80.0, 85.0, 90.0]) / 3 * 0.7)
    assert breakdown.movement_anomaly.points == round(expected_base, 1)
    assert breakdown.asymmetry_flag.points == 15.0
    assert breakdown.prior_injury_flag.points == 10.0
    assert breakdown.acwr_flag.points == 10.0
    assert breakdown.fatigue_flag.points == 0.0
    assert result["overall_score"] == round(min(100.0, expected_base + 35.0), 1)
    assert result["risk_category"] in ("low", "moderate", "high", "critical")


@pytest.mark.asyncio
async def test_baseline_recompute_rejects_invalid_movement(client: AsyncClient):
    token = await register_and_login(client, "admin@test.com", "admin")
    resp = await client.post("/api/v1/baselines/recompute",
                             json={"movement_type": "not_a_real_movement"},
                             headers=auth_header(token))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_baseline_recompute_requires_privileged_role(client: AsyncClient):
    token = await register_and_login(client, "coach@test.com", "coach")
    resp = await client.post("/api/v1/baselines/recompute",
                             json={"movement_type": "squatting"},
                             headers=auth_header(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_risk_score_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/videos/00000000-0000-0000-0000-000000000000/risk-score")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_recommendations_trace_to_breakdown():
    from app.modules.recommendations.rules import generate_recommendations
    from app.modules.risk_scoring.scoring import compute_risk_score

    result = compute_risk_score([90.0], 80.0, True)
    recs = generate_recommendations(result["score_breakdown"])
    titles = {r["title"] for r in recs}
    assert "Address limb asymmetry" in titles
    assert "Prior injury monitoring" in titles
    assert all(1 <= r["priority"] <= 5 for r in recs)
