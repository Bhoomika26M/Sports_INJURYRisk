"""Tests written AFTER a mutation campaign showed the first suite was too loose.

Every test here pins an exact, calibrated value (or a threshold boundary) that a specific injected
bug used to slip past. Names reference what each one protects.
"""

import math
from datetime import date, timedelta

import numpy as np
import pytest

from app.modules.athletes.service import compute_acwr_from_loads
from app.modules.biomechanics.calculations import LANDMARK, hip_flexion_angle
from app.modules.biomechanics.movement_analysis import (
    analyze_gait, analyze_movement, analyze_reps, detect_reps, movement_dynamics,
)
from app.modules.biomechanics.registry import get_calculator
from app.modules.pose import pipeline as P
from app.modules.pose.analysis import build_track, clean_track, jitter_deg
from app.modules.pose.processing import _dense_series, analyze_frames, compute_biomechanics
from app.modules.recommendations.rules import generate_recommendations
from app.modules.risk_scoring import anomaly as AN
from app.modules.risk_scoring.injury_categories import _kinematic_driver
from app.modules.risk_scoring.scoring import (
    Component, WEIGHTS, combine, compute_sub_scores, consistency_score, score_asymmetry,
    score_history, score_training_load,
)
from tests.synth import make_pose, occlude_leg, roll_camera, run_frames, squat_frames, drop_frames
from tests.test_scoring_engine import TODAY, _assessment, _cats, _feat, inj


# =========================================== scoring ======================================

@pytest.mark.parametrize("acwr,expected", [(1.4, 25.0), (1.45, 37.5), (1.6, 60.0), (1.9, 90.0)])
def test_training_load_interior_points_of_the_ramp(acwr, expected):
    assert score_training_load({"acwr": acwr}).score == pytest.approx(expected, abs=0.01)


def test_consistency_needs_exactly_three_reps():
    assert consistency_score({"n_reps": 2, "cv_pct": 20.0}) == (None, {})
    assert consistency_score({"n_reps": 3, "cv_pct": 15.0})[0] == pytest.approx(50.0)


@pytest.mark.parametrize("months,expected", [(18, 70.0), (22, 70.0), (26, 40.0), (30, 40.0)])
def test_injury_recency_boundary_is_24_months(months, expected):
    assert score_history([inj("knee", months)], "landing", TODAY).score == expected


def test_sub_scores_exact_values():
    comps = [Component(k, s, {}) for k, s in zip(WEIGHTS, [60, 0, 40, None, 40])]
    overall = combine(comps)["overall_score"]
    assert overall == pytest.approx(38.8, abs=0.05)                     # (21+0+8+4)/0.85
    sub = compute_sub_scores(comps, overall, {"n_reps": 5, "cv_pct": 15.0})
    assert sub["movement_quality"]["score"] == pytest.approx(40.0)
    assert sub["fatigue_risk"]["score"] == pytest.approx(40.0)
    assert sub["biomechanical_efficiency"]["score"] == pytest.approx(55.0)   # 100 - mean(asym 40, inconsistency 50)
    assert sub["overall_health"]["score"] == pytest.approx(53.7, abs=0.1)    # mean(40, 61.2, 60)


def test_asymmetry_needs_both_sides():
    assert not score_asymmetry({"knee_flexion_angle_left.p95": 100.0}).available
    assert not score_asymmetry({"knee_flexion_angle_right.p95": 100.0}).available


# =========================================== anomaly ======================================

def test_percentile_of_normal_samples_is_unbiased_not_inflated_by_in_sample_scoring():
    """Fresh samples drawn from the baseline distribution must average ~50. An in-sample forest
    (ranking against the points it was trained on) averages ~62 — a gap of ~7 standard errors."""
    pcts = []
    for seed in range(6):
        rng = np.random.default_rng(seed)
        base, fresh = rng.normal(size=(20, 5)), rng.normal(size=(60, 5))
        pcts += AN.compute_anomaly_scores(fresh, base, 5)
    assert 44 < np.mean(pcts) < 57


@pytest.mark.parametrize("z,n,expected", [(4.2, 10, 0.0), (5.6, 10, 50.0), (7.0, 10, 100.0), (3.012, 1000, 0.0), (9.0, 10, 100.0)])
def test_extremity_tail_thresholds_widen_for_small_baselines(z, n, expected):
    assert AN.z_tail_score(z, n) == pytest.approx(expected, abs=0.2)


