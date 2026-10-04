"""Pure-engine tests: scoring components, the spec's weighted model, injury categories, recommendations."""

from datetime import date, timedelta

import numpy as np
import pytest

from app.modules.athletes.service import (
    compute_acwr_from_loads, compute_rpe_trend_from_entries,
)
from app.modules.recommendations.rules import generate_recommendations
from app.modules.risk_scoring.injury_categories import assess_injury_categories
from app.modules.risk_scoring.scoring import (
    WEIGHTS, Component, body_part_region, categorize, combine, compute_sub_scores,
    score_asymmetry, score_biomechanical, score_fatigue, score_history, score_training_load,
)

TODAY = date(2026, 9, 30)


# ------------------------------------ the spec's weights ----------------------------------

def test_spec_weights_are_35_20_20_15_10():
    assert WEIGHTS == {
        "biomechanical_deviations": 0.35, "historical_injury_factors": 0.20, "movement_asymmetry": 0.20,
        "training_load_indicators": 0.15, "fatigue_indicators": 0.10,
    }
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def _all(scores):
    return [Component(k, s, {}) for k, s in zip(WEIGHTS, scores)]


def test_combine_applies_spec_weights_when_everything_is_available():
    r = combine(_all([100, 0, 0, 0, 0]))
    assert r["overall_score"] == 35.0 and r["data_completeness"] == 1.0
    r = combine(_all([0, 100, 100, 0, 0]))
    assert r["overall_score"] == 40.0
    r = combine(_all([100] * 5))
    assert r["overall_score"] == 100.0 and r["risk_category"] == "critical"
    assert sum(b["points"] for b in r["score_breakdown"].values()) == pytest.approx(r["overall_score"], abs=0.2)


def test_unavailable_component_is_excluded_not_scored_as_zero():
    comps = _all([80, 0, None, None, None])
    r = combine(comps)
    # bio (35) + history (20) renormalised: 80*0.636 + 0*0.364
    assert r["overall_score"] == pytest.approx(50.9, abs=0.1)
    assert r["data_completeness"] == 0.55
    assert set(r["missing_components"]) == {"movement_asymmetry", "training_load_indicators", "fatigue_indicators"}
    assert r["score_breakdown"]["movement_asymmetry"]["available"] is False
    # "no data" must never LOWER the score relative to the data we do have
    assert r["overall_score"] > 80 * WEIGHTS["biomechanical_deviations"]


def test_combine_needs_at_least_one_component():
    with pytest.raises(ValueError):
        combine(_all([None] * 5))


@pytest.mark.parametrize("score,cat", [(0, "low"), (24.9, "low"), (25, "moderate"), (49.9, "moderate"),
                                       (50, "high"), (74.9, "high"), (75, "critical"), (100, "critical")])
def test_category_boundaries(score, cat):
    assert categorize(score) == cat


# ------------------------------------ components ------------------------------------------

def inj(part, recovered_months_ago=None, severity="moderate"):
    rec = None if recovered_months_ago is None else TODAY - timedelta(days=int(30.44 * recovered_months_ago))
    return {"body_part": part, "severity": severity, "injury_date": TODAY - timedelta(days=900), "recovery_date": rec}


def test_history_none_is_zero_not_missing():
    c = score_history([], "squatting", TODAY)
    assert c.available and c.score == 0.0


@pytest.mark.parametrize("injuries,movement,expected", [
    ([inj("Left knee ACL")], "squatting", 100.0),                    # unresolved + relevant
    ([inj("knee", 6)], "landing", 70.0),                              # recent + relevant
    ([inj("knee", 40)], "landing", 40.0),                             # remote + relevant
    ([inj("shoulder")], "squatting", 40.0),                           # unresolved but not this movement
    ([inj("shoulder", 6)], "squatting", 25.0),
    ([inj("shoulder", 40)], "squatting", 10.0),
    ([inj("mystery body part", 40)], "squatting", 40.0),              # unknown region -> treated as relevant
    ([inj("shoulder", 40), inj("knee", 6)], "squatting", 70.0),       # highest level wins
])
def test_history_ordinal_levels(injuries, movement, expected):
    assert score_history(injuries, movement, TODAY).score == expected


