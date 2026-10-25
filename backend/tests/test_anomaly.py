import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.anomaly_service import anomaly_service
from app.schemas.anomaly import AnomalyDetectionResponse

client = TestClient(app)

@patch("app.services.anomaly_service.generate_biomechanics_analysis")
def test_detect_anomalies(mock_analysis):
    # Mocking analysis output
    mock_analysis.return_value = {
        "video_id": 1,
        "metrics_over_time": [
            {
                "timestamp_ms": 0,
                "left_knee_angle": 150,
                "right_knee_angle": 150,
                "trunk_lean": 10,
                "quality_flag": "OK"
            },
            {
                # Normal movement
                "timestamp_ms": 33,
                "left_knee_angle": 140,
                "right_knee_angle": 140,
                "trunk_lean": 12,
                "quality_flag": "OK"
            },
            {
                # Injected abnormal value (Jitter/Variability) -> Delta 60 > 45
                "timestamp_ms": 66,
                "left_knee_angle": 80,
                "right_knee_angle": 140,
                "trunk_lean": 10,
                "quality_flag": "OK"
            },
            {
                # Asymmetry -> diff 40 > 25
                "timestamp_ms": 99,
                "left_knee_angle": 140,
                "right_knee_angle": 100,
                "trunk_lean": 10,
                "quality_flag": "OK"
            },
            {
                # Trunk lean -> 40 > 30
                "timestamp_ms": 133,
                "left_knee_angle": 140,
                "right_knee_angle": 140,
                "trunk_lean": 40,
                "quality_flag": "OK"
            },
            {
                # Quality flag (missing landmark)
                "timestamp_ms": 166,
                "left_knee_angle": None,
                "right_knee_angle": None,
                "trunk_lean": None,
                "quality_flag": "MISSING_LANDMARKS"
            }
        ]
    }
    
    # Testing the service logic directly
    response = anomaly_service.detect_anomalies(db=None, video_id=1)
    
    assert response.video_id == 1
    assert response.total_anomalies == 6
    
    metrics_flagged = [e.metric for e in response.events]
    assert "movement_variability" in metrics_flagged
    assert "knee_asymmetry" in metrics_flagged
    assert "trunk_lean" in metrics_flagged
    assert "data_quality" in metrics_flagged
    
    # Check disclaimers
    assert "do NOT directly detect fatigue or injury" in response.disclaimer

@patch("app.api.endpoints.anomaly.anomaly_service.detect_anomalies")
def test_anomaly_api(mock_detect):
    mock_detect.return_value = AnomalyDetectionResponse(
        video_id=1,
        total_anomalies=1,
        events=[{
            "timestamp_ms": 0,
            "metric": "trunk_lean",
            "observed_value": 35.0,
            "reference_rule": "<= 30.0",
            "severity": "medium",
            "explanation": "Lean too far",
            "is_data_quality_issue": False
        }]
    )
    
    res = client.get("/api/v1/anomaly/1")
    assert res.status_code == 200
    assert res.json()["total_anomalies"] == 1
    assert res.json()["events"][0]["metric"] == "trunk_lean"
