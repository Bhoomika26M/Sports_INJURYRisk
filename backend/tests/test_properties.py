"""Property-based tests: invariants that must hold for ANY input, plus fuzzing for crashes."""

import json
import math
from datetime import date, timedelta

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from app.modules.biomechanics.movement_analysis import analyze_gait, detect_reps
from app.modules.pose.analysis import build_track, clean_track
from app.modules.pose.processing import analyze_frames
from app.modules.recommendations.rules import generate_recommendations
from app.modules.risk_scoring.injury_categories import assess_injury_categories
from app.modules.risk_scoring.scoring import (
    Component, WEIGHTS, _ramp, categorize, combine, compute_sub_scores, score_asymmetry,
    score_fatigue, score_history, score_training_load,
)
from tests.synth import drop_frames, occlude_leg, run_frames, spike, squat_frames

FUZZ = settings(max_examples=40, deadline=None, suppress_health_check=list(HealthCheck))
KEYS = list(WEIGHTS)
MOVEMENTS = ["squatting", "landing", "jumping", "throwing", "running", "sprinting", "cutting", "sport_specific"]
fl = st.floats(min_value=0, max_value=100, allow_nan=False)


# ---------------------------------- scoring invariants ----------------------------------

score_lists = st.lists(st.one_of(st.none(), fl), min_size=5, max_size=5).filter(lambda l: any(x is not None for x in l))


@given(score_lists)
@FUZZ
def test_combine_is_bounded_consistent_and_renormalised(scores):
    r = combine([Component(k, s, {}) for k, s in zip(KEYS, scores)])
    assert 0 <= r["overall_score"] <= 100
    assert r["risk_category"] == categorize(r["overall_score"])
    bd = r["score_breakdown"]
    assert sum(b["effective_weight"] for b in bd.values()) == pytest.approx(1.0, abs=0.01)
    assert sum(b["points"] for b in bd.values()) == pytest.approx(r["overall_score"], abs=0.3)
    assert all((not b["available"]) == (b["max"] == 0.0) for b in bd.values())
    assert r["data_completeness"] == pytest.approx(sum(WEIGHTS[k] for k, s in zip(KEYS, scores) if s is not None), abs=0.01)


@given(score_lists, st.integers(0, 4), st.floats(0, 100))
@FUZZ
def test_raising_one_component_never_lowers_the_overall_score(scores, i, new):
    if scores[i] is None:
        return
    base = combine([Component(k, s, {}) for k, s in zip(KEYS, scores)])["overall_score"]
    bumped = list(scores)
    bumped[i] = max(scores[i], new)
    assert combine([Component(k, s, {}) for k, s in zip(KEYS, bumped)])["overall_score"] >= base - 0.06


@given(st.floats(-1e6, 1e6, allow_nan=False), st.floats(-100, 100), st.floats(-100, 100))
@FUZZ
def test_ramp_is_bounded_and_monotone(x, a, b):
    start, full = (a, b) if a < b else (b, a)
    if start == full:
        return
    v = _ramp(x, start, full)
    assert 0 <= v <= 100
    assert _ramp(x + 1.0, start, full) >= v - 1e-9


@given(st.floats(0, 50, allow_nan=False))
@FUZZ
def test_training_load_score_is_bounded_and_monotone_in_acwr(acwr):
    s = score_training_load({"acwr": acwr}).score
    assert 0 <= s <= 100 and score_training_load({"acwr": acwr + 0.1}).score >= s - 1e-9


@given(st.floats(0, 400, allow_nan=False), st.floats(0, 400, allow_nan=False),
       st.one_of(st.none(), st.fixed_dictionaries({"left_leg": fl, "right_leg": fl})))
@FUZZ
def test_asymmetry_is_symmetric_bounded_or_unavailable(left, right, usable):
    a = score_asymmetry({"knee_flexion_angle_left.p95": left, "knee_flexion_angle_right.p95": right}, usable)
    b = score_asymmetry({"knee_flexion_angle_left.p95": right, "knee_flexion_angle_right.p95": left}, usable)
    assert a.score == b.score                                    # swapping sides cannot change the score
    assert a.score is None or 0 <= a.score <= 100


injuries = st.lists(st.fixed_dictionaries({
    "body_part": st.text(min_size=1, max_size=30),
    "severity": st.one_of(st.none(), st.sampled_from(["minor", "moderate", "severe"])),
    "injury_date": st.dates(date(2015, 1, 1), date(2026, 9, 1)),
    "recovery_date": st.one_of(st.none(), st.dates(date(2015, 1, 1), date(2026, 9, 1))),
}), max_size=6)


@given(injuries, st.sampled_from(MOVEMENTS + ["unknown_movement"]))
@FUZZ
def test_history_score_is_a_known_ordinal_level_for_any_injury_list(inj_list, movement):
    c = score_history(inj_list, movement, date(2026, 9, 30))
    assert c.available and c.score in (0.0, 10.0, 25.0, 40.0, 70.0, 100.0)
    if inj_list:
        assert c.score > 0 or False