@pytest.mark.parametrize("text,region", [
    ("Left ACL tear", "knee"), ("Hamstring strain", "hamstring"), ("right ankle sprain", "ankle"),
    ("Achilles", "ankle"), ("lower back pain", "lower_back"), ("Rotator cuff", "shoulder"),
    ("groin", "hip_groin"), ("something else", None),
])
def test_body_part_region(text, region):
    assert body_part_region(text) == region


def test_asymmetry_is_continuous_not_a_90_percent_cliff():
    def lsi_to_score(lsi):
        return score_asymmetry({"knee_flexion_angle_left.p95": 100.0, "knee_flexion_angle_right.p95": lsi}).score
    assert lsi_to_score(100) == 0 and lsi_to_score(90) == 0
    assert lsi_to_score(80) == pytest.approx(50, abs=0.5)
    assert lsi_to_score(70) == 100 and lsi_to_score(40) == 100
    assert 0 < lsi_to_score(89) < lsi_to_score(85) < lsi_to_score(75)


def test_asymmetry_unavailable_when_a_leg_was_not_visible():
    feats = {"knee_flexion_angle_left.p95": 100.0, "knee_flexion_angle_right.p95": 60.0}
    c = score_asymmetry(feats, {"left_leg": 95, "right_leg": 30})
    assert not c.available and "not reliably visible" in c.detail["reason"]


def test_asymmetry_unavailable_below_the_noise_floor():
    c = score_asymmetry({"knee_flexion_angle_left.p95": 12.0, "knee_flexion_angle_right.p95": 6.0})
    assert not c.available


def test_asymmetry_unavailable_without_a_side_pair():
    assert not score_asymmetry({"trunk_lean_angle.p95": 20}).available


@pytest.mark.parametrize("acwr,expected", [(0.9, 0), (1.3, 0), (1.5, 50), (1.75, 75), (2.0, 100), (3.0, 100)])
def test_training_load_mapping(acwr, expected):
    assert score_training_load({"acwr": acwr}).score == pytest.approx(expected, abs=0.5)


def test_training_load_unavailable_without_acwr():
    c = score_training_load({"acwr": None, "message": "Insufficient history"})
    assert not c.available and "Insufficient" in c.detail["reason"]


def test_fatigue_uses_either_indicator_and_averages_both():
    rpe = {"rpe_trend": 2.5, "recent_mean_rpe": 8, "baseline_mean_rpe": 5.5, "n_recent": 4, "n_baseline": 9}
    dyn = {"n_reps": 6, "drift_pct": -30.0, "drift_direction": "decrease"}
    assert score_fatigue(rpe, None).score == 100
    assert score_fatigue(None, dyn).score == 100
    assert score_fatigue({**rpe, "rpe_trend": 0.5}, dyn).score == pytest.approx(50)
    assert not score_fatigue(None, None).available
    assert not score_fatigue(None, {"n_reps": 3, "cv_pct": 5.0}).available  # no drift without 4 reps


def test_fatigue_drift_is_direction_agnostic():
    up = score_fatigue(None, {"n_reps": 6, "drift_pct": +20.0, "drift_direction": "increase"}).score
    down = score_fatigue(None, {"n_reps": 6, "drift_pct": -20.0, "drift_direction": "decrease"}).score
    assert up == down > 0


def test_sub_scores_cover_the_five_spec_scores_with_definitions():
    comps = _all([60, 0, 50, None, 40])
    overall = combine(comps)["overall_score"]
    sub = compute_sub_scores(comps, overall, {"n_reps": 5, "cv_pct": 15.0})
    assert set(sub) == {"injury_risk", "movement_quality", "biomechanical_efficiency", "fatigue_risk", "overall_health"}
    assert sub["injury_risk"]["score"] == overall
    assert sub["movement_quality"]["score"] == 40.0
    assert sub["fatigue_risk"]["score"] == 40.0
    assert all(v["definition"] for v in sub.values())
    assert "PROXY" in sub["biomechanical_efficiency"]["definition"]
    assert 0 <= sub["overall_health"]["score"] <= 100


