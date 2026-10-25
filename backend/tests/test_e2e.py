import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
import random
import string

client = TestClient(app)

def random_email():
    return "".join(random.choices(string.ascii_lowercase, k=10)) + "@example.com"

def test_e2e_flow():
    # 1. Authenticate
    email = random_email()
    password = "securepassword"
    
    resp = client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "E2E Athlete", "role": "athlete"})
    assert resp.status_code == 200
    
    login_resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Athlete Profile Creation
    profile_data = {
        "sport_type": "Soccer",
        "age": 25,
        "height_cm": 180.0,
        "weight_kg": 75.0,
        "injury_history": [],
        "training_load": {"sessions_per_week": 5}
    }
    
    resp = client.post("/api/v1/athletes/me", json=profile_data, headers=headers)
    assert resp.status_code == 200
    profile_id = resp.json()["id"]
    
    # Check Dashboard Before Upload
    resp = client.get("/api/v1/dashboard/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["video_count"] == 0
    
    # 3. Video Upload (Mocking extract_video_metadata and process_and_save_upload)
    with patch("app.services.video_service.extract_video_metadata") as mock_extract:
        mock_extract.return_value = (30.0, 1920, 1080, 5.0)
        
        with patch("app.api.endpoints.videos.process_video_bg"):
            dummy_file = b"fake video content"
            files = {"file": ("test_video.mp4", dummy_file, "video/mp4")}
            data = {"athlete_id": profile_id}
            
            resp = client.post("/api/v1/videos/", files=files, data=data, headers=headers)
            assert resp.status_code == 200
            
            video_id = resp.json()["id"]
            
    # Mark video as completed so dashboard picks it up
    from app.db.session import SessionLocal
    from app.models.video import Video
    db = SessionLocal()
    video = db.query(Video).filter(Video.id == video_id).first()
    video.status = "completed"
    db.commit()
    db.close()
    
    # Mock the analysis and anomaly services for the dashboard
    with patch("app.api.endpoints.dashboard.analysis_service.generate_biomechanics_analysis") as mock_analysis:
        mock_analysis.return_value = {"aggregates": {"max_trunk_lean": 15, "symmetry_index": 5}}
        
        with patch("app.api.endpoints.dashboard.anomaly_service.detect_anomalies") as mock_anomaly:
            from app.schemas.anomaly import AnomalyDetectionResponse, AnomalyEvent
            mock_anomaly.return_value = AnomalyDetectionResponse(
                video_id=video_id,
                total_anomalies=1,
                events=[AnomalyEvent(frame_index=1, timestamp_ms=33, metric="test", observed_value=1.0, reference_rule="<2", severity="High", explanation="test")]
            )
            
            with patch("app.api.endpoints.dashboard.recommendation_service.generate_recommendations") as mock_rec:
                from app.schemas.recommendation import RecommendationResponse
                mock_rec.return_value = RecommendationResponse(video_id=video_id, recommendations=[])
                
                # 4. Check Dashboard After Upload
                resp = client.get("/api/v1/dashboard/me", headers=headers)
                assert resp.status_code == 200
                data = resp.json()
                
                assert data["video_count"] == 1
                assert data["latest_analysis"] is not None
                assert "risk_score" in data
                assert len(data["anomalies"]) == 1
                assert data["anomalies"][0]["severity"] == "High"
