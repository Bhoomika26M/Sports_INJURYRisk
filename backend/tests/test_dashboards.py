import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_coach_dashboard():
    response = client.get("/dashboard/coach")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "roster" in data
    assert data["summary"]["total_athletes"] >= 1
    assert "squad_health_score" in data["summary"]


def test_physio_dashboard():
    response = client.get("/dashboard/physio")
    assert response.status_code == 200
    data = response.json()
    assert "rehab_cases" in data
    assert "injury_breakdown" in data
    assert "corrective_protocols" in data


def test_sports_scientist_dashboard():
    response = client.get("/dashboard/sports-scientist")
    assert response.status_code == 200
    data = response.json()
    assert "kinematic_benchmarks" in data
    assert "risk_correlations" in data
    assert "ml_model_accuracy" in data


def test_admin_dashboard():
    response = client.get("/dashboard/admin")
    assert response.status_code == 200
    data = response.json()
    assert "platform_stats" in data
    assert "system_health" in data


def test_notifications_endpoints():
    get_res = client.get("/notifications/")
    assert get_res.status_code == 200
    notifs = get_res.json()
    assert len(notifs) >= 1

    post_res = client.post("/notifications/", json={
        "severity": "WARNING",
        "category": "TRAINING_OVERLOAD",
        "title": "Test Overload Alert",
        "message": "Testing real-time notification engine"
    })
    assert post_res.status_code == 200
    created = post_res.json()
    assert created["title"] == "Test Overload Alert"


def test_reports_endpoints():
    get_res = client.get("/reports/")
    assert get_res.status_code == 200
    assert len(get_res.json()) >= 1

    csv_res = client.get("/reports/export/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