@st.composite
def full_assessment(draw):
    feats = {}
    for m in ("knee_flexion_angle_left", "knee_flexion_angle_right", "trunk_lean_angle", "hip_flexion_angle_left"):
        for stat in ("p95", "p05"):
            if draw(st.booleans()):
                feats[f"{m}.{stat}"] = draw(st.floats(0, 180))
    asym = score_asymmetry(feats, draw(st.one_of(st.none(), st.fixed_dictionaries({"left_leg": fl, "right_leg": fl}))))
    load = score_training_load({"acwr": draw(st.one_of(st.none(), st.floats(0, 4)))})
    rpe = draw(st.one_of(st.none(), st.fixed_dictionaries({
        "rpe_trend": st.floats(-5, 5), "recent_mean_rpe": st.floats(0, 10), "baseline_mean_rpe": st.floats(0, 10),
        "n_recent": st.integers(3, 20), "n_baseline": st.integers(3, 20)})))
    dyn = draw(st.one_of(st.none(), st.fixed_dictionaries({
        "n_reps": st.integers(0, 12), "drift_pct": st.floats(-80, 80), "drift_direction": st.sampled_from(["increase", "decrease", "stable"]),
        "cv_pct": st.floats(0, 60)})))
    fatigue = score_fatigue(rpe, dyn)
    hist = score_history(draw(injuries), draw(st.sampled_from(MOVEMENTS)), date(2026, 9, 30))
    anomalous = draw(st.booleans())
    zs = [{"feature": k, "metric": k.rsplit(".", 1)[0], "stat": k.rsplit(".", 1)[1], "value": v,
           "baseline_median": 90.0, "z": draw(st.floats(-8, 8)), "direction": "above", "flagged": True}
          for k, v in feats.items()] if anomalous else []
    bio = Component("biomechanical_deviations", draw(fl), {"deviating_features": []}) if anomalous or draw(st.booleans()) else Component("biomechanical_deviations", None, {})
    comps = [bio, hist, asym, load, fatigue]
    if all(not c.available for c in comps):
        comps[1] = Component("historical_injury_factors", 0.0, {})
    combined = combine(comps)
    movement = draw(st.sampled_from(MOVEMENTS))
    cats = assess_injury_categories(
        movement_type=movement, anomaly={"features": zs} if zs else None,
        injuries=hist.detail.get("injuries", []), components={c.key: c for c in comps},
        qualitative=draw(st.one_of(st.none(), st.fixed_dictionaries({"knee_valgus_deviation_left": st.floats(0, 40)}))))
    assessment = {**combined, "anomaly_features": zs, "injury_categories": cats,
                  "sub_scores": compute_sub_scores(comps, combined["overall_score"], dyn)}
    return assessment, movement


@given(full_assessment())
@FUZZ
def test_recommendations_and_categories_are_well_formed_for_any_assessment(args):
    a, movement = args
    recs = generate_recommendations(a, movement)
    assert 1 <= len(recs) <= 8
    assert [r["priority"] for r in recs] == sorted(r["priority"] for r in recs)
    assert len({r["title"] for r in recs}) == len(recs)
    assert all(r["category"] in {"exercise", "mobility", "strengthening", "recovery", "training_modification"}
               and 1 <= r["priority"] <= 5 and r["description"].strip() and len(r["title"]) <= 255 for r in recs)
    assert set(a["injury_categories"]) == {"acl", "hamstring", "ankle_sprain", "shoulder", "lower_back", "overuse"}
    for c in a["injury_categories"].values():
        assert c["level"] in ("low", "moderate", "high", "critical", "insufficient_data")
        assert (c["risk_score"] is None) == (c["level"] == "insufficient_data")
        assert c["risk_score"] is None or 0 <= c["risk_score"] <= 100
    for s in a["sub_scores"].values():
        assert s["score"] is None or 0 <= s["score"] <= 100
    json.dumps({k: v for k, v in a.items()})                     # everything we persist must serialise


# ---------------------------------- movement analysis fuzz --------------------------------

@given(st.lists(st.floats(-500, 500, allow_nan=False, allow_infinity=False), max_size=300))
@FUZZ
def test_detect_reps_never_crashes_and_peaks_lie_within_the_data(values):
    peaks = detect_reps(np.array(values))
    if values:
        assert all(min(values) - 1e-6 <= p <= max(values) + 1e-6 for p in peaks)
    assert len(peaks) <= len(values)


@given(st.integers(0, 90), st.integers(0, 2**31 - 1), st.floats(0, 0.3))
@FUZZ
def test_gait_analysis_never_crashes_on_random_or_partly_missing_landmarks(T, seed, nan_frac):
    rng = np.random.default_rng(seed)
    xyz = rng.normal(0, 0.3, (T, 33, 3))
    xyz[rng.random(xyz.shape) < nan_frac] = np.nan
    g = analyze_gait(xyz, 30.0)
    assert g is None or (60 <= g["cadence_spm"] <= 330 and g["n_steps"] >= 4)


# ---------------------------------- pose pipeline fuzz ------------------------------------

