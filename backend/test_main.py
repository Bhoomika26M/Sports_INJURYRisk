import pytest
from fastapi.testclient import TestClient
from main import app
from database import Base, engine, SessionLocal
import models
import auth
import uuid
from unittest.mock import patch

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Create a test user
    hashed_password = auth.get_password_hash("testpassword")
    user = models.User(email="test@example.com", hashed_password=hashed_password, role="Athlete")
    db.add(user)
    db.commit()
    yield
    # Teardown
    db.query(models.User).filter(models.User.email == "test@example.com").delete()
    db.commit()
    db.close()

def test_register_user(setup_database):
    unique_email = f"newuser_{uuid.uuid4()}@example.com"
    response = client.post("/register", json={
        "email": unique_email,
        "password": "newpassword",
        "role": "Athlete"
    })
    assert response.status_code == 200
    assert response.json()["email"] == unique_email

def test_login_user(setup_database):
    response = client.post("/token", data={
        "username": "test@example.com",
        "password": "testpassword"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_get_me(setup_database):
    # First login to get token
    login_res = client.post("/token", data={
        "username": "test@example.com",
        "password": "testpassword"
    })
    token = login_res.json()["access_token"]
    
    # Then get me
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

@patch("main.process_video_with_mediapipe")
def test_upload_video(mock_process, setup_database):
    mock_process.return_value = {
        "filename": "mock.mp4",
        "analytics": {
            "activity_analyzed": "Unknown",
            "surface_type": "Unknown",
            "footwear": "Unknown",
            "rpe": 5,
            "sleep_quality": 5,
            "risk_score": 10,
            "risk_level": "Low",
            "risk_flags": [],
            "injury_probabilities": {"ACL Injury": 10},
            "corrective_recommendation": "Good"
        }
    }
    
    login_res = client.post("/token", data={
        "username": "test@example.com",
        "password": "testpassword"
    })
    token = login_res.json()["access_token"]

    # We mock a small file upload
    files = {'file': ('test.mp4', b'dummy content', 'video/mp4')}
    response = client.post("/video/upload", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert response.status_code == 200
    assert "message" in response.json()

def test_get_analyses(setup_database):
    login_res = client.post("/token", data={
        "username": "test@example.com",
        "password": "testpassword"
    })
    token = login_res.json()["access_token"]

    response = client.get("/athlete/analyses", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