def test_robust_z_exact_value_and_noise_floor():
    assert AN.robust_z(110.0, np.arange(10.0, 100.0, 10.0)) == pytest.approx(60 / (1.4826 * 20), abs=1e-6)
    tight = np.array([100.0, 100.05, 99.95, 100.1, 99.9])             # MAD ~0.05 deg
    # without the floor this 4 deg gap would read as z ~ 80; floored at half the 6.5 deg tracking RMSE
    assert AN.robust_z(104.0, tight) == pytest.approx(4.0 / (6.5 / 2), abs=0.01)


def _single_feature_baseline():
    return [{"a.p95": v} for v in [90, 95, 100, 105, 110] * 2]       # median 100, scale 7.413


def test_feature_is_flagged_between_z_1_5_and_2_5():
    hi = AN.assess_video_anomaly({"a.p95": 100 + 2.5 * 7.413}, _single_feature_baseline(), 10)["features"][0]
    lo = AN.assess_video_anomaly({"a.p95": 100 + 1.5 * 7.413}, _single_feature_baseline(), 10)["features"][0]
    assert hi["flagged"] and hi["z"] == pytest.approx(2.5, abs=0.01)
    assert not lo["flagged"] and lo["z"] == pytest.approx(1.5, abs=0.01)


@pytest.fixture
def forest_percentile(monkeypatch):
    """Pin the forest's output so the BLEND logic can be tested deterministically."""
    def set_(p):
        monkeypatch.setattr(AN, "compute_anomaly_scores", lambda *a, **k: [p])
    return set_


def test_blend_uses_the_forest_when_features_look_normal(forest_percentile):
    forest_percentile(97.0)
    out = AN.assess_video_anomaly({"a.p95": 100.0}, _single_feature_baseline(), 10)
    assert out["isolation_forest_score"] == pytest.approx(70.0) and out["extremity_score"] == 0.0
    assert out["deviation_score"] == pytest.approx(70.0)              # a z-only scorer would say 0
    assert out["flagged"] is True                                      # percentile >= 95


def test_blend_uses_extremity_when_the_forest_is_blind(forest_percentile):
    forest_percentile(50.0)                                            # forest sees nothing unusual...
    out = AN.assess_video_anomaly({"a.p95": 400.0}, _single_feature_baseline(), 10)  # ...but it is 40 sigma out
    assert out["isolation_forest_score"] == 0.0 and out["extremity_score"] == 100.0
    assert out["deviation_score"] == 100.0 and out["flagged"] is True  # flagged by extremity alone


def test_blend_is_quiet_when_both_signals_are_quiet(forest_percentile):
    forest_percentile(50.0)
    out = AN.assess_video_anomaly({"a.p95": 101.0}, _single_feature_baseline(), 10)
    assert out["deviation_score"] == 0.0 and out["flagged"] is False


def test_baseline_floor_error_names_the_video_level_features():
    with pytest.raises(AN.InsufficientBaselineError) as e:
        AN.assess_video_anomaly({"a.p95": 1.0}, [{"a.p95": 1.0}] * 3, 10)
    assert (e.value.metric_name, e.value.have, e.value.need) == ("video-level features", 3, 10)


# =========================================== injury categories ============================

@pytest.mark.parametrize("z,expected", [(-0.5, 0.0), (-1.0, 0.0), (-2.0, 50.0), (-3.0, 100.0), (-9.0, 100.0), (+3.0, 0.0)])
def test_kinematic_driver_ramp_and_direction(z, expected):
    feats = [_feat("knee_flexion_angle_left", "p95", 50, 100, z)]
    score, _ = _kinematic_driver(feats, ("knee_flexion_angle_left",), "p95", -1)
    assert score == pytest.approx(expected)


def test_acl_risk_is_the_exact_weighted_mean_of_its_drivers():
    # reduced knee flexion (z=-3 -> 100, weight 2) + no prior knee injury (0, weight 3) = 200/5
    acl = _cats("landing", feats=[_feat("knee_flexion_angle_left", "p95", 40, 95, -3.0)])["acl"]
    assert acl["risk_score"] == pytest.approx(40.0)
    assert {d["factor"]: d["score"] for d in acl["drivers"]} == {"reduced peak knee flexion": 100.0, "prior knee injury": 0.0}


