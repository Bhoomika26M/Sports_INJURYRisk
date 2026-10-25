import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.dataset_service import dataset_service
from app.services.assessment_service import evaluate_movement

client = TestClient(app)

def test_list_datasets():
    response = client.get("/api/v1/datasets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    ids = {d["id"] for d in data}
    assert ids == {"human36m", "mpii", "coco", "sportspose", "fifa_reference"}

def test_get_fifa_risk_factors():
    response = client.get("/api/v1/datasets/fifa/risk-factors")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "fifa_reference"
    assert "knee_valgus" in data["risk_factors"]
    assert "trunk_lean" in data["risk_factors"]
    assert "limb_symmetry_index" in data["risk_factors"]

def test_get_individual_dataset():
    response = client.get("/api/v1/datasets/human36m")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "human36m"
    assert "Human3.6M" in data["name"]
    assert data["keypoint_count"] == 17

def test_get_dataset_sample():
    for ds_id in ["coco", "mpii", "human36m", "sportspose", "fifa_reference"]:
        response = client.get(f"/api/v1/datasets/{ds_id}/sample")
        assert response.status_code == 200, f"Failed for {ds_id}"
        sample = response.json()
        assert sample is not None

def test_convert_coco_and_analyze():
    sample = dataset_service.get_dataset_sample("coco")
    response = client.post("/api/v1/datasets/convert?dataset_id=coco", json=sample)
    assert response.status_code == 200
    res = response.json()
    assert res["dataset_id"] == "coco"
    assert res["converted_landmarks_count"] == 17
    assert "biomechanics" in res
    assert "fifa_evaluation" in res
    assert res["fifa_evaluation"]["clinical_reference"].startswith("FIFA")

def test_convert_mpii_and_analyze():
    sample = dataset_service.get_dataset_sample("mpii")
    response = client.post("/api/v1/datasets/convert?dataset_id=mpii", json=sample)
    assert response.status_code == 200
    res = response.json()
    assert res["dataset_id"] == "mpii"
    assert res["converted_landmarks_count"] == 16
    assert "biomechanics" in res
    assert "fifa_evaluation" in res

def test_convert_human36m_and_analyze():
    sample = dataset_service.get_dataset_sample("human36m")
    response = client.post("/api/v1/datasets/convert?dataset_id=human36m", json=sample)
    assert response.status_code == 200
    res = response.json()
    assert res["dataset_id"] == "human36m"
    assert res["converted_landmarks_count"] == 17
    assert "biomechanics" in res
    assert "fifa_evaluation" in res

def test_convert_sportspose_and_analyze():
    sample = dataset_service.get_dataset_sample("sportspose")
    response = client.post("/api/v1/datasets/convert?dataset_id=sportspose", json=sample)
    assert response.status_code == 200
    res = response.json()
    assert res["dataset_id"] == "sportspose"
    assert res["converted_landmarks_count"] > 10
    assert "biomechanics" in res
    assert "fifa_evaluation" in res

def test_convert_invalid_dataset():
    response = client.post("/api/v1/datasets/convert?dataset_id=unknown_dataset", json={})
    assert response.status_code == 400

def test_assessment_service_fifa_integration():
    mock_analysis = {
        "metrics_over_time": [
            {
                "timestamp_ms": 100,
                "quality_flag": "OK",
                "left_knee_angle": 120.0,
                "right_knee_angle": 122.0,
                "trunk_lean": 12.0
            },
            {
                "timestamp_ms": 200,
                "quality_flag": "OK",
                "left_knee_angle": 110.0,
                "right_knee_angle": 111.0,
                "trunk_lean": 14.0
            }
        ]
    }
    result = evaluate_movement(mock_analysis, "squatting")
    assert result["status"] == "success"
    assert "FIFA" in result["clinical_reference"]
    assert "fifa_benchmarks" in result
    assert "knee_symmetry" in result["fifa_benchmarks"]
    assert result["fifa_benchmarks"]["knee_symmetry"]["status"] == "NORMAL"