def test_sub_scores_never_invent_values_without_inputs():
    comps = [Component("biomechanical_deviations", 20, {})] + [Component(k, None, {}) for k in list(WEIGHTS)[1:]]
    sub = compute_sub_scores(comps, 20.0, None)
    assert sub["fatigue_risk"]["score"] is None and sub["biomechanical_efficiency"]["score"] is None


# ------------------------------------ ACWR / RPE ------------------------------------------

def _loads(pattern):
    """pattern: {days_ago: load}"""
    return {TODAY - timedelta(days=d): v for d, v in pattern.items()}


def test_acwr_counts_rest_days_as_zero_load():
    # 4 sessions of 100 in the last week; 12 sessions of 100 across the 28-day window
    days = {0: 100, 1: 100, 3: 100, 5: 100, 8: 100, 10: 100, 12: 100, 14: 100, 16: 100, 19: 100, 22: 100, 26: 100}
    r = compute_acwr_from_loads(_loads(days), TODAY, TODAY - timedelta(days=60))
    assert r["acwr"] == pytest.approx((400 / 7) / (1200 / 28), abs=0.01)  # 1.33
    # the OLD formula divided chronic by training days only (12) -> chronic mean 100 -> 0.57
    assert r["acwr"] > 1.2


def test_acwr_flagged_only_above_1_5():
    base = {d: 100 for d in range(7, 28, 3)}
    spike = {**base, **{d: 300 for d in range(0, 7)}}
    assert compute_acwr_from_loads(_loads(spike), TODAY, TODAY - timedelta(days=60))["flagged"] is True
    assert compute_acwr_from_loads(_loads(base), TODAY, TODAY - timedelta(days=60))["flagged"] is False


def test_acwr_refuses_without_a_full_chronic_window():
    r = compute_acwr_from_loads(_loads({0: 100, 1: 100}), TODAY, TODAY - timedelta(days=10))
    assert r["acwr"] is None and "28-day" in r["message"]
    assert compute_acwr_from_loads({}, TODAY, None)["acwr"] is None


def test_acwr_undefined_when_no_chronic_load():
    r = compute_acwr_from_loads({}, TODAY, TODAY - timedelta(days=60))
    assert r["acwr"] is None and "undefined" in r["message"]


def test_rpe_trend_needs_enough_sessions_in_both_windows():
    recent = [(TODAY - timedelta(days=d), 8) for d in (0, 2, 4)]
    base = [(TODAY - timedelta(days=d), 5) for d in (9, 12, 15, 18)]
    r = compute_rpe_trend_from_entries(recent + base, TODAY)
    assert r["rpe_trend"] == 3.0 and r["n_recent"] == 3 and r["n_baseline"] == 4
    assert compute_rpe_trend_from_entries(recent[:2] + base, TODAY) is None
    assert compute_rpe_trend_from_entries(recent + base[:2], TODAY) is None


# ------------------------------------ anomaly ---------------------------------------------

def test_anomaly_calibration_normal_videos_score_low_gross_outliers_score_max():
    from app.modules.risk_scoring.anomaly import assess_video_anomaly
    rng = np.random.default_rng(11)
    names = ["knee_flexion_angle_left", "knee_flexion_angle_right", "trunk_lean_angle"]

    def draw():
        z = rng.normal()
        d = {}
        for n, mu, sd in zip(names, (105, 104, 35), (9, 9, 7)):
            d[f"{n}.p95"] = mu + sd * (0.7 * z + 0.7 * rng.normal())
            d[f"{n}.p05"] = 6 + 3 * rng.normal()
        return d

    base = [draw() for _ in range(25)]
    normal = [assess_video_anomaly(draw(), base, 10)["deviation_score"] for _ in range(12)]
    assert np.median(normal) < 10 and np.mean(np.array(normal) > 50) < 0.2

    bad = draw(); bad["knee_flexion_angle_left.p95"] -= 60; bad["knee_flexion_angle_right.p95"] -= 60
    out = assess_video_anomaly(bad, base, 10)
    assert out["deviation_score"] == 100 and out["flagged"]
    assert out["features"][0]["flagged"] and out["features"][0]["direction"] == "below"


