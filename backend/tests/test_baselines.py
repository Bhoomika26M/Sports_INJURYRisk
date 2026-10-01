"""Baseline tests — leave-one-out (Defect 2), video/athlete sufficiency (Defect 3), NULL not zero (Defect 4)."""

import inspect

import numpy as np
import pytest
from sqlalchemy import delete, select

from app.modules.risk_scoring.anomaly import compute_anomaly_scores
from app.modules.risk_scoring.baselines import (
    BaselineCoverage,
    fetch_baseline,
    find_shortfall,
    recompute_baseline,
    summarize_rows,
)
from app.modules.risk_scoring.constants import MIN_BASELINE_ATHLETES, MIN_BASELINE_FRAMES, MIN_BASELINE_VIDEOS
from app.modules.risk_scoring.models import MovementBaseline
from app.modules.video.models import BiomechanicalMetric, VideoProcessingStatus
from tests.factories import make_athlete, make_population, make_user, make_video, normal_frames

METRIC = "knee_flexion_angle_left"


# ---- pure: non-finite handling and coverage counting ---------------------------------------

def test_summarize_rows_drops_non_finite_before_counting():
    rows = [(90.0, "v1", "a1"), (91.0, "v1", "a1"), (float("nan"), "v2", "a2"), (float("inf"), "v2", "a2")]
    sample = summarize_rows(rows)
    assert sample.dropped_non_finite == 2
    assert sample.coverage == BaselineCoverage(videos=1, athletes=1, frames=2)   # v2 had only junk


def test_find_shortfall_reports_first_unmet_unit_in_fixed_order():
    s = find_shortfall(METRIC, BaselineCoverage(videos=426, athletes=1, frames=426))
    assert (s.unit, s.have, s.need) == ("athletes", 1, MIN_BASELINE_ATHLETES)   # many videos, one person
    s = find_shortfall(METRIC, BaselineCoverage(videos=1, athletes=1, frames=426))
    assert (s.unit, s.have, s.need) == ("videos", 1, MIN_BASELINE_VIDEOS)
    s = find_shortfall(METRIC, BaselineCoverage(videos=MIN_BASELINE_VIDEOS, athletes=2, frames=5000))
    assert (s.unit, s.have, s.need) == ("athletes", 2, MIN_BASELINE_ATHLETES)
    s = find_shortfall(METRIC, BaselineCoverage(videos=6, athletes=3, frames=40))
    assert (s.unit, s.have, s.need) == ("frames", 40, MIN_BASELINE_FRAMES)
    assert find_shortfall(METRIC, BaselineCoverage(videos=6, athletes=3, frames=900)) is None


def test_exclude_video_id_is_a_required_keyword_with_no_default():
    """Structural, not a caller-side `if`: forgetting the argument is a TypeError."""
    param = inspect.signature(fetch_baseline).parameters["exclude_video_id"]
    assert param.kind is inspect.Parameter.KEYWORD_ONLY
    assert param.default is inspect.Parameter.empty


# ---- Defect 2: a video is never part of its own baseline -----------------------------------

@pytest.mark.asyncio
async def test_baseline_excludes_the_video_under_evaluation(db_session):
    _, _, videos = await make_population(db_session, videos=6, athletes=3)
    target = videos[0]
    with_exclusion = await fetch_baseline(db_session, "squatting", METRIC, exclude_video_id=target.id)
    everything = await fetch_baseline(db_session, "squatting", METRIC, exclude_video_id=None)
    assert with_exclusion.coverage.videos == 5 and everything.coverage.videos == 6
    assert with_exclusion.coverage.frames == everything.coverage.frames - 150


@pytest.mark.asyncio
async def test_anomaly_scores_identical_whether_or_not_the_video_own_rows_exist(db_session):
    """Scoring video X must not depend on X's own rows being in the baseline table."""
    coach, _, videos = await make_population(db_session, videos=6, athletes=3, seed=1)
    target = videos[0]
    rng = np.random.default_rng(99)
    # Make X's own frames clearly deviant, so any self-inclusion would visibly damp its score.
    deviant = [float(v) for v in rng.normal(90 + 6 * 8, 8, size=150)]
    await db_session.execute(delete(BiomechanicalMetric).where(BiomechanicalMetric.video_id == target.id))
    await db_session.commit()
    base_with_x_rows_absent = await fetch_baseline(db_session, "squatting", METRIC, exclude_video_id=target.id)

    from sqlalchemy import insert
    await db_session.execute(insert(BiomechanicalMetric), [
        {"video_id": target.id, "frame_number": i, "metric_name": METRIC, "metric_value": round(v, 3),
         "plane": "sagittal", "confidence": "validated"} for i, v in enumerate(deviant)])
    await db_session.commit()
    base_with_x_rows_present = await fetch_baseline(db_session, "squatting", METRIC, exclude_video_id=target.id)

    assert np.array_equal(base_with_x_rows_absent.values, base_with_x_rows_present.values)
    sample = np.array(deviant).reshape(-1, 1)
    a = compute_anomaly_scores(sample, base_with_x_rows_absent.values.reshape(-1, 1))
    b = compute_anomaly_scores(sample, base_with_x_rows_present.values.reshape(-1, 1))
    assert a == b

    # Sensitivity check: the naive, self-including baseline really does damp the deviation.
    leaky = fetch_baseline(db_session, "squatting", METRIC, exclude_video_id=None)
    leaky = (await leaky).values.reshape(-1, 1)
    assert np.mean(compute_anomaly_scores(sample, leaky)) < np.mean(a)