def test_knee_flexion_ABOVE_baseline_is_not_an_acl_risk():
    acl = _cats("landing", feats=[_feat("knee_flexion_angle_left", "p95", 130, 95, +3.0)])["acl"]
    drv = {d["factor"]: d["score"] for d in acl["drivers"]}
    assert drv["reduced peak knee flexion"] == 0.0


def test_the_worst_prior_injury_in_a_region_drives_the_history_factor():
    acl = _cats("landing", injuries=[inj("knee"), inj("knee", 40)])["acl"]
    assert {d["factor"]: d["score"] for d in acl["drivers"]}["prior knee injury"] == 100.0


def test_overuse_uses_load_and_fatigue_with_their_own_weights():
    # load 100 (w3), fatigue 0 (w2), no unresolved injury 0 (w1) -> 300/6
    assert _cats(load=100, fatigue=0)["overuse"]["risk_score"] == pytest.approx(50.0)
    # swapped: load 0, fatigue 100 -> 200/6
    assert _cats(load=0, fatigue=100)["overuse"]["risk_score"] == pytest.approx(33.3, abs=0.1)


# =========================================== recommendations ==============================

def _titles(a, mv="landing"):
    return [r["title"] for r in generate_recommendations(a, mv)]


def test_recommendations_need_a_real_deviation_z_2():
    weak = _assessment(feats=[_feat("knee_flexion_angle_left", "p95", 80, 100, -1.5)])
    strong = _assessment(feats=[_feat("knee_flexion_angle_left", "p95", 60, 100, -2.5)])
    assert not any("Soft-landing" in t for t in _titles(weak))
    assert any("Soft-landing" in t for t in _titles(strong))


@pytest.mark.parametrize("score,present,priority", [(20, False, None), (40, True, 3), (60, True, 2)])
def test_asymmetry_recommendation_threshold_and_priority(score, present, priority):
    a = _assessment(breakdown={"movement_asymmetry": {"available": True, "score": score, "detail": {
        "left_peak_deg": 100, "right_peak_deg": 70, "lsi_pct": 70}}})
    recs = [r for r in generate_recommendations(a, "squatting") if r["title"] == "Address left/right asymmetry"]
    assert bool(recs) is present
    if present:
        assert recs[0]["priority"] == priority


@pytest.mark.parametrize("score,present,priority", [(10, False, None), (40, True, 2), (60, True, 1)])
def test_load_recommendation_threshold_and_priority(score, present, priority):
    a = _assessment(breakdown={"training_load_indicators": {"available": True, "score": score, "detail": {"acwr": 1.6}}})
    recs = [r for r in generate_recommendations(a, "squatting") if r["title"] == "Manage training-load spike"]
    assert bool(recs) is present
    if present:
        assert recs[0]["priority"] == priority


def test_urgent_items_are_sorted_ahead_of_items_generated_earlier():
    a = _assessment(
        feats=[_feat("knee_flexion_angle_left", "p95", 60, 100, -2.5)],      # generated first, priority 3
        breakdown={"historical_injury_factors": {"available": True, "score": 100, "detail": {
            "injuries": [{"body_part": "knee", "status": "unresolved"}]}}},   # generated later, priority 1
    )
    recs = generate_recommendations(a, "squatting")
    assert recs[0]["priority"] == 1
    assert [r["priority"] for r in recs] == sorted(r["priority"] for r in recs)


@pytest.mark.parametrize("level,present", [("high", True), ("moderate", True), ("low", False)])
def test_nordic_hamstring_recommendation_follows_the_category_level(level, present):
    titles = _titles(_assessment(cats={"hamstring": {"level": level}}), "running")
    assert any("Nordic" in t for t in titles) is present


# =========================================== ACWR =========================================

def _loads(p):
    return {TODAY - timedelta(days=d): v for d, v in p.items()}