def test_anomaly_refuses_a_too_small_baseline():
    from app.modules.risk_scoring.anomaly import InsufficientBaselineError, assess_video_anomaly
    with pytest.raises(InsufficientBaselineError):
        assess_video_anomaly({"a.p95": 1.0}, [{"a.p95": 1.0}] * 3, 10)


def test_anomaly_baseline_is_exchangeable_not_in_sample_biased():
    """Percentile of a fresh baseline-distributed sample should be ~uniform (mean ~50), not skewed high."""
    from app.modules.risk_scoring.anomaly import compute_anomaly_scores
    rng = np.random.default_rng(5)
    base = rng.normal(0, 1, (40, 3))
    fresh = rng.normal(0, 1, (60, 3))
    pct = np.array(compute_anomaly_scores(fresh, base, 10))
    assert 35 < pct.mean() < 65


# ------------------------------------ injury categories -----------------------------------

def _feat(metric, stat, value, median, z):
    return {"feature": f"{metric}.{stat}", "metric": metric, "stat": stat, "value": value,
            "baseline_median": median, "z": z, "direction": "above" if z > 0 else "below", "flagged": abs(z) >= 2}


def _cats(movement="landing", feats=(), injuries=(), load=None, fatigue=None, asym=None, qual=None):
    comps = {
        "training_load_indicators": Component("training_load_indicators", load, {}),
        "fatigue_indicators": Component("fatigue_indicators", fatigue, {}),
        "movement_asymmetry": Component("movement_asymmetry", asym, {}),
    }
    rows = score_history(list(injuries), movement, TODAY).detail.get("injuries", [])
    return assess_injury_categories(movement_type=movement, anomaly={"features": list(feats)} if feats else None,
                                    injuries=rows, components=comps, qualitative=qual)


def test_all_six_spec_categories_present():
    assert set(_cats()) == {"acl", "hamstring", "ankle_sprain", "shoulder", "lower_back", "overuse"}


def test_acl_uses_video_kinematics_and_history_for_a_landing():
    cats = _cats("landing", feats=[_feat("knee_flexion_angle_left", "p95", 40, 95, -3.2)],
                 injuries=[inj("ACL", 6)], qual={"knee_valgus_deviation_left": 18.0})
    acl = cats["acl"]
    assert acl["level"] in ("high", "critical") and acl["video_kinematics_used"]
    factors = {d["factor"] for d in acl["drivers"]}
    assert {"reduced peak knee flexion", "prior knee injury", "knee valgus flag (qualitative)"} <= factors


def test_acl_ignores_video_for_movements_it_is_not_validated_for():
    cats = _cats("throwing", feats=[_feat("knee_flexion_angle_left", "p95", 40, 95, -3.2)])
    assert not cats["acl"]["video_kinematics_used"]


def test_ankle_hamstring_never_use_video_kinematics():
    cats = _cats("landing", feats=[_feat("knee_flexion_angle_left", "p95", 40, 95, -3.2)], injuries=[inj("ankle"), inj("hamstring")])
    for k in ("ankle_sprain", "hamstring"):
        assert not cats[k]["video_kinematics_used"]
        assert all(d["source"] != "video" or d["factor"].startswith("left/right") for d in cats[k]["drivers"])
    assert cats["ankle_sprain"]["level"] in ("high", "critical")  # unresolved ankle injury dominates


def test_overuse_is_load_and_fatigue_driven():
    assert _cats(load=100, fatigue=100)["overuse"]["level"] == "critical"
    assert _cats(load=0, fatigue=0)["overuse"]["level"] == "low"
    assert _cats()["overuse"]["risk_score"] == 0.0  # no unresolved injury -> a real zero, driver available