@pytest.mark.asyncio
async def test_baseline_order_is_deterministic(db_session):
    _, _, videos = await make_population(db_session, videos=5, athletes=3, seed=2)
    first = await fetch_baseline(db_session, "squatting", METRIC, exclude_video_id=videos[0].id)
    second = await fetch_baseline(db_session, "squatting", METRIC, exclude_video_id=videos[0].id)
    assert np.array_equal(first.values, second.values)


@pytest.mark.asyncio
async def test_baseline_only_counts_completed_validated_videos_of_the_same_movement(db_session):
    coach, people, _ = await make_population(db_session, videos=5, athletes=3, seed=3)
    rng = np.random.default_rng(3)
    await make_video(db_session, people[0].id, coach.id, "squatting", VideoProcessingStatus.failed,
                     {METRIC: normal_frames(rng, 100)})
    await make_video(db_session, people[0].id, coach.id, "squatting", VideoProcessingStatus.processing,
                     {METRIC: normal_frames(rng, 100)})
    await make_video(db_session, people[0].id, coach.id, "running", VideoProcessingStatus.completed,
                     {METRIC: normal_frames(rng, 100)})
    await make_video(db_session, people[0].id, coach.id, "squatting", VideoProcessingStatus.completed,
                     {METRIC: normal_frames(rng, 100)}, confidence="qualitative")
    sample = await fetch_baseline(db_session, "squatting", METRIC, exclude_video_id=None)
    assert sample.coverage.videos == 5 and sample.coverage.athletes == 3


# ---- the confidence column must hold 'qualitative' -----------------------------------------

@pytest.mark.asyncio
async def test_qualitative_confidence_tier_can_be_stored(db_session):
    """biomechanical_metrics.confidence was VARCHAR(10); 'qualitative' is 11 characters."""
    coach = await make_user(db_session, "q@example.com")
    athlete = await make_athlete(db_session, coach.id)
    video = await make_video(db_session, athlete.id, coach.id, metrics={"knee_valgus_deviation_left": [4.2, 5.1]},
                             confidence="qualitative")
    stored = (await db_session.scalars(select(BiomechanicalMetric.confidence).where(BiomechanicalMetric.video_id == video.id))).all()
    assert set(stored) == {"qualitative"}


# ---- Defects 3 and 4: stored baseline ------------------------------------------------------

@pytest.mark.asyncio
async def test_one_video_of_one_athlete_is_insufficient_however_many_frames(db_session):
    """The real squat clip made 426 rows per metric: one video, one person. Must NOT count as enough."""
    coach = await make_user(db_session, "solo@example.com")
    athlete = await make_athlete(db_session, coach.id)
    rng = np.random.default_rng(0)
    await make_video(db_session, athlete.id, coach.id, metrics={METRIC: normal_frames(rng, 426)})

    result = await recompute_baseline(db_session, "squatting", METRIC)
    assert result["sufficient"] is False
    assert result["sample_size"] == 426 and result["sample_size_unit"] == "frames"
    assert (result["video_count"], result["athlete_count"]) == (1, 1)
    assert result["unmet"] == {"unit": "videos", "have": 1, "need": MIN_BASELINE_VIDEOS}


@pytest.mark.asyncio
async def test_insufficient_baseline_stores_null_not_fabricated_zeros(db_session):
    coach = await make_user(db_session, "null@example.com")
    athlete = await make_athlete(db_session, coach.id)
    await make_video(db_session, athlete.id, coach.id, metrics={METRIC: normal_frames(np.random.default_rng(0), 200)})
    await recompute_baseline(db_session, "squatting", METRIC)

    row = await db_session.scalar(select(MovementBaseline).where(
        MovementBaseline.movement_type == "squatting", MovementBaseline.metric_name == METRIC))
    assert row.mean_value is None and row.std_dev is None
    assert (row.sample_size, row.video_count, row.athlete_count) == (200, 1, 1)


@pytest.mark.asyncio
async def test_sufficient_baseline_stores_real_mean_and_std(db_session):
    await make_population(db_session, videos=MIN_BASELINE_VIDEOS, athletes=MIN_BASELINE_ATHLETES, frames=200, seed=4)
    result = await recompute_baseline(db_session, "squatting", METRIC)
    assert result["sufficient"] is True and result["unmet"] is None
    row = await db_session.scalar(select(MovementBaseline).where(MovementBaseline.metric_name == METRIC))
    assert row.mean_value == pytest.approx(90.0, abs=2.0) and row.std_dev == pytest.approx(8.0, abs=1.5)
    assert (row.video_count, row.athlete_count) == (MIN_BASELINE_VIDEOS, MIN_BASELINE_ATHLETES)


@pytest.mark.asyncio
async def test_recompute_drops_non_finite_values(db_session):
    coach = await make_user(db_session, "nan@example.com")
    athlete = await make_athlete(db_session, coach.id)
    await make_video(db_session, athlete.id, coach.id, metrics={METRIC: [90.0, 91.0, float("nan"), 89.5]})
    result = await recompute_baseline(db_session, "squatting", METRIC)
    assert result["dropped_non_finite"] == 1 and result["sample_size"] == 3
