"""Tests for athlete analysis history and rolling-baseline comparison.

These focus on the comparison engine's correctness and its guard rails: the
baseline must exclude the current analysis, must be scoped to the same activity
type, and must not fire alarms on a small sample or on a naturally noisy
athlete.
"""

import secrets
from datetime import datetime, timedelta

import pytest

from app.models.analysis_snapshot import AnalysisSnapshot
from app.models.athlete import Athlete
from app.models.biomechanical_analysis import BiomechanicalAnalysis
from app.models.pose_analysis import PoseAnalysis
from app.models.user import User
from app.models.video import Video, ProcessingStatus
from app.services import baseline_service as bs


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _athlete(db, user_id=None, public_id=None):
    a = Athlete(
        athlete_id=public_id or f"ATH{secrets.token_hex(4)}",
        user_id=user_id,
        sport_type="Basketball",
        age=24,
        height=180.0,
        weight=75.0,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _video(db, athlete, activity="squat", created_at=None):
    v = Video(
        athlete_id=athlete.id,
        uploaded_by=1,
        filename=f"{secrets.token_hex(8)}.mp4",
        original_filename="in.mp4",
        storage_path="uploads/in.mp4",
        activity_type=activity,
        processing_status=ProcessingStatus.COMPLETED,
        created_at=created_at or datetime.utcnow(),
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _risk(score, findings=0):
    return {
        "overall_risk_score": score,
        "risk_level": "low" if score < 30 else "moderate",
        "findings": [{"issue": f"f{i}"} for i in range(findings)],
    }


def _snap(db, athlete, activity, score, metrics=None, days_ago=0, findings=0):
    """Insert a snapshot directly, to build controlled histories."""
    video = _video(
        db, athlete, activity, created_at=datetime.utcnow() - timedelta(days=days_ago)
    )
    merged = {"risk_score": score, "findings_count": float(findings)}
    if metrics:
        merged.update(metrics)
    snap = AnalysisSnapshot(
        athlete_id=athlete.id,
        video_id=video.id,
        activity_type=activity,
        sequence_index=1,
        performed_at=video.created_at,
        overall_risk_score=score,
        risk_level="low",
        findings_count=findings,
        metrics=merged,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


# --------------------------------------------------------------------------- #
# Metric extraction
# --------------------------------------------------------------------------- #

def test_build_metrics_extracts_headline_numbers():
    bio = BiomechanicalAnalysis(
        pose_analysis_id=1,
        movement_quality={"score": 78.5, "components": {"symmetry": 88.0}},
        symmetry={"knee_asymmetry": {"max_asymmetry": 6.5, "mean_asymmetry": 3.0}},
        trunk_lean={"max": -12.0},
        rom={"knee_left": {"rom": 105.0}, "hip_right": {"rom": 60.0}},
    )
    metrics = bs.build_metrics(_risk(42.0, findings=3), bio, {"mean_confidence": 0.93})

    assert metrics["risk_score"] == 42.0
    assert metrics["findings_count"] == 3.0
    assert metrics["movement_quality"] == 78.5
    assert metrics["symmetry_score"] == 88.0
    assert metrics["knee_asymmetry"] == 6.5
    # Trunk lean is stored as a magnitude.
    assert metrics["trunk_lean_max"] == 12.0
    assert metrics["knee_rom_left"] == 105.0
    assert metrics["hip_rom_right"] == 60.0
    assert metrics["mean_pose_confidence"] == 0.93


def test_build_metrics_omits_missing_values():
    """A missing metric must be absent, never coerced to 0."""
    bio = BiomechanicalAnalysis(pose_analysis_id=1, movement_quality=None)
    metrics = bs.build_metrics(_risk(10.0), bio, {})
    assert "movement_quality" not in metrics
    assert "knee_asymmetry" not in metrics
    assert metrics["risk_score"] == 10.0


# --------------------------------------------------------------------------- #
# Baseline construction
# --------------------------------------------------------------------------- #

def test_baseline_uses_prior_analyses_excluding_current(db):
    athlete = _athlete(db)
    for i, score in enumerate([10.0, 20.0, 30.0]):
        _snap(db, athlete, "squat", score, days_ago=10 - i)

    # An unrealistically high current video must not pollute its own baseline.
    current = _video(db, athlete, "squat")
    baseline = bs.compute_baseline(
        db, athlete.id, "squat", exclude_video_id=current.id
    )
    assert baseline["risk_score"]["count"] == 3
    assert baseline["risk_score"]["mean"] == pytest.approx(20.0)


def test_baseline_is_scoped_to_activity(db):
    athlete = _athlete(db)
    _snap(db, athlete, "squat", 10.0, days_ago=3)
    _snap(db, athlete, "squat", 20.0, days_ago=2)
    _snap(db, athlete, "running", 90.0, days_ago=1)

    squat_baseline = bs.compute_baseline(db, athlete.id, "squat")
    running_baseline = bs.compute_baseline(db, athlete.id, "running")

    assert squat_baseline["risk_score"]["mean"] == pytest.approx(15.0)
    assert running_baseline["risk_score"]["mean"] == pytest.approx(90.0)


def test_baseline_window_is_limited_to_recent(db):
    athlete = _athlete(db)
    # Older sessions are deliberately extreme; they must fall outside the window.
    _snap(db, athlete, "squat", 100.0, days_ago=20)
    for i in range(bs.BASELINE_WINDOW):
        _snap(db, athlete, "squat", 10.0, days_ago=10 - i)

    baseline = bs.compute_baseline(db, athlete.id, "squat")
    assert baseline["risk_score"]["count"] == bs.BASELINE_WINDOW
    assert baseline["risk_score"]["mean"] == pytest.approx(10.0)


# --------------------------------------------------------------------------- #
# Comparison semantics
# --------------------------------------------------------------------------- #

def test_first_analysis_reports_no_history():
    result = bs.compare_to_baseline({"risk_score": 30.0}, {})
    assert result["status"] == "no_history"
    assert result["baseline_size"] == 0


def test_insufficient_history_below_threshold(db):
    athlete = _athlete(db)
    _snap(db, athlete, "squat", 20.0, days_ago=1)

    baseline = bs.compute_baseline(db, athlete.id, "squat")
    result = bs.compare_to_baseline({"risk_score": 25.0}, baseline)
    assert result["status"] == "insufficient_history"


def test_stable_when_change_is_within_noise(db):
    athlete = _athlete(db)
    for score in [20.0, 21.0, 19.0, 20.5]:
        _snap(db, athlete, "squat", score, days_ago=10)

    baseline = bs.compute_baseline(db, athlete.id, "squat")
    result = bs.compare_to_baseline({"risk_score": 20.2}, baseline)
    assert result["status"] == "stable"
    assert result["flags"] == []


def test_rising_risk_is_flagged_as_deterioration(db):
    athlete = _athlete(db)
    for score in [20.0, 21.0, 19.0, 20.0, 20.5]:
        _snap(db, athlete, "squat", score, days_ago=10)

    baseline = bs.compute_baseline(db, athlete.id, "squat")
    result = bs.compare_to_baseline({"risk_score": 65.0}, baseline)

    assert result["status"] == "changed"
    assert "risk_score" in result["deteriorations"]
    assert result["flags"][0]["verdict"] == "deterioration"


def test_falling_movement_quality_is_deterioration(db):
    """Direction matters: a LOWER quality score is worse."""
    athlete = _athlete(db)
    for q in [85.0, 84.0, 86.0, 85.5]:
        _snap(db, athlete, "squat", 20.0, metrics={"movement_quality": q}, days_ago=10)

    baseline = bs.compute_baseline(db, athlete.id, "squat")
    result = bs.compare_to_baseline(
        {"risk_score": 20.0, "movement_quality": 55.0}, baseline
    )
    assert "movement_quality" in result["deteriorations"]


def test_rising_movement_quality_is_improvement(db):
    athlete = _athlete(db)
    for q in [60.0, 61.0, 59.0, 60.5]:
        _snap(db, athlete, "squat", 20.0, metrics={"movement_quality": q}, days_ago=10)

    baseline = bs.compute_baseline(db, athlete.id, "squat")
    result = bs.compare_to_baseline(
        {"risk_score": 20.0, "movement_quality": 90.0}, baseline
    )
    assert "movement_quality" in result["improvements"]


def test_flat_history_does_not_explode_z_scores(db):
    """A perfectly flat baseline must not make any delta look infinite."""
    athlete = _athlete(db)
    for _ in range(4):
        _snap(db, athlete, "squat", 20.0, days_ago=10)

    baseline = bs.compute_baseline(db, athlete.id, "squat")
    result = bs.compare_to_baseline({"risk_score": 20.001}, baseline)
    # A microscopic change stays stable thanks to the noise floor.
    assert result["status"] == "stable"


def test_noisy_athlete_needs_a_large_move_to_flag(db):
    """Large natural variation should not raise false alarms."""
    athlete = _athlete(db)
    for score in [10.0, 40.0, 15.0, 45.0, 20.0]:
        _snap(db, athlete, "squat", score, days_ago=10)

    baseline = bs.compute_baseline(db, athlete.id, "squat")
    modest = bs.compare_to_baseline({"risk_score": 30.0}, baseline)
    extreme = bs.compare_to_baseline({"risk_score": 95.0}, baseline)

    assert modest["flags"] == []
    assert extreme["status"] == "changed"


def test_informational_metrics_never_flagged(db):
    """ROM has no inherent good/bad direction, so it must not raise a flag."""
    athlete = _athlete(db)
    for rom in [100.0, 101.0, 99.0, 100.5]:
        _snap(db, athlete, "squat", 20.0, metrics={"knee_rom_left": rom}, days_ago=10)

    baseline = bs.compute_baseline(db, athlete.id, "squat")
    result = bs.compare_to_baseline(
        {"risk_score": 20.0, "knee_rom_left": 40.0}, baseline
    )
    assert "knee_rom_left" not in result["deteriorations"]
    assert "knee_rom_left" not in result["improvements"]
    # It is still reported as a delta, just not as a verdict.
    assert any(d["metric"] == "knee_rom_left" for d in result["deltas"])


# --------------------------------------------------------------------------- #
# Snapshot recording (integration with the pipeline)
# --------------------------------------------------------------------------- #

def test_record_snapshot_is_idempotent(db):
    athlete = _athlete(db)
    video = _video(db, athlete, "squat")
    pose = PoseAnalysis(
        video_id=video.id, pose_model="m", analysis_version="1.0",
        pose_quality={"mean_confidence": 0.9},
    )
    db.add(pose)
    db.commit()
    db.refresh(pose)

    first = bs.record_snapshot(db, video, _risk(30.0), pose, None)
    second = bs.record_snapshot(db, video, _risk(99.0), pose, None)

    assert first is not None
    assert second.id == first.id
    # The original result must not be overwritten by a later call.
    assert second.overall_risk_score == 30.0
    assert db.query(AnalysisSnapshot).filter(
        AnalysisSnapshot.video_id == video.id
    ).count() == 1


def test_record_snapshot_assigns_sequence_and_compares(db):
    athlete = _athlete(db)
    for score, days in [(20.0, 10), (22.0, 8), (21.0, 6)]:
        _snap(db, athlete, "squat", score, days_ago=days)

    video = _video(db, athlete, "squat")
    pose = PoseAnalysis(
        video_id=video.id, pose_model="m", analysis_version="1.0",
        pose_quality={"mean_confidence": 0.9},
    )
    db.add(pose)
    db.commit()
    db.refresh(pose)

    snap = bs.record_snapshot(db, video, _risk(70.0), pose, None)
    assert snap is not None
    assert snap.sequence_index == 2  # the three seeded rows all used index 1
    assert snap.overall_risk_score == 70.0
    # The comparison is persisted, not recomputed on read.
    assert snap.baseline_comparison["status"] == "changed"
    assert "risk_score" in snap.baseline_comparison["deteriorations"]


def test_record_snapshot_skips_without_risk_score(db):
    athlete = _athlete(db)
    video = _video(db, athlete, "squat")
    assert bs.record_snapshot(db, video, {"findings": []}, None, None) is None


# --------------------------------------------------------------------------- #
# Trends
# --------------------------------------------------------------------------- #

def test_comparison_includes_baseline_metrics(db):
    """The baseline reference values are always present, even pre-comparison."""
    athlete = _athlete(db)
    for score in [20.0, 22.0, 24.0]:
        _snap(db, athlete, "squat", score, days_ago=5)

    baseline = bs.compute_baseline(db, athlete.id, "squat")
    result = bs.compare_to_baseline({"risk_score": 23.0}, baseline)

    metrics = {m["metric"]: m for m in result["baseline_metrics"]}
    assert "risk_score" in metrics
    assert metrics["risk_score"]["mean"] == pytest.approx(22.0)
    assert metrics["risk_score"]["samples"] == 3


def test_baseline_metrics_empty_without_history():
    result = bs.compare_to_baseline({"risk_score": 10.0}, {})
    assert result["baseline_metrics"] == []
    # These keys must always exist so the client never has to null-check.
    assert result["deteriorations"] == []
    assert result["improvements"] == []
    assert result["baseline_window"] == bs.BASELINE_WINDOW


def test_snapshot_stores_baseline(db):
    """The baseline is persisted so it can be displayed later."""
    athlete = _athlete(db)
    for score in [20.0, 30.0]:
        _snap(db, athlete, "squat", score, days_ago=5)

    video = _video(db, athlete, "squat")
    pose = PoseAnalysis(
        video_id=video.id, pose_model="m", analysis_version="1.0",
        pose_quality={"mean_confidence": 0.9},
    )
    db.add(pose)
    db.commit()
    db.refresh(pose)

    snap = bs.record_snapshot(db, video, _risk(25.0), pose, None)
    assert snap.baseline is not None
    assert snap.baseline["risk_score"]["mean"] == pytest.approx(25.0)


def test_summarize_trends_detects_worsening(db):
    athlete = _athlete(db)
    for i, score in enumerate([10.0, 12.0, 40.0, 45.0]):
        _snap(db, athlete, "squat", score, days_ago=10 - i)

    rows = bs.get_athlete_history(db, athlete.id)
    trends = bs.summarize_trends(rows)

    assert len(trends) == 1
    assert trends[0]["direction"] == "worsening"
    assert trends[0]["analysis_count"] == 4
    assert trends[0]["latest_risk_score"] == 45.0


def test_summarize_trends_detects_improving(db):
    athlete = _athlete(db)
    for i, score in enumerate([60.0, 58.0, 20.0, 15.0]):
        _snap(db, athlete, "squat", score, days_ago=10 - i)

    trends = bs.summarize_trends(bs.get_athlete_history(db, athlete.id))
    assert trends[0]["direction"] == "improving"


def test_summarize_trends_separates_activities(db):
    athlete = _athlete(db)
    _snap(db, athlete, "squat", 20.0, days_ago=5)
    _snap(db, athlete, "squat", 22.0, days_ago=4)
    _snap(db, athlete, "running", 80.0, days_ago=3)

    trends = bs.summarize_trends(bs.get_athlete_history(db, athlete.id))
    by_activity = {t["activity_type"]: t for t in trends}
    assert set(by_activity) == {"squat", "running"}
    assert by_activity["squat"]["analysis_count"] == 2
    assert by_activity["running"]["analysis_count"] == 1
