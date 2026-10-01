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


# ---- Defects 2 + 3 at the API: the 202 gate counts VIDEOS and ATHLETES, never frame rows -------

import numpy as np  # noqa: E402

from app.modules.risk_scoring.constants import MIN_BASELINE_ATHLETES, MIN_BASELINE_VIDEOS  # noqa: E402
from tests.factories import make_athlete, make_population, make_user, make_video, normal_frames  # noqa: E402

METRICS = ("knee_flexion_angle_left", "knee_flexion_angle_right")


async def _score(client: AsyncClient, video_id: str, token: str, **params):
    return await client.get(f"/api/v1/videos/{video_id}/risk-score", params=params, headers=auth_header(token))


@pytest.mark.asyncio
async def test_single_video_of_one_athlete_is_202_regardless_of_frame_count(client: AsyncClient, db_session):
    """The real squat clip: 426 rows per metric, one video, one person. Previously scored 200."""
    token = await register_and_login(client, "admin@gate.example.com", "admin")
    coach = await make_user(db_session, "coach@gate.example.com")
    athlete = await make_athlete(db_session, coach.id)
    rng = np.random.default_rng(0)
    video = await make_video(db_session, athlete.id, coach.id, metrics={m: normal_frames(rng, 426) for m in METRICS})

    resp = await _score(client, video.id, token)
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "insufficient_baseline_data"
    assert body["unit"] == "videos"
    assert body["have"] == 0            # the video is never counted in its own baseline
    assert body["need"] == MIN_BASELINE_VIDEOS
    assert body["coverage"]["frames"]["have"] == 0
    assert "never counted in its own baseline" in body["message"]


@pytest.mark.asyncio
async def test_one_video_short_of_the_floor_is_still_202_because_the_video_does_not_count_itself(client, db_session):
    token = await register_and_login(client, "admin@gate2.example.com", "admin")
    _, _, videos = await make_population(db_session, videos=MIN_BASELINE_VIDEOS, athletes=MIN_BASELINE_ATHLETES, seed=5)
    resp = await _score(client, videos[0].id, token)   # 5 videos exist, but only 4 OTHER ones
    assert resp.status_code == 202
    assert (resp.json()["unit"], resp.json()["have"], resp.json()["need"]) == ("videos", MIN_BASELINE_VIDEOS - 1, MIN_BASELINE_VIDEOS)


@pytest.mark.asyncio
async def test_many_videos_from_too_few_athletes_is_202_on_athletes(client, db_session):
    token = await register_and_login(client, "admin@gate3.example.com", "admin")
    _, _, videos = await make_population(db_session, videos=MIN_BASELINE_VIDEOS + 3, athletes=MIN_BASELINE_ATHLETES - 1, seed=6)
    resp = await _score(client, videos[0].id, token)
    body = resp.json()
    assert resp.status_code == 202 and body["unit"] == "athletes"
    assert (body["have"], body["need"]) == (MIN_BASELINE_ATHLETES - 1, MIN_BASELINE_ATHLETES)
    assert body["coverage"]["videos"]["have"] >= MIN_BASELINE_VIDEOS   # videos were fine; athletes were not


@pytest.mark.asyncio
async def test_real_population_scores_and_a_normal_athlete_is_low_not_moderate(client, db_session):
    token = await register_and_login(client, "admin@gate4.example.com", "admin")
    coach, people, _ = await make_population(db_session, videos=MIN_BASELINE_VIDEOS, athletes=MIN_BASELINE_ATHLETES, frames=200, seed=7)
    rng = np.random.default_rng(70)
    subject = await make_video(db_session, people[0].id, coach.id, metrics={m: normal_frames(rng, 200) for m in METRICS})

    resp = await _score(client, subject.id, token)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    anomaly = body["score_breakdown"]["movement_anomaly"]
    assert anomaly["points"] < 5.0          # was ~37 of 70 for a perfectly normal athlete
    assert body["risk_category"] == "low"
    assert f"{MIN_BASELINE_VIDEOS} other videos" in anomaly["detail"] and "excluded" in anomaly["detail"]


@pytest.mark.asyncio
async def test_clearly_deviant_athlete_scores_high_against_the_same_population(client, db_session):
    token = await register_and_login(client, "admin@gate5.example.com", "admin")
    coach, people, _ = await make_population(db_session, videos=MIN_BASELINE_VIDEOS, athletes=MIN_BASELINE_ATHLETES, frames=200, seed=8)
    rng = np.random.default_rng(80)
    deviant = await make_video(db_session, people[0].id, coach.id,
                               metrics={m: normal_frames(rng, 200, mu=90 + 8 * 8) for m in METRICS})
    resp = await _score(client, deviant.id, token)
    body = resp.json()
    assert resp.status_code == 200
    assert body["score_breakdown"]["movement_anomaly"]["points"] > 50.0
    assert body["risk_category"] == "high"


@pytest.mark.asyncio
async def test_score_is_unchanged_by_the_subject_own_rows_being_in_the_table(client, db_session):
    """Endpoint-level leakage check: adding a clone of the subject to the DB changes the baseline
    (it is another video) but the subject's own rows never do."""
    token = await register_and_login(client, "admin@gate6.example.com", "admin")
    coach, people, _ = await make_population(db_session, videos=MIN_BASELINE_VIDEOS, athletes=MIN_BASELINE_ATHLETES, frames=200, seed=9)
    rng = np.random.default_rng(90)
    subject = await make_video(db_session, people[0].id, coach.id,
                               metrics={m: normal_frames(rng, 200, mu=90 + 6 * 8) for m in METRICS})
    first = (await _score(client, subject.id, token)).json()["score_breakdown"]["movement_anomaly"]["points"]
    second = (await _score(client, subject.id, token, recompute=True)).json()["score_breakdown"]["movement_anomaly"]["points"]
    assert first == second and first > 30.0


@pytest.mark.asyncio
async def test_risk_score_forbidden_for_unrelated_athlete_user(client, db_session):
    _, _, videos = await make_population(db_session, videos=MIN_BASELINE_VIDEOS, athletes=MIN_BASELINE_ATHLETES, seed=10)
    token = await register_and_login(client, "someone@else.example.com", "athlete")
    resp = await _score(client, videos[0].id, token)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_risk_score_rejects_a_malformed_video_id_with_422(client):
    token = await register_and_login(client, "admin@gate7.example.com", "admin")
    resp = await client.get("/api/v1/videos/not-a-uuid/risk-score", headers=auth_header(token))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_baseline_recompute_reports_units_and_nulls_when_insufficient(client, db_session):
    token = await register_and_login(client, "admin@gate8.example.com", "admin")
    coach = await make_user(db_session, "coach@gate8.example.com")
    athlete = await make_athlete(db_session, coach.id)
    await make_video(db_session, athlete.id, coach.id, metrics={METRICS[0]: normal_frames(np.random.default_rng(0), 426)})
    resp = await client.post("/api/v1/baselines/recompute", json={"movement_type": "squatting"}, headers=auth_header(token))
    assert resp.status_code == 200, resp.text
    detail = resp.json()["details"][0]
    assert detail["sufficient"] is False and detail["sample_size_unit"] == "frames"
    assert (detail["video_count"], detail["athlete_count"]) == (1, 1)