def test_acwr_exactly_1_5_is_not_flagged_but_just_above_is():
    at = compute_acwr_from_loads(_loads({0: 1050, 10: 1750}), TODAY, TODAY - timedelta(days=90))
    over = compute_acwr_from_loads(_loads({0: 1060, 10: 1740}), TODAY, TODAY - timedelta(days=90))
    assert at["acwr"] == 1.5 and at["flagged"] is False
    assert over["acwr"] > 1.5 and over["flagged"] is True


def test_acute_window_is_exactly_seven_days():
    r = compute_acwr_from_loads(_loads({7: 700, 20: 100}), TODAY, TODAY - timedelta(days=90))
    assert r["acute_load"] == 0.0 and r["acwr"] == 0.0               # day 7 is OUTSIDE the acute window
    r = compute_acwr_from_loads(_loads({6: 700, 20: 100}), TODAY, TODAY - timedelta(days=90))
    assert r["acute_load"] == 700.0                                    # day 6 is inside


# =========================================== pipeline =====================================

from tests.test_pipeline_loop import _detector, _write_video  # noqa: E402
import cv2  # noqa: E402


def test_timestamps_are_forced_increasing_when_rounding_would_collide(tmp_path):
    """At 5000 fps, int(round(i*1000/fps)) repeats (0,0,0,0,1,...). The guard must still make them strictly increase."""
    detect, calls = _detector()
    cap = cv2.VideoCapture(_write_video(tmp_path / "v.mp4", n=40))
    P._run_pass(cap, detect, 5000.0, 40, None, None, None, 1, False, {})
    cap.release()
    assert len(calls["ts"]) == 40
    assert all(b > a for a, b in zip(calls["ts"], calls["ts"][1:]))


def test_low_light_enhancement_is_actually_applied_inside_the_loop(tmp_path):
    means = {}
    for enhance in (False, True):
        seen = []
        pose = make_pose(10, 10, 5)

        def detect(rgb, ts, seen=seen):
            seen.append(float(rgb.mean()))
            return P._Detection(pose, None, None)

        cap = cv2.VideoCapture(_write_video(tmp_path / f"dark{enhance}.mp4", brightness=25, n=10))
        P._run_pass(cap, detect, 30.0, 10, None, None, None, 1, enhance, {})
        cap.release()
        means[enhance] = np.mean(seen)
    assert means[True] > means[False] + 20


# =========================================== biomechanics =================================

def test_hip_flexion_uses_the_flexion_from_extension_convention():
    stand = make_pose(0, 0, 0, 0, 0)
    assert hip_flexion_angle(stand, "left") == pytest.approx(0.0, abs=1.0)        # NOT ~180
    leaned = make_pose(0, 0, 40, 0, 0)
    assert hip_flexion_angle(leaned, "left") == pytest.approx(40.0, abs=1.0)
    deep = make_pose(100, 100, 35)                                                 # thigh 50 deg + trunk 35 deg
    assert hip_flexion_angle(deep, "left") == pytest.approx(85.0, abs=1.0)


def test_landing_metrics_carry_no_fabricated_phase_label():
    metrics = get_calculator("landing").compute_all(make_pose(40, 40, 20), "sagittal")
    assert metrics and all(not m.get("phase") for m in metrics)


# =========================================== movement analysis ============================

def _bump(n_up, lo, hi):
    return np.linspace(lo, hi, n_up, endpoint=False)


def test_a_dip_below_40_percent_ends_a_rep():
    sig = np.concatenate([np.zeros(30), _bump(30, 0, 100), _bump(15, 100, 25), _bump(15, 25, 100),
                          _bump(30, 100, 0), np.zeros(30)])
    assert len(detect_reps(sig)) == 2         # a shallow dip to 25 is NOT a single continuous rep
    held = np.concatenate([np.zeros(30), _bump(30, 0, 100), _bump(15, 100, 55), _bump(15, 55, 100),
                           _bump(30, 100, 0), np.zeros(30)])
    assert len(detect_reps(held)) == 1        # a dip to only 55 is within the dead band


def test_drift_compares_the_first_and_last_thirds_not_single_reps():
    out = movement_dynamics([100, 90, 100, 100, 100, 130])
    assert out["drift_pct"] == 21.1 and out["drift_direction"] == "increase"


