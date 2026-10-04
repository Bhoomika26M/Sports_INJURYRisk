"""Risk scoring tests — validation, RBAC, breakdown transparency."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, register_and_login


def test_risk_score_breakdown_is_transparent_and_weighted_per_spec():
    from app.modules.risk_scoring.scoring import Component, WEIGHTS, combine

    comps = [Component(k, v, {"why": k}) for k, v in zip(WEIGHTS, [80.0, 100.0, 50.0, 70.0, 30.0])]
    result = combine(comps)
    bd = result["score_breakdown"]
    expected = 0.35 * 80 + 0.20 * 100 + 0.20 * 50 + 0.15 * 70 + 0.10 * 30
    assert result["overall_score"] == round(expected, 1)
    assert bd["biomechanical_deviations"]["points"] == round(0.35 * 80, 1)
    assert bd["movement_asymmetry"]["max"] == 20.0
    assert all(c["detail"] for c in bd.values())
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


def test_recommendations_trace_to_breakdown():
    from app.modules.recommendations.rules import generate_recommendations
    from app.modules.risk_scoring.scoring import WEIGHTS

    bd = {k: {"available": False, "score": None, "detail": {}} for k in WEIGHTS}
    bd["movement_asymmetry"] = {"available": True, "score": 90.0, "detail": {"left_peak_deg": 100, "right_peak_deg": 65, "lsi_pct": 65}}
    bd["historical_injury_factors"] = {"available": True, "score": 100.0, "detail": {"injuries": [{"body_part": "knee", "status": "unresolved"}]}}
    recs = generate_recommendations({"overall_score": 60, "score_breakdown": bd, "anomaly_features": [], "injury_categories": {}}, "squatting")
    titles = {r["title"] for r in recs}
    assert "Address left/right asymmetry" in titles
    assert any("physiotherapist" in t.lower() for t in titles)
    assert all(1 <= r["priority"] <= 5 for r in recs)


# ---- The 202 gate counts VIDEOS and ATHLETES, never frame rows ---------------------------------

import numpy as np  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.config import settings  # noqa: E402
from app.modules.risk_scoring.models import MovementBaseline  # noqa: E402
from tests.factories import make_athlete, make_population, make_user, make_video, normal_frames  # noqa: E402

MIN_V, MIN_A = settings.min_baseline_videos, settings.min_baseline_athletes
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
    assert body["need"] == MIN_V
    assert body["coverage"] == {"videos": {"have": 0, "need": MIN_V}, "athletes": {"have": 0, "need": MIN_A}}
    assert "never counted in its own baseline" in body["message"]


@pytest.mark.asyncio
async def test_one_video_short_of_the_floor_is_still_202_because_the_video_does_not_count_itself(client, db_session):
    token = await register_and_login(client, "admin@gate2.example.com", "admin")
    _, _, videos = await make_population(db_session, videos=MIN_V, athletes=MIN_A, seed=5)
    resp = await _score(client, videos[0].id, token)   # MIN_V videos exist, but only MIN_V-1 OTHER ones
    assert resp.status_code == 202
    assert (resp.json()["unit"], resp.json()["have"], resp.json()["need"]) == ("videos", MIN_V - 1, MIN_V)


@pytest.mark.asyncio
async def test_many_videos_from_too_few_athletes_is_202_on_athletes(client, db_session):
    """Ten clips of one or two athletes are a personal envelope, not a population."""
    token = await register_and_login(client, "admin@gate3.example.com", "admin")
    _, _, videos = await make_population(db_session, videos=MIN_V + 3, athletes=MIN_A - 1, seed=6)
    resp = await _score(client, videos[0].id, token)
    body = resp.json()
    assert resp.status_code == 202 and body["unit"] == "athletes"
    assert (body["have"], body["need"]) == (MIN_A - 1, MIN_A)
    assert body["coverage"]["videos"]["have"] >= MIN_V   # videos were fine; athletes were not


@pytest.mark.asyncio
async def test_caveated_videos_do_not_count_toward_the_athlete_or_video_floor(client, db_session):
    """A multi-person / partial-coverage clip must not help a baseline reach its floor."""
    token = await register_and_login(client, "admin@gate9.example.com", "admin")
    _, _, videos = await make_population(db_session, videos=MIN_V + 2, athletes=MIN_A, seed=11)
    for v in videos[1:4]:
        v.coverage_caveat = "Partial coverage: ..."
    await db_session.commit()
    resp = await _score(client, videos[0].id, token)
    body = resp.json()
    assert resp.status_code == 202 and body["unit"] == "videos"
    assert body["have"] == MIN_V + 1 - 3        # everything but itself, minus the three caveated clips


@pytest.mark.asyncio
async def test_real_population_scores_and_a_normal_athlete_is_low_not_moderate(client, db_session):
    token = await register_and_login(client, "admin@gate4.example.com", "admin")
    coach, people, _ = await make_population(db_session, videos=MIN_V, athletes=MIN_A, frames=200, seed=7)
    rng = np.random.default_rng(70)
    subject = await make_video(db_session, people[0].id, coach.id, metrics={m: normal_frames(rng, 200) for m in METRICS})

    resp = await _score(client, subject.id, token)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    dev = body["score_breakdown"]["biomechanical_deviations"]
    assert dev["score"] < 5.0          # was ~37 of 70 for a perfectly normal athlete
    assert body["risk_category"] == "low" and body["overall_score"] < 10
    assert body["baseline"]["videos"] == MIN_V and body["baseline"]["athletes"] >= MIN_A
    assert body["baseline"]["provisional"] is True   # 10 baseline videos is under the 30-video "established" mark
    assert body["data_quality"] == {"detection_rate": None, "person_count_detected": None, "caveat": None}


@pytest.mark.asyncio
async def test_clearly_deviant_athlete_scores_far_above_a_normal_one_against_the_same_population(client, db_session):
    token = await register_and_login(client, "admin@gate5.example.com", "admin")
    coach, people, _ = await make_population(db_session, videos=MIN_V, athletes=MIN_A, frames=200, seed=8)
    rng = np.random.default_rng(80)
    normal = await make_video(db_session, people[0].id, coach.id, metrics={m: normal_frames(rng, 200) for m in METRICS})
    deviant = await make_video(db_session, people[0].id, coach.id,
                               metrics={m: normal_frames(rng, 200, mu=90 + 8 * 8) for m in METRICS})
    n = (await _score(client, normal.id, token)).json()
    d_resp = await _score(client, deviant.id, token)
    d = d_resp.json()
    assert d_resp.status_code == 200
    assert d["score_breakdown"]["biomechanical_deviations"]["score"] == 100.0
    # one maxed component alongside clean asymmetry/history is a "moderate" composite, never "low"
    assert d["risk_category"] in ("moderate", "high") and d["overall_score"] >= 40
    assert d["overall_score"] - n["overall_score"] >= 35


@pytest.mark.asyncio
async def test_score_is_unchanged_by_the_subject_own_rows_being_in_the_table(client, db_session):
    """Endpoint-level leakage check: the subject's own rows never feed its own baseline."""
    token = await register_and_login(client, "admin@gate6.example.com", "admin")
    coach, people, _ = await make_population(db_session, videos=MIN_V, athletes=MIN_A, frames=200, seed=9)
    rng = np.random.default_rng(90)
    subject = await make_video(db_session, people[0].id, coach.id,
                               metrics={m: normal_frames(rng, 200, mu=90 + 6 * 8) for m in METRICS})
    first = (await _score(client, subject.id, token)).json()["score_breakdown"]["biomechanical_deviations"]["score"]
    second = (await _score(client, subject.id, token, recompute=True)).json()["score_breakdown"]["biomechanical_deviations"]["score"]
    assert first == second and first > 30.0


@pytest.mark.asyncio
async def test_risk_score_forbidden_for_unrelated_athlete_user(client, db_session):
    _, _, videos = await make_population(db_session, videos=MIN_V, athletes=MIN_A, seed=10)
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
    detail = resp.json()["details"]
    assert (detail["videos"], detail["need"], detail["need_athletes"]) == (1, MIN_V, MIN_A)
    f = detail["features"][0]
    assert f["sufficient"] is False and f["mean"] is None and f["sample_size"] == 1 and f["athletes"] == 1
    rows = (await db_session.scalars(select(MovementBaseline))).all()
    assert rows and all(r.mean_value is None and r.std_dev is None for r in rows)   # unknown, not 0.0
    assert all((r.video_count, r.athlete_count) == (1, 1) for r in rows)
