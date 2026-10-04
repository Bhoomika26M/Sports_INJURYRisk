"""Database-level hardening: query edge cases the first e2e suite never exercised."""

import math
import uuid
from decimal import Decimal

import numpy as np
import pytest
from sqlalchemy import insert, select

from app.modules.recommendations.models import Recommendation
from app.modules.risk_scoring.features import fetch_all_video_features, fetch_baseline_features, fetch_video_features
from app.modules.risk_scoring.models import RiskScore
from app.modules.video.models import BiomechanicalMetric, VideoProcessingStatus
from tests.conftest import auth_header, register_and_login
from tests.synth import occlude_leg, squat_frames
from tests.test_risk_assessment_api import _athlete, _normal, _score, _setup, _user, _video


async def _ctx(client, db):
    await register_and_login(client, "c@t.com", "coach")
    coach = await _user(db, "c@t.com")
    return coach, await _athlete(db, coach.id)


@pytest.mark.asyncio
async def test_a_metric_with_too_few_frames_is_not_a_feature(client, db_session):
    coach, ath = await _ctx(client, db_session)
    v = await _video(db_session, coach.id, ath.id, squat_frames(n_reps=4))
    await db_session.execute(insert(BiomechanicalMetric), [
        {"video_id": v.id, "frame_number": i, "metric_name": "trunk_rotation", "metric_value": 30.0 + i,
         "plane": "transverse", "confidence": "validated"} for i in range(10)])           # only 10 frames (< 15)
    await db_session.commit()
    feats = await fetch_video_features(db_session, v.id)
    assert "trunk_rotation.p95" not in feats and "knee_flexion_angle_left.p95" in feats


@pytest.mark.asyncio
async def test_nan_metric_rows_cannot_poison_a_feature(client, db_session):
    coach, ath = await _ctx(client, db_session)
    v = await _video(db_session, coach.id, ath.id, squat_frames(n_reps=4))
    clean = (await fetch_video_features(db_session, v.id))["knee_flexion_angle_left.p95"]
    n = len(squat_frames(n_reps=4))
    # 25% NaN rows: Postgres sorts NaN above every number, so an unfiltered p95 would itself be NaN
    await db_session.execute(insert(BiomechanicalMetric), [
        {"video_id": v.id, "frame_number": 10_000 + i, "metric_name": "knee_flexion_angle_left",
         "metric_value": Decimal("NaN"), "plane": "sagittal", "confidence": "validated"} for i in range(n // 3)])
    await db_session.commit()
    poisoned = (await fetch_video_features(db_session, v.id))["knee_flexion_angle_left.p95"]
    assert math.isfinite(poisoned) and poisoned == pytest.approx(clean, abs=0.5)


@pytest.mark.asyncio
async def test_baseline_only_contains_complete_videos_and_counts_the_rest(client, db_session):
    coach, ath = await _ctx(client, db_session)
    for s in (1, 2):
        await _video(db_session, coach.id, ath.id, _normal(s))
    await _video(db_session, coach.id, ath.id, occlude_leg(_normal(3), "right"))        # lacks every right-leg feature
    target = await _video(db_session, coach.id, ath.id, _normal(4))
    required = sorted(await fetch_video_features(db_session, target.id))
    rows, dropped = await fetch_baseline_features(db_session, "squatting", target.id, required)
    assert len(rows) == 2 and dropped == 1
    assert all(set(r) == set(required) for r in rows)


@pytest.mark.asyncio
async def test_unfinished_and_failed_videos_never_enter_a_baseline(client, db_session):
    coach, ath = await _ctx(client, db_session)
    await _video(db_session, coach.id, ath.id, _normal(1))
    await _video(db_session, coach.id, ath.id, _normal(2), status=VideoProcessingStatus.failed)
    await _video(db_session, coach.id, ath.id, _normal(3), status=VideoProcessingStatus.processing)
    target = await _video(db_session, coach.id, ath.id, _normal(4))
    required = sorted(await fetch_video_features(db_session, target.id))
    rows, _ = await fetch_baseline_features(db_session, "squatting", target.id, required)
    assert len(rows) == 1
    assert len(await fetch_all_video_features(db_session, "squatting")) == 2           # completed ones only


@pytest.mark.asyncio
async def test_recomputing_never_changes_the_number_of_recommendations(client, db_session):
    token, coach, ath = await _setup(client, db_session)
    v = await _video(db_session, coach.id, ath.id, _normal(950))
    assert (await _score(client, token, v.id)).status_code == 200
    rs = await db_session.scalar(select(RiskScore))

    async def n_recs():
        return len((await db_session.scalars(select(Recommendation).where(Recommendation.risk_score_id == rs.id))).all())

    first = await n_recs()
    assert first >= 1
    for _ in range(2):
        assert (await _score(client, token, v.id, recompute="true")).status_code == 200
        assert await n_recs() == first                                                   # 3 x first would mean accumulation


@pytest.mark.asyncio
async def test_a_mostly_hidden_leg_makes_asymmetry_unavailable_through_the_api(client, db_session):
    """The leg is visible just often enough to yield features (so it IS comparable to the baseline) but
    not often enough for a left/right comparison to mean anything. The visibility report must reach the score."""
    token, coach, ath = await _setup(client, db_session)
    v = await _video(db_session, coach.id, ath.id, occlude_leg(_normal(960), "right", frac=0.7))
    r = await _score(client, token, v.id)
    assert r.status_code == 200, r.text
    j = r.json()
    asym = j["score_breakdown"]["movement_asymmetry"]
    assert asym["available"] is False and "not reliably visible" in asym["detail"]["reason"]
    assert j["quality"]["usable_pct"]["right_leg"] < 60 and j["quality"]["grade"] != "good"
    assert "movement_asymmetry" in j["missing_components"]