def test_rep_timing_active_time_vs_exact_cycle_time():
    sig = [np.zeros(10)]
    for L in (30, 60, 120):
        sig.append(100 * (1 - np.cos(2 * np.pi * np.arange(L) / L)) / 2)
    out = analyze_reps({"knee_flexion_angle_left": np.concatenate(sig)}, "squatting", 30.0)
    assert out["n_reps"] == 3
    # exact cycle time = mean peak-to-peak spacing: ((30+60)/2 + (60+120)/2) / 2 / 30 frames/s = 2.25 s
    assert out["mean_cycle_s"] == pytest.approx(2.25, abs=0.05)
    # active time excludes flat valley edges: ~14% shorter than the 70-frame mean (2.33 s), never the max (4 s) or min
    assert 1.8 < out["mean_rep_s"] < 2.3


def _gait(frames, mv="running"):
    t = build_track(frames, 30)
    return analyze_gait(clean_track(t, mv), t.fps_eff), t


@pytest.mark.parametrize("kw", [dict(seconds=1.2), dict(cadence_spm=30, seconds=10), dict(cadence_spm=400, seconds=4)])
def test_gait_is_refused_for_too_few_steps_or_implausible_cadence(kw):
    assert _gait(run_frames(**kw))[0] is None


def test_quiet_standing_sway_is_not_gait():
    assert _gait(run_frames(kmax=0.0, swing_deg=2.0, seconds=6))[0] is None


def test_gait_survives_heavy_landmark_noise_and_the_stress_case_really_needs_the_band(monkeypatch):
    """Slow, small-swing gait buried in 12 cm of landmark noise. Calibrated so that a detector WITHOUT the
    confirmation band reads ~108 steps/min for a true 80 — the assertion below proves the test has teeth."""
    import app.modules.biomechanics.movement_analysis as MV
    frames = run_frames(cadence_spm=80, swing_deg=8, kmax=10, noise_m=0.12, seconds=14, seed=3)
    g, _ = _gait(frames)
    assert g["cadence_spm"] == pytest.approx(80, rel=0.05)         # (asymmetry degrades at this absurd noise; see next test)
    monkeypatch.setattr(MV, "GAIT_CONFIRM_BAND", 0.0)
    unconfirmed, _ = _gait(frames)
    assert abs(unconfirmed["cadence_spm"] - 80) > 0.15 * 80       # without the band this stress case is wrong


def test_symmetric_gait_reads_as_symmetric_at_realistic_noise():
    g, _ = _gait(run_frames(noise_m=0.03, seconds=6))
    assert g["cadence_spm"] == pytest.approx(170, rel=0.05) and g["step_time_asymmetry_pct"] < 5


def test_gait_is_found_when_travel_is_almost_along_the_depth_axis():
    """89 deg of yaw leaves only ~4 cm of ankle separation in the image-x axis (below the 15 cm floor):
    an x-axis-only detector sees nothing, the principal-axis detector still finds the stride."""
    fr = run_frames(seconds=6)
    r = math.radians(89)
    R = np.array([[math.cos(r), 0, math.sin(r)], [0, 1, 0], [-math.sin(r), 0, math.cos(r)]])
    rot = [{**f, "world_landmarks": {k: (R @ np.array(v)).tolist() for k, v in f["world_landmarks"].items()}} for f in fr]
    g, _ = _gait(rot)
    assert g and g["cadence_spm"] == pytest.approx(170, rel=0.05)


def test_a_short_run_is_not_called_a_mislabel():
    """Four steps is not enough evidence to accuse the coach of mislabelling a squat."""
    fr = run_frames(seconds=1.6)
    g, t = _gait(fr)
    assert g and g["n_steps"] < 6
    from tests.test_movement_analysis import _knee_series
    out = analyze_movement("squatting", "sagittal", _knee_series(fr), clean_track(t, "squatting"), t.fps_eff)
    assert not any(w["code"] == "movement_type_mismatch_suspected" for w in out["warnings"])


# =========================================== pose cleaning & quality ======================

def test_long_dropouts_stay_missing_in_the_cleaned_track():
    t = build_track(drop_frames(squat_frames(n_reps=5), ranges=[(60, 120)]), 30)   # 2 s outage
    cleaned = clean_track(t, "squatting")
    gap_mid = int(np.flatnonzero(t.grid == 90)[0])
    assert np.isnan(cleaned[gap_mid, LANDMARK["left_knee"]]).all()
    short = build_track(drop_frames(squat_frames(n_reps=5), ranges=[(60, 63)]), 30)  # 3 frames = 0.1 s
    assert np.isfinite(clean_track(short, "squatting")[int(np.flatnonzero(short.grid == 61)[0]), LANDMARK["left_knee"]]).all()


