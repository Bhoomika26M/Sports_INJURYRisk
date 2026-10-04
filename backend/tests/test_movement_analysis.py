"""Movement-specific analysis against synthetic motion with known ground truth."""

import numpy as np
import pytest

from app.modules.biomechanics.movement_analysis import (
    analyze_gait, analyze_movement, analyze_reps, detect_reps, detect_reps_detailed, movement_dynamics,
)
from app.modules.pose.analysis import build_track, clean_track
from tests.synth import run_frames, squat_frames


def _xyz(frames, movement):
    t = build_track(frames, 30)
    return clean_track(t, movement), t


def _knee_series(frames):
    from app.modules.biomechanics.calculations import knee_flexion_angle
    kl = np.array([knee_flexion_angle(f["world_landmarks"], "left") for f in frames])
    kr = np.array([knee_flexion_angle(f["world_landmarks"], "right") for f in frames])
    return {"knee_flexion_angle_left": kl, "knee_flexion_angle_right": kr}


def test_detect_reps_counts_squats_and_recovers_depth():
    series = _knee_series(squat_frames(n_reps=5, depth=100))
    sig = (series["knee_flexion_angle_left"] + series["knee_flexion_angle_right"]) / 2
    peaks = detect_reps(sig)
    assert len(peaks) == 5
    assert all(abs(p - 100) < 4 for p in peaks)


def test_detect_reps_tempo_matches_rep_duration():
    series = _knee_series(squat_frames(n_reps=4, rep_s=2.5, fps=30))
    out = analyze_reps(series, "squatting", 30.0)
    assert out["n_reps"] == 4
    assert out["mean_rep_s"] == pytest.approx(2.5, abs=0.4)
    # symmetric cosine rep: descent ~ ascent
    assert out["mean_descent_s"] == pytest.approx(out["mean_ascent_s"], abs=0.35)


def test_no_reps_when_movement_range_is_within_tracking_noise():
    rng = np.random.default_rng(0)
    flat = 10 + rng.normal(0, 1.5, 300)
    assert detect_reps(flat) == []
    assert detect_reps_detailed(np.array([5.0] * 10)) == []  # too short


def test_drift_detects_set_degradation_and_reports_direction():
    series = _knee_series(squat_frames(n_reps=6, depth=100, depth_drift=-0.30))
    out = analyze_reps(series, "squatting", 30.0)
    assert out["n_reps"] == 6
    assert -40 < out["drift_pct"] < -15
    assert out["drift_direction"] == "decrease"


def test_steady_set_has_negligible_drift_and_low_variability():
    out = movement_dynamics([100, 99, 101, 100, 100, 99])
    assert abs(out["drift_pct"]) < 2 and out["cv_pct"] < 2


def test_drift_needs_four_reps():
    assert "drift_pct" not in movement_dynamics([100, 80, 60])
    assert "cv_pct" in movement_dynamics([100, 80, 60])


@pytest.mark.parametrize("cadence", [150, 170, 200])
def test_gait_cadence_recovered(cadence):
    xyz, t = _xyz(run_frames(cadence_spm=cadence, seconds=6), "running")
    g = analyze_gait(xyz, t.fps_eff)
    assert g is not None
    assert g["cadence_spm"] == pytest.approx(cadence, rel=0.06)
    assert g["step_time_asymmetry_pct"] < 6  # symmetric gait


def test_gait_step_time_asymmetry_detected():
    xyz, t = _xyz(run_frames(cadence_spm=170, asym=0.10, seconds=8), "running")
    g = analyze_gait(xyz, t.fps_eff)
    assert g["step_time_asymmetry_pct"] > 12  # true value ~20%


def test_gait_not_found_in_a_squat():
    xyz, t = _xyz(squat_frames(), "squatting")
    assert analyze_gait(xyz, t.fps_eff) is None


def test_gait_is_oblique_view_safe_via_pca_axis():
    """Camera at an angle: travel axis is a mix of x and z. PCA must still find the cadence."""
    from tests.synth import make_pose  # noqa: F401
    frames = run_frames(cadence_spm=170, seconds=6)
    r = np.radians(40)
    R = np.array([[np.cos(r), 0, np.sin(r)], [0, 1, 0], [-np.sin(r), 0, np.cos(r)]])  # yaw 40 deg
    rotated = [{**f, "world_landmarks": {k: (R @ np.array(v)).tolist() for k, v in f["world_landmarks"].items()}} for f in frames]
    xyz, t = _xyz(rotated, "running")
    g = analyze_gait(xyz, t.fps_eff)
    assert g and g["cadence_spm"] == pytest.approx(170, rel=0.07)


def test_label_mismatch_running_clip_labelled_squat():
    xyz, t = _xyz(run_frames(seconds=6), "squatting")
    out = analyze_movement("squatting", "sagittal", _knee_series(run_frames(seconds=6)), xyz, t.fps_eff)
    assert any(w["code"] == "movement_type_mismatch_suspected" for w in out["warnings"])


def test_squat_clip_labelled_running_warns_no_stride():
    fr = squat_frames()
    xyz, t = _xyz(fr, "running")
    out = analyze_movement("running", "sagittal", _knee_series(fr), xyz, t.fps_eff)
    assert any(w["code"] == "no_stride_pattern_detected" for w in out["warnings"])


def test_frontal_running_does_not_fabricate_step_timing():
    fr = run_frames(seconds=6)
    xyz, t = _xyz(fr, "running")
    out = analyze_movement("running", "frontal", _knee_series(fr), xyz, t.fps_eff)
    assert out["gait"] is None
    assert any(w["code"] == "gait_timing_needs_side_view" for w in out["warnings"])


def test_squat_with_no_reps_warns():
    out = analyze_movement("squatting", "sagittal", {"knee_flexion_angle_left": np.full(100, 8.0)}, None, 30.0)
    assert any(w["code"] == "no_repetitions_detected" for w in out["warnings"])
