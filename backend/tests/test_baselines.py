"""Baselines are computed over VIDEOS (one feature vector each), not pooled per-frame values.

Merged from two lines of work: the video-level baseline (sample_size counts videos), and the honesty
rules — an insufficient baseline stores NULL ("we don't know"), never a fabricated 0.0 +/- 0.0, and
"enough" means enough distinct VIDEOS *and* enough distinct ATHLETES.
"""

import numpy as np
import pytest
from sqlalchemy import select

from app.config import settings
from app.modules.risk_scoring.baselines import recompute_movement_baselines
from app.modules.risk_scoring.models import MovementBaseline
from app.modules.video.models import BiomechanicalMetric
from tests.conftest import register_and_login
from tests.factories import make_athlete, make_user, make_video
from tests.synth import squat_frames
from tests.test_risk_assessment_api import _athlete, _normal, _user, _video

FEATURE = "knee_flexion_angle_left.p95"


@pytest.mark.asyncio
async def test_sample_size_counts_videos_not_frames(client, db_session):
    await register_and_login(client, "c@t.com", "coach")
    coach = await _user(db_session, "c@t.com")
    ath = await _athlete(db_session, coach.id)
    for i in range(3):
        await _video(db_session, coach.id, ath.id, squat_frames(n_reps=3, depth=95 + 5 * i, seed=i))
    out = await recompute_movement_baselines(db_session, "squatting")
    assert out["videos"] == 3
    f = next(x for x in out["features"] if x["feature"] == FEATURE)
    assert f["sample_size"] == 3                            # not hundreds of frame rows
    assert f["sufficient"] is False and f["mean"] is None   # below the video floor: no pretend baseline
    rows = (await db_session.scalars(select(MovementBaseline))).all()
    assert rows and all(r.sample_size == 3 and r.video_count == 3 and r.athlete_count == 1 for r in rows)


@pytest.mark.asyncio
async def test_insufficient_baseline_stores_null_not_fabricated_zeros(client, db_session):
    """Regression: insufficient baselines used to be stored as 0.0 +/- 0.0 — a plausible, wrong number."""
    await register_and_login(client, "c@t.com", "coach")
    coach = await _user(db_session, "c@t.com")
    ath = await _athlete(db_session, coach.id)
    await _video(db_session, coach.id, ath.id, squat_frames(n_reps=3, seed=1))
    await recompute_movement_baselines(db_session, "squatting")
    rows = (await db_session.scalars(select(MovementBaseline))).all()
    assert rows and all(r.mean_value is None and r.std_dev is None for r in rows)


@pytest.mark.asyncio
async def test_many_videos_from_one_athlete_is_not_a_population(client, db_session):
    """Enough VIDEOS but one ATHLETE: that is a personal envelope, so the baseline stays unknown."""
    await register_and_login(client, "c@t.com", "coach")
    coach = await _user(db_session, "c@t.com")
    ath = await _athlete(db_session, coach.id)
    n = settings.min_baseline_videos
    for i in range(n):
        await _video(db_session, coach.id, ath.id, _normal(200 + i))
    out = await recompute_movement_baselines(db_session, "squatting")
    f = next(x for x in out["features"] if x["feature"] == FEATURE)
    assert f["sample_size"] == n and f["athletes"] == 1
    assert f["sufficient"] is False and f["mean"] is None


@pytest.mark.asyncio
async def test_sufficient_baseline_stores_real_mean_and_counts(client, db_session):
    await register_and_login(client, "c@t.com", "coach")
    coach = await _user(db_session, "c@t.com")
    people = [await _athlete(db_session, coach.id) for _ in range(settings.min_baseline_athletes)]
    n = settings.min_baseline_videos
    for i in range(n):
        await _video(db_session, coach.id, people[i % len(people)].id, _normal(300 + i))
    out = await recompute_movement_baselines(db_session, "squatting")
    f = next(x for x in out["features"] if x["feature"] == FEATURE)
    assert f["sufficient"] is True and f["mean"] is not None and f["std"] > 0
    row = await db_session.scalar(select(MovementBaseline).where(MovementBaseline.metric_name == FEATURE))
    assert (row.video_count, row.athlete_count) == (n, len(people))
    assert row.mean_value == pytest.approx(f["mean"], abs=0.01)


@pytest.mark.asyncio
async def test_recompute_replaces_previous_rows_and_ignores_other_movements(client, db_session):
    await register_and_login(client, "c@t.com", "coach")
    coach = await _user(db_session, "c@t.com")
    ath = await _athlete(db_session, coach.id)
    await _video(db_session, coach.id, ath.id, squat_frames(n_reps=3, seed=1))
    await recompute_movement_baselines(db_session, "squatting")
    n1 = len((await db_session.scalars(select(MovementBaseline))).all())
    await recompute_movement_baselines(db_session, "squatting")
    assert len((await db_session.scalars(select(MovementBaseline))).all()) == n1   # replaced, not appended
    assert (await recompute_movement_baselines(db_session, "running"))["videos"] == 0


@pytest.mark.asyncio
async def test_qualitative_confidence_tier_can_be_stored(db_session):
    """biomechanical_metrics.confidence was VARCHAR(10); 'qualitative' is 11 characters, so every
    frontal-view clip (knee valgus) died at INSERT."""
    coach = await make_user(db_session, "q@example.com")
    athlete = await make_athlete(db_session, coach.id)
    video = await make_video(db_session, athlete.id, coach.id, metrics={"knee_valgus_deviation_left": [4.2, 5.1]},
                             confidence="qualitative")
    stored = (await db_session.scalars(
        select(BiomechanicalMetric.confidence).where(BiomechanicalMetric.video_id == video.id))).all()
    assert set(stored) == {"qualitative"}