def test_jitter_estimate_matches_the_injected_noise():
    rng = np.random.default_rng(0)
    t = np.arange(400)
    angle = 60 + 40 * np.sin(2 * np.pi * t / 90) + rng.normal(0, 2.0, len(t))
    assert jitter_deg(angle) == pytest.approx(2.0, abs=0.3)
    assert jitter_deg(np.full(5, 1.0)) is None                          # too short
    angle[100:140] = np.nan                                              # hidden-limb frames must not count
    assert jitter_deg(angle) == pytest.approx(2.0, abs=0.35)


def _quality(frames, **kw):
    return analyze_frames(frames, "squatting", "sagittal", 30)[1]["quality"]


def test_noise_level_sets_the_grade():
    assert _quality(squat_frames(noise_m=0.0, seed=1))["grade"] == "good"
    q = _quality(squat_frames(noise_m=0.02, seed=1))
    assert q["grade"] == "fair" and 3.5 < q["jitter_deg"] < 6.5 and "noisy_tracking" in {w["code"] for w in q["warnings"]}
    q = _quality(squat_frames(noise_m=0.04, seed=1))
    assert q["grade"] == "poor" and q["jitter_deg"] >= 6.5


def test_grade_ladder_for_occlusion_and_camera_roll():
    assert _quality(roll_camera(squat_frames(), 15))["grade"] == "fair"                      # a warning -> fair
    one_gone = _quality(occlude_leg(squat_frames(), "right", 1.0))
    assert one_gone["grade"] == "fair" and one_gone["jitter_deg"] < 1.0                      # hidden-leg garbage is NOT noise
    both = occlude_leg(occlude_leg(squat_frames(), "left", 0.7), "right", 0.7)
    q = _quality(both)
    assert q["grade"] == "poor" and q["usable_pct"]["left_leg"] < 50 and q["usable_pct"]["right_leg"] < 50


def test_qualitative_metrics_never_drive_rep_analysis():
    frames = squat_frames()
    track = build_track(frames, 30)
    metrics = compute_biomechanics(
        [{**f} for f in frames], get_calculator("squatting"), "other")
    assert any(m["confidence"] == "qualitative" for m in metrics)
    assert not [k for k in _dense_series(metrics, track) if "valgus" in k]


def test_fast_landing_peaks_survive_the_landing_filter():
    metrics, a = analyze_frames(squat_frames(n_reps=6, rep_s=0.8, depth=100, lead_s=0.4, tail_s=0.4), "landing", "sagittal", 30)
    k = np.array([m["value"] for m in metrics if m["name"] == "knee_flexion_angle_left"])
    assert np.percentile(k, 95) > 90 and a["movement"]["reps"]["n_reps"] == 6


def test_a_single_rep_has_no_cycle_time():
    sig = np.concatenate([np.zeros(20), 100 * (1 - np.cos(2 * np.pi * np.arange(60) / 60)) / 2, np.zeros(20)])
    out = analyze_reps({"knee_flexion_angle_left": sig}, "squatting", 30.0)
    assert out["n_reps"] == 1 and "mean_rep_s" in out
    assert "mean_cycle_s" not in out                     # one rep has no peak-to-peak spacing (was NaN)


def test_non_finite_coordinates_are_treated_as_missing_without_numeric_warnings():
    import warnings
    frames = squat_frames(n_reps=3)
    for i in range(20, 60, 3):
        lm = dict(frames[i]["world_landmarks"])
        for name in ("right_knee", "left_hip", "right_hip", "left_shoulder", "right_shoulder"):
            lm[str(LANDMARK[name])] = [float("inf"), float("inf"), float("nan")]   # inf - inf -> invalid-value warnings
        frames[i] = {**frames[i], "world_landmarks": lm}
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)   # overflow / invalid-value would raise here
        metrics, analysis = analyze_frames(frames, "squatting", "sagittal", 30)
    assert metrics and all(math.isfinite(m["value"]) for m in metrics)
