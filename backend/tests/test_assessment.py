import pytest
from app.services.assessment_service import evaluate_movement

def test_evaluate_movement_unsupported():
    res = evaluate_movement({}, "swimming")
    assert res["status"] == "unsupported"

def test_evaluate_movement_limited():
    res = evaluate_movement({}, "throwing")
    assert res["status"] == "limited"

def test_evaluate_movement_insufficient_data():
    res = evaluate_movement({"metrics_over_time": []}, "squatting")
    assert res["status"] == "insufficient_data"

def test_evaluate_movement_squatting_normal():
    data = {
        "metrics_over_time": [
            {"quality_flag": "OK", "left_knee_angle": 90, "right_knee_angle": 92, "trunk_lean": 10},
            {"quality_flag": "OK", "left_knee_angle": 85, "right_knee_angle": 83, "trunk_lean": 12},
        ]
    }
    res = evaluate_movement(data, "squatting")
    assert res["status"] == "success"
    assert len(res["flags"]) == 0
    assert "Knee flexion symmetry is within normal ranges" in res["summary"]

def test_evaluate_movement_squatting_flagged():
    data = {
        "metrics_over_time": [
            {"quality_flag": "OK", "left_knee_angle": 90, "right_knee_angle": 120, "trunk_lean": 30},
        ]
    }
    res = evaluate_movement(data, "squatting")
    assert res["status"] == "success"
    assert len(res["flags"]) == 2
    assert any("Asymmetrical knee flexion" in f for f in res["flags"])
    assert any("Excessive forward trunk lean" in f for f in res["flags"])
