import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.risk_scoring_engine import RiskScoringEngine

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_datasets():
    response = client.get("/api/datasets")
    assert response.status_code == 200
    data = response.json()
    assert data["total_datasets"] >= 5
    assert "normative_benchmarks" in data

def test_auth_login():
    # Login with seeded athlete
    response = client.post("/api/auth/login", json={
        "email": "athlete@sportsai.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "athlete"

def test_athletes_list():
    response = client.get("/api/athletes")
    assert response.status_code == 200
    athletes = response.json()
    assert len(athletes) >= 5
    assert any(a["athlete_code"] == "ATH-101" for a in athletes)

def test_weighted_scoring_formula():
    engine = RiskScoringEngine()
    biomechanics = {
        "knee_valgus_left_max": 16.5,
        "knee_valgus_right_max": 18.0,
        "trunk_lean_lateral_max": 12.0,
        "landing_mechanics_score": 45.0,
        "movement_symmetry_score": 75.0
    }
    athlete_profile = {
        "acwr": 1.45,
        "training_load": 18.0,
        "injury_history": [{"injury_name": "ACL Tear", "severity": "Surgical", "status": "Vulnerable"}]
    }
    scores = engine.compute_scores(biomechanics, athlete_profile, fatigue_drift_pct=22.0)
    
    # Check weighted formula sum:
    # 0.35 * dev + 0.20 * hist + 0.20 * asym + 0.15 * load + 0.10 * fatigue
    expected = (
        0.35 * scores["biomechanical_deviation_score"] +
        0.20 * scores["historical_injury_factor_score"] +
        0.20 * scores["movement_asymmetry_score"] +
        0.15 * scores["training_load_indicator_score"] +
        0.10 * scores["fatigue_indicator_score"]
    )
    assert abs(scores["overall_injury_risk_score"] - round(expected, 1)) < 0.2
    assert scores["risk_category"] in ["High Risk", "Critical Risk"]

def test_dashboards():
    coach_res = client.get("/api/dashboards/coach")
    assert coach_res.status_code == 200
    coach_data = coach_res.json()
    assert "summary" in coach_data
    assert "roster" in coach_data

    physio_res = client.get("/api/dashboards/physiotherapist")
    assert physio_res.status_code == 200
    physio_data = physio_res.json()
    assert "rehab_registry" in physio_data

    scientist_res = client.get("/api/dashboards/sports_scientist")
    assert scientist_res.status_code == 200
    scientist_data = scientist_res.json()
    assert "scientific_overview" in scientist_data
