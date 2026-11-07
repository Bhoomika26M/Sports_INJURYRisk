"""Tests for Within-Athlete Metric History and Rolling Baseline Comparison (U1)."""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient

from app.modules.users.models import UserRole
from tests.conftest import auth_header, register_and_login
from tests.factories import make_user, make_athlete, make_video


@pytest.mark.asyncio
async def test_history_comparison_requires_3_priors(client: AsyncClient, db_session):
    """Proves U1: videos with < 3 priors return HTTP 202; >= 3 priors returns 200 comparison."""
    coach = await make_user(db_session, "hist_coach@test.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=coach.id)
    token = await register_and_login(client, "hist_coach@test.com", "coach")
    headers = auth_header(token)

    now = datetime.now(timezone.utc)
    priors = []
    for i in range(3):
        v = await make_video(
            db_session,
            athlete.id,
            coach.id,
            movement_type="squatting",
        )
        v.created_at = now - timedelta(days=10 - i)
        v.analysis = {
            "version": "2.3",
            "quality": {"grade": "good", "coverage_caveat": None},
            "movement": {
                "metrics": {
                    "knee_flexion_angle_left": 95.0 + i * 2,
                    "knee_flexion_angle_right": 94.0 + i * 2,
                    "trunk_lean_angle": 20.0 + i,
                }
            },
        }
        priors.append(v)
    await db_session.commit()

    # Prior 1 has 0 prior videos -> 202
    r0 = await client.get(f"/api/v1/videos/{priors[0].id}/history-comparison", headers=headers)
    assert r0.status_code == 202
    b0 = r0.json()
    assert b0["status"] == "history_building"
    assert b0["have"] == 0
    assert b0["need"] == 3

    # Prior 3 has 2 prior videos -> 202
    r2 = await client.get(f"/api/v1/videos/{priors[2].id}/history-comparison", headers=headers)
    assert r2.status_code == 202
    assert r2.json()["have"] == 2

    # Now add the 4th video (target), which has exactly 3 prior videos
    target = await make_video(
        db_session,
        athlete.id,
        coach.id,
        movement_type="squatting",
    )
    target.created_at = now
    target.analysis = {
        "version": "2.3",
        "quality": {"grade": "good", "coverage_caveat": None},
        "movement": {
            "metrics": {
                "knee_flexion_angle_left": 97.0,
                "knee_flexion_angle_right": 96.0,
                "trunk_lean_angle": 21.0,
            }
        },
    }
    await db_session.commit()

    r_target = await client.get(f"/api/v1/videos/{target.id}/history-comparison", headers=headers)
    assert r_target.status_code == 200
    body = r_target.json()
    assert body["movement_type"] == "squatting"
    assert len(body["deltas"]) > 0
    # Median of priors (95, 97, 99) = 97. Target is 97. Delta = 0, within_noise.
    kf_l = next((d for d in body["deltas"] if d["metric"] == "knee_flexion_angle_left"), None)
    assert kf_l is not None
    assert kf_l["verdict"] == "within_noise"


@pytest.mark.asyncio
async def test_athlete_history_endpoint(client: AsyncClient, db_session):
    """GET /api/v1/athletes/{id}/history lists all completed videos and metrics."""
    coach = await make_user(db_session, "hist_coach2@test.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=coach.id)
    token = await register_and_login(client, "hist_coach2@test.com", "coach")
    headers = auth_header(token)

    v1 = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    v1.analysis = {
        "quality": {"grade": "good"},
        "movement": {"metrics": {"knee_flexion_angle_left": 100.0}},
    }
    await db_session.commit()

    resp = await client.get(f"/api/v1/athletes/{athlete.id}/history", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["athlete_id"] == athlete.id
    assert body["total_videos"] >= 1
    assert body["videos"][0]["video_id"] == v1.id
    assert body["videos"][0]["metrics"]["knee_flexion_angle_left"] == 100.0


@pytest.mark.asyncio
async def test_athlete_history_unauthorized_coach(client: AsyncClient, db_session):
    """Unrelated coach cannot access athlete history (403)."""
    coach1 = await make_user(db_session, "c1@test.com", role=UserRole.coach)
    coach2 = await make_user(db_session, "c2@test.com", role=UserRole.coach)
    athlete = await make_athlete(db_session, coach_id=coach1.id)
    await db_session.commit()

    attacker_token = await register_and_login(client, "c2@test.com", "coach")
    resp = await client.get(f"/api/v1/athletes/{athlete.id}/history", headers=auth_header(attacker_token))
    assert resp.status_code == 403
