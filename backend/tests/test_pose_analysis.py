"""Cleaning + quality layer: does the engine survive realistic recording problems?"""

import numpy as np
import pytest

from app.modules.pose.analysis import build_track, clean_track, frames_for_metrics, jitter_deg, _angle_series
from app.modules.pose.processing import analyze_frames, compute_biomechanics
from app.modules.biomechanics.registry import get_calculator
from tests.synth import (
    drop_frames, occlude_leg, roll_camera, run_frames, spike, squat_frames, strip_visibility,
)


def _knee(metrics, side):
    return np.array([m["value"] for m in metrics if m["name"] == f"knee_flexion_angle_{side}"])


def _codes(analysis):
    return {w["code"] for w in analysis["quality"]["warnings"]}


# ------------------------------ ground-truth recovery -----------------------------------

def test_clean_pipeline_recovers_true_knee_flexion():
    metrics, analysis = analyze_frames(squat_frames(depth=100), "squatting", "sagittal", 30)
    for side in ("left", "right"):
        k = _knee(metrics, side)
        assert np.percentile(k, 95) == pytest.approx(100, abs=3)
        assert np.percentile(k, 5) < 6
    assert analysis["quality"]["grade"] == "good"
    assert analysis["movement"]["reps"]["n_reps"] == 5


def test_noisy_landmarks_still_give_a_usable_peak():
    """2 cm landmark noise (realistic pose-model jitter) must not wreck the peak."""
    metrics, analysis = analyze_frames(squat_frames(depth=100, noise_m=0.02, seed=3), "squatting", "sagittal", 30)
    assert np.percentile(_knee(metrics, "left"), 95) == pytest.approx(100, abs=7)
    assert analysis["movement"]["reps"]["n_reps"] == 5  # reps still counted through the noise


def test_smoothing_reduces_noise_versus_raw():
    frames = squat_frames(depth=100, noise_m=0.02, seed=5)
    raw = compute_biomechanics(
        [{**f, "world_landmarks": f["world_landmarks"]} for f in frames], get_calculator("squatting"), "sagittal")
    cleaned, _ = analyze_frames(frames, "squatting", "sagittal", 30)
    jr = jitter_deg(_knee(raw, "left"))
    jc = jitter_deg(_knee(cleaned, "left"))
    assert jc < jr * 0.8


def test_single_frame_landmark_spike_does_not_define_the_peak():
    frames = spike(squat_frames(depth=100), 40, "left_knee", metres=0.6)
    metrics, _ = analyze_frames(frames, "squatting", "sagittal", 30)
    assert np.percentile(_knee(metrics, "left"), 95) == pytest.approx(100, abs=4)
    assert _knee(metrics, "left").max() < 115  # without despiking the spike frame reads far off


def test_running_peaks_survive_smoothing():
    """Smoothing must not flatten fast movement: cutoff is per-movement."""
    metrics, _ = analyze_frames(run_frames(kmax=80, seconds=6), "running", "sagittal", 30)
    assert np.percentile(_knee(metrics, "left"), 95) > 80 * 0.9


# ------------------------------ occlusion / visibility ----------------------------------

def test_occluded_leg_is_dropped_not_measured():
    frames = occlude_leg(squat_frames(depth=100), "right", frac=1.0)
    metrics, analysis = analyze_frames(frames, "squatting", "sagittal", 30)
    assert len(_knee(metrics, "right")) == 0, "hallucinated landmarks were stored as measurements"
    assert np.percentile(_knee(metrics, "left"), 95) == pytest.approx(100, abs=3)  # visible leg unaffected
    assert "right_leg_poorly_visible" in _codes(analysis)
    assert analysis["quality"]["grade"] != "good"


def test_partially_occluded_leg_keeps_only_visible_frames():
    frames = occlude_leg(squat_frames(depth=100), "right", frac=0.3)
    metrics, analysis = analyze_frames(frames, "squatting", "sagittal", 30)
    n_total = len(frames)
    n_right = len(_knee(metrics, "right"))
    assert 0.55 * n_total < n_right < 0.8 * n_total
    # the surviving right-leg values are real, not garbage
    assert np.percentile(_knee(metrics, "right"), 95) == pytest.approx(100, abs=4)


