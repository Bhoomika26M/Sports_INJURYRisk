import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_athletes():
    response = client.get("/athletes/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_create_and_get_athlete():
    import uuid
    ath_id = f"ATH-{uuid.uuid4().hex[:6].upper()}"
    
    payload = {
        "athlete_id": ath_id,
        "sport_type": "Basketball",
        "position": "Forward",
        "age": 21,
        "height": 196.0,
        "weight": 92.0,
        "injury_history": "None",
        "training_load": 72.0
    }
    create_res = client.post("/athletes/", json=payload)
    assert create_res.status_code == 200

    get_res = client.get(f"/athletes/{ath_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["athlete_id"] == ath_id
    assert data["sport_type"] == "Basketball"