def _check_analysis(metrics, analysis):
    assert all(math.isfinite(m["value"]) for m in metrics)
    for m in metrics:
        if m["name"].startswith(("knee_flexion", "hip_flexion")):
            assert -1 <= m["value"] <= 181
        if m["name"] == "trunk_lean_angle":
            assert -1 <= m["value"] <= 181
    json.dumps(analysis)
    q = analysis["quality"]
    assert q["grade"] in ("good", "fair", "poor")
    assert all({"code", "message"} <= set(w) for w in q["warnings"])


@st.composite
def corrupted_clip(draw):
    kind = draw(st.sampled_from(["squat", "run"]))
    fps = draw(st.sampled_from([24, 30, 60]))
    frames = (squat_frames(n_reps=draw(st.integers(1, 5)), fps=fps, depth=draw(st.floats(10, 150)),
                           rep_s=draw(st.floats(0.5, 4.0)), noise_m=draw(st.floats(0, 0.05)), seed=draw(st.integers(0, 99)))
              if kind == "squat" else
              run_frames(cadence_spm=draw(st.floats(80, 260)), seconds=draw(st.floats(1.0, 6.0)), fps=fps,
                         asym=draw(st.floats(0, 0.3)), noise_m=draw(st.floats(0, 0.05)), seed=draw(st.integers(0, 99))))
    if draw(st.booleans()):
        frames = occlude_leg(frames, draw(st.sampled_from(["left", "right"])), draw(st.floats(0, 1)))
    if draw(st.booleans()) and len(frames) > 12:
        frames = drop_frames(frames, every=draw(st.one_of(st.none(), st.integers(2, 12))),
                             ranges=[(a, a + draw(st.integers(1, 40))) for a in draw(st.lists(st.integers(0, len(frames)), max_size=2))])
    if draw(st.booleans()) and len(frames) > 12:
        frames = spike(frames, draw(st.integers(0, len(frames) - 1)), draw(st.sampled_from(["left_knee", "right_ankle", "left_shoulder"])),
                       draw(st.floats(-2, 2)))
    if draw(st.booleans()):
        frames = [{**f, "visibility": None} for f in frames]
    return frames, fps


@given(corrupted_clip(), st.sampled_from(MOVEMENTS), st.sampled_from(["sagittal", "frontal", "other"]))
@settings(max_examples=60, deadline=None, suppress_health_check=list(HealthCheck))
def test_analysis_survives_any_realistic_recording_problem(clip, movement, view):
    frames, fps = clip
    metrics, analysis = analyze_frames(frames, movement, view, fps)
    _check_analysis(metrics, analysis)
    seen = {f["frame_number"] for f in frames}
    assert {m["frame_number"] for m in metrics} <= seen          # metrics only for frames the model actually saw


@st.composite
def garbage_clip(draw):
    n = draw(st.integers(1, 40))
    nums = sorted(draw(st.sets(st.integers(0, 300), min_size=n, max_size=n)))
    coord = st.one_of(st.floats(-4, 4), st.floats(-4, 4), st.just(float('nan')), st.just(float('inf')), st.just(float('-inf')))
    frames = []
    for f in nums:
        idx = draw(st.sets(st.integers(0, 32), max_size=33))
        vis = draw(st.one_of(st.none(), st.lists(st.floats(0, 1), min_size=33, max_size=33), st.lists(st.floats(0, 1), min_size=0, max_size=10)))
        frames.append({"frame_number": f, "timestamp_ms": f * 33,
                       "world_landmarks": {str(i): [draw(coord), draw(coord), draw(coord)] for i in idx}, "visibility": vis})
    return frames


@given(garbage_clip(), st.sampled_from(MOVEMENTS), st.sampled_from(["sagittal", "frontal", "other"]),
       st.sampled_from([None, 24, 30, 60]))
@settings(max_examples=120, deadline=None, suppress_health_check=list(HealthCheck))
def test_analysis_never_crashes_on_garbage_landmarks(frames, movement, view, fps):
    """Random coordinates, NaN/inf, missing landmarks, wrong-length visibility, 1-frame clips."""
    metrics, analysis = analyze_frames(frames, movement, view, fps)
    _check_analysis(metrics, analysis)


@given(corrupted_clip(), st.sampled_from(MOVEMENTS))
@settings(max_examples=40, deadline=None, suppress_health_check=list(HealthCheck))
def test_cleaning_never_invents_values_outside_the_observed_range(clip, movement):
    frames, fps = clip
    track = build_track(frames, fps)
    if track is None:
        return
    cleaned = clean_track(track, movement)
    assert cleaned.shape == track.xyz.shape
    raw = track.xyz.copy()
    low = np.nan_to_num(track.vis, nan=1.0) < 0.5 if track.has_visibility else np.zeros(raw.shape[:2], bool)
    raw[low] = np.nan                                            # visibility gating happens before everything else
    for j in range(33):
        for c in range(3):
            r, k = raw[:, j, c], cleaned[:, j, c]
            if np.isfinite(r).any():
                ok = np.isfinite(k)
                assert (k[ok] >= np.nanmin(r) - 1e-9).all() and (k[ok] <= np.nanmax(r) + 1e-9).all()
            else:
                assert not np.isfinite(k).any()