def test_legacy_video_without_visibility_is_flagged_not_silently_trusted():
    _, analysis = analyze_frames(strip_visibility(squat_frames()), "squatting", "sagittal", 30)
    assert "visibility_unavailable" in _codes(analysis)


# ------------------------------ dropped frames ------------------------------------------

def test_dropped_frames_are_bridged_and_reps_still_counted():
    frames = drop_frames(squat_frames(n_reps=5), every=9)
    metrics, analysis = analyze_frames(frames, "squatting", "sagittal", 30)
    assert analysis["movement"]["reps"]["n_reps"] == 5
    assert np.percentile(_knee(metrics, "left"), 95) == pytest.approx(100, abs=4)
    # metrics are emitted only for frames the model actually saw
    assert len(_knee(metrics, "left")) == len(frames)


def test_long_dropout_is_not_interpolated_into_metrics():
    frames = drop_frames(squat_frames(n_reps=5), ranges=[(60, 120)])  # 2 s outage
    metrics, analysis = analyze_frames(frames, "squatting", "sagittal", 30)
    assert len(_knee(metrics, "left")) == len(frames)
    assert analysis["quality"]["frames"]["longest_gap_s"] >= 1.9


def test_slow_motion_stride_grid_is_handled():
    """Frames kept every 2nd (stride=2 on 60 fps footage): effective fps halves, results unchanged."""
    full = squat_frames(n_reps=5, fps=60, rep_s=2.0)
    strided = [f for f in full if f["frame_number"] % 2 == 0]
    metrics, analysis = analyze_frames(strided, "squatting", "sagittal", 60)
    assert analysis["quality"]["frames"]["effective_fps"] == pytest.approx(30, abs=1)
    assert analysis["movement"]["reps"]["n_reps"] == 5
    assert analysis["movement"]["reps"]["mean_rep_s"] == pytest.approx(2.0, abs=0.35)


# ------------------------------ camera conditions ---------------------------------------

def test_rolled_camera_is_detected():
    frames = roll_camera(squat_frames(), 15)
    _, analysis = analyze_frames(frames, "squatting", "sagittal", 30)
    assert analysis["quality"]["camera_tilt_deg"] == pytest.approx(15, abs=3)
    assert "camera_tilt_suspected" in _codes(analysis)


def test_level_camera_is_not_flagged():
    _, analysis = analyze_frames(squat_frames(), "squatting", "sagittal", 30)
    assert analysis["quality"]["camera_tilt_deg"] < 3
    assert "camera_tilt_suspected" not in _codes(analysis)


def test_frontal_view_reports_no_validated_metrics_with_guidance():
    metrics, analysis = analyze_frames(squat_frames(), "squatting", "frontal", 30)
    assert not [m for m in metrics if m["confidence"] == "validated"]
    assert "no_validated_metrics" in _codes(analysis)
    assert analysis["quality"]["grade"] == "poor"


def test_short_clip_is_flagged():
    _, analysis = analyze_frames(squat_frames(n_reps=1, rep_s=0.5, lead_s=0.1, tail_s=0.1), "squatting", "sagittal", 30)
    assert "short_clip" in _codes(analysis)


def test_no_pose_data_is_a_graded_report_not_a_crash():
    metrics, analysis = analyze_frames([], "squatting", "sagittal", 30)
    assert metrics == [] and analysis["quality"]["grade"] == "poor"


def test_all_analysis_output_is_json_serialisable():
    import json
    _, analysis = analyze_frames(run_frames(seconds=6), "running", "sagittal", 30)
    json.dumps(analysis)  # numpy types must not leak into JSONB


def test_every_movement_type_runs_end_to_end():
    for mv in ("squatting", "landing", "jumping", "throwing", "running", "sprinting", "cutting", "sport_specific"):
        frames = run_frames(seconds=5) if mv in ("running", "sprinting", "cutting") else squat_frames(n_reps=4)
        metrics, analysis = analyze_frames(frames, mv, "sagittal", 30)
        assert metrics, mv
        assert analysis["quality"]["grade"] in ("good", "fair", "poor"), mv
