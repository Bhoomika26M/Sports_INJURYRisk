import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.db.session import Base
import random
import string

client = TestClient(app)

def random_email():
    return "".join(random.choices(string.ascii_lowercase, k=10)) + "@example.com"

def create_athlete_and_profile():
    email = random_email()
    password = "pass"
    client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Test Athlete"})
    login_resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = login_resp.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/api/v1/athletes/me", json={"sport_type": "Soccer", "age": 22}, headers=headers)
    profile_id = resp.json()["id"]
    return profile_id, token, headers

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

@patch("app.services.video_service.extract_video_metadata")
def test_valid_video_upload(mock_extract):
    mock_extract.return_value = (30.0, 1920, 1080, 10.5) # fps, w, h, duration
    
    profile_id, token, headers = create_athlete_and_profile()
    
    # Create a dummy file
    dummy_file = b"fake video content"
    files = {"file": ("test_video.mp4", dummy_file, "video/mp4")}
    data = {"athlete_id": profile_id}
    
    response = client.post("/api/v1/videos/", files=files, data=data, headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["filename"].endswith(".mp4")
    assert res_data["duration_sec"] == 10.5
    assert res_data["size_bytes"] == len(dummy_file)
    assert res_data["status"] == "uploaded"

def test_invalid_video_extension():
    profile_id, token, headers = create_athlete_and_profile()
    
    dummy_file = b"fake text content"
    files = {"file": ("test_doc.pdf", dummy_file, "application/pdf")}
    data = {"athlete_id": profile_id}
    
    response = client.post("/api/v1/videos/", files=files, data=data, headers=headers)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

def test_unauthorized_athlete_access():
    # Athlete 1
    profile_id_1, token_1, headers_1 = create_athlete_and_profile()
    # Athlete 2
    profile_id_2, token_2, headers_2 = create_athlete_and_profile()
    
    # Athlete 2 tries to upload for Athlete 1
    dummy_file = b"fake video content"
    files = {"file": ("test_video.mp4", dummy_file, "video/mp4")}
    data = {"athlete_id": profile_id_1}
    
    response = client.post("/api/v1/videos/", files=files, data=data, headers=headers_2)
    assert response.status_code == 403
    assert "Athletes can only upload videos for their own profile" in response.json()["detail"]

@patch("app.services.video_service.extract_video_metadata")
def test_video_upload_with_movement_type_and_status(mock_extract):
    mock_extract.return_value = (30.0, 1280, 720, 8.0)
    profile_id, token, headers = create_athlete_and_profile()

    dummy_file = b"sample video binary stream"
    files = {"file": ("sprint_trial.mp4", dummy_file, "video/mp4")}
    data = {"athlete_id": profile_id, "movement_type": "sprinting"}

    response = client.post("/api/v1/videos/", files=files, data=data, headers=headers)
    assert response.status_code == 200
    video_id = response.json()["id"]
    assert response.json()["movement_type"] == "sprinting"

    # Test status polling endpoint
    status_resp = client.get(f"/api/v1/videos/{video_id}/status", headers=headers)
    assert status_resp.status_code == 200
    assert "processing_progress" in status_resp.json()
    assert "status" in status_resp.json()

    # Test single video details
    get_resp = client.get(f"/api/v1/videos/{video_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == video_id

    # Test delete video
    del_resp = client.delete(f"/api/v1/videos/{video_id}", headers=headers)
    assert del_resp.status_code == 200
    assert "successfully deleted" in del_resp.json()["message"]

@patch("app.services.video_service.extract_video_metadata")
def test_video_too_short_validation(mock_extract):
    mock_extract.return_value = (30.0, 1280, 720, 0.2)
    profile_id, token, headers = create_athlete_and_profile()

    dummy_file = b"short stream"
    files = {"file": ("short.mp4", dummy_file, "video/mp4")}
    data = {"athlete_id": profile_id}

    response = client.post("/api/v1/videos/", files=files, data=data, headers=headers)
    assert response.status_code == 400
    assert "too short" in response.json()["detail"]
