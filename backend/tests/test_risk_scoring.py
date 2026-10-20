import json
from datetime import date, timedelta

from app.services.analysis_pipeline import analyze_pose
from app.services.anomaly_detection import fatigue_trend, severity_fraction
from app.services.risk_scoring import (
    WEIGHTS,
    categorize,
    compute_load_stats,
    compute_risk_score,
    historical_injury_score,
    training_load_score,
)
from tests.synthetic import make_sequence


def test_weights_match_spec_and_sum_to_one():
    assert WEIGHTS == {
        "biomechanical_deviations": 0.35,
        "historical_injury": 0.20,
        "movement_asymmetry": 0.20,
        "training_load": 0.15,
        "fatigue": 0.10,
    }
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def test_weighted_score_matches_hand_calculation():
    comps = {
        "biomechanical_deviations": 80, "historical_injury": 50, "movement_asymmetry": 40,
        "training_load": 20, "fatigue": 10,
    }
    expected = 0.35 * 80 + 0.20 * 50 + 0.20 * 40 + 0.15 * 20 + 0.10 * 10
    assert abs(compute_risk_score(comps)["score"] - round(expected, 1)) < 0.05


def test_missing_components_renormalise_weights():
    result = compute_risk_score({
        "biomechanical_deviations": 60, "historical_injury": 0, "movement_asymmetry": None,
        "training_load": None, "fatigue": None,
    })
    assert result["missing_components"] == ["movement_asymmetry", "training_load", "fatigue"]
    assert abs(sum(result["weights_used"].values()) - 1.0) < 0.01
    assert abs(result["score"] - 60 * 0.35 / 0.55) < 0.1


def test_categories():
    assert categorize(10) == "low"
    assert categorize(30) == "moderate"
    assert categorize(60) == "high"
    assert categorize(80) == "critical"


def test_severity_fraction_directions():
    assert severity_fraction(3, 5, 8, 12) == 0
    assert abs(severity_fraction(8, 5, 8, 12) - 0.4) < 1e-9
    assert abs(severity_fraction(12, 5, 8, 12) - 0.8) < 1e-9
    # lower is worse: landing knee flexion
    assert severity_fraction(40, 35, 25, 15, "low") == 0
    assert abs(severity_fraction(15, 35, 25, 15, "low") - 0.8) < 1e-9


def test_recent_severe_injury_raises_history_score():
    today = date(2026, 1, 1)
    recent = [{"severity": "severe", "status": "recovered", "injury_date": today - timedelta(days=60)}]
    old = [{"severity": "severe", "status": "recovered", "injury_date": today - timedelta(days=1500)}]
    assert historical_injury_score(recent, today) > historical_injury_score(old, today) + 20
    assert historical_injury_score([], today) == 0


def test_acwr_needs_history_and_spikes_score_higher():
    today = date(2026, 3, 1)
    assert compute_load_stats([{"entry_date": today, "load_au": 300}], today) is None  # too little history

    steady = [{"entry_date": today - timedelta(days=d), "load_au": 300} for d in range(0, 28, 2)]
    spike = steady + [{"entry_date": today - timedelta(days=d), "load_au": 900} for d in range(0, 6)]
    s1, s2 = compute_load_stats(steady, today), compute_load_stats(spike, today)
    assert s2["acwr"] > s1["acwr"]
    assert training_load_score(s2) > training_load_score(s1)


def test_fatigue_trend_detects_drift():
    drifting = {"peak_knee_flexion": [100, 95, 88, 80, 70], "peak_valgus": [4, 6, 8, 10, 12], "trunk_lean": [10, 12, 15, 18, 20]}
    stable = {"peak_knee_flexion": [100, 100, 99, 100, 100], "peak_valgus": [5, 5, 5, 5, 5], "trunk_lean": [10, 10, 10, 10, 10]}
    assert fatigue_trend(drifting)["fatigue_index"] > 0.7
    assert fatigue_trend(stable)["fatigue_index"] < 0.1
    assert fatigue_trend({"peak_knee_flexion": [100, 90]}) is None


def test_full_pipeline_orders_risk_sensibly():
    good = analyze_pose(make_sequence(), 30, "squatting", 180, 75)
    bad = analyze_pose(
        make_sequence(valgus_offset=0.05, pelvic_drop=0.04, left_rom_scale=0.4, fatigue_drift=0.5), 30, "squatting", 180, 75,
        injuries=[{"body_part": "knee", "injury_type": "ACL tear", "severity": "severe", "status": "recovering", "injury_date": date.today()}],
    )
    assert bad["risk_score"] > good["risk_score"] + 15
    assert bad["movement_quality"] < good["movement_quality"]
    assert bad["injury_risks"][0]["category"] == "ACL injury"
    assert bad["recommendations"]["clinical_referral_suggested"] in (True, False)
    assert any(c["issue"] == "knee_valgus" for c in bad["recommendations"]["corrective_exercises"])
    json.dumps(bad)  # everything must be storable as JSON