def test_category_reports_what_it_is_based_on():
    c = _cats("squatting")["lower_back"]
    assert c["based_on"] == ["history"] and not c["video_kinematics_used"]
    assert all(c["evidence"])


# ------------------------------------ recommendations -------------------------------------

def _assessment(overall=60, breakdown=None, feats=(), cats=None):
    bd = {k: {"available": False, "score": None, "detail": {}} for k in WEIGHTS}
    bd.update(breakdown or {})
    return {"overall_score": overall, "score_breakdown": bd, "anomaly_features": list(feats),
            "injury_categories": cats or {}, "sub_scores": {}}


def test_recommendation_cites_the_specific_flagged_metric_and_value():
    a = _assessment(feats=[_feat("knee_flexion_angle_left", "p95", 62, 101, -3.0)])
    recs = generate_recommendations(a, "landing")
    r = next(r for r in recs if "Soft-landing" in r["title"])
    assert "62°" in r["description"] and "101°" in r["description"] and r["category"] == "exercise"
    assert any(x["category"] == "mobility" for x in recs)


def test_all_five_recommendation_categories_are_reachable():
    a = _assessment(
        breakdown={
            "biomechanical_deviations": {"available": True, "score": 70, "detail": {}},
            "movement_asymmetry": {"available": True, "score": 60, "detail": {"left_peak_deg": 100, "right_peak_deg": 70, "lsi_pct": 70}},
            "training_load_indicators": {"available": True, "score": 70, "detail": {"acwr": 1.7}},
            "fatigue_indicators": {"available": True, "score": 80, "detail": {
                "movement_drift": {"n_reps": 6, "drift_pct": -25, "direction": "decrease"},
                "rpe_trend": {"recent_mean_rpe": 8, "baseline_mean_rpe": 6, "rpe_trend": 2}}},
            "historical_injury_factors": {"available": True, "score": 100, "detail": {"injuries": [
                {"body_part": "knee", "status": "unresolved"}]}},
        },
        feats=[_feat("knee_flexion_angle_left", "p95", 62, 101, -3.0)],
        cats={"hamstring": {"level": "high"}, "acl": {"level": "high"}},
    )
    cats = {r["category"] for r in generate_recommendations(a, "squatting")}
    # truncated to the 8 highest-priority; across the full pool every category is produced
    assert cats <= {"exercise", "mobility", "strengthening", "recovery", "training_modification"}
    from app.modules.recommendations import rules
    old = rules.MAX_RECOMMENDATIONS
    rules.MAX_RECOMMENDATIONS = 50
    try:
        full = {r["category"] for r in generate_recommendations(a, "squatting")}
    finally:
        rules.MAX_RECOMMENDATIONS = old
    assert full == {"exercise", "mobility", "strengthening", "recovery", "training_modification"}


def test_unresolved_injury_is_the_top_priority():
    a = _assessment(breakdown={"historical_injury_factors": {"available": True, "score": 100, "detail": {
        "injuries": [{"body_part": "hamstring", "status": "unresolved"}]}}})
    recs = generate_recommendations(a, "running")
    assert recs[0]["priority"] == 1 and "physiotherapist" in recs[0]["title"].lower()


def test_nothing_flagged_gives_an_honest_maintenance_note_not_filler():
    recs = generate_recommendations(_assessment(overall=5), "squatting")
    assert len(recs) == 1 and recs[0]["priority"] == 5 and "No deviations" in recs[0]["title"]


def test_recommendations_are_ordered_unique_and_bounded():
    a = _assessment(feats=[_feat("knee_flexion_angle_left", "p95", 62, 101, -3.0), _feat("trunk_lean_angle", "p95", 60, 35, 3.5)])
    recs = generate_recommendations(a, "squatting")
    assert [r["priority"] for r in recs] == sorted(r["priority"] for r in recs)
    assert len({r["title"] for r in recs}) == len(recs) <= 8
    assert all(1 <= r["priority"] <= 5 and r["description"] for r in recs)
