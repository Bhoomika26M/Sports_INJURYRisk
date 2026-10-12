import pytest
import os
import tempfile
from io import BytesIO
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import Base, get_db
from app.models.user import User
from app.models.athlete import Athlete
from app.models.video import Video
from app.core.security import create_access_token


# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_video.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    return TestClient(app)


@pytest.fixture
def test_user(db):
    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password",
        role="athlete",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_athlete(db, test_user):
    athlete = Athlete(
        athlete_id="ATH001",
        user_id=test_user.id,
        sport_type="running",
        position="forward",
        age=25,
        height=175.0,
        weight=70.0
    )
    db.add(athlete)
    db.commit()
    db.refresh(athlete)
    return athlete


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}


def test_upload_video_success(client, test_athlete, auth_headers):
    """Test successful video upload."""
    # Create a dummy video file
    video_content = b"fake video content"
    video_file = BytesIO(video_content)
    video_file.name = "test_video.mp4"
    
    response = client.post(
        "/api/v1/videos",
        headers=auth_headers,
        data={
            "athlete_id": test_athlete.id,
            "activity_type": "squat"
        },
        files={"video": ("test_video.mp4", video_file, "video/mp4")}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["athlete_id"] == test_athlete.id
    assert data["activity_type"] == "squat"
    assert data["processing_status"] == "uploaded"
    assert "id" in data


def test_upload_video_unauthorized_athlete(client, db, auth_headers):
    """Test that athletes cannot upload for other athletes."""
    # Create another athlete not linked to the user
    other_user = User(
        email="other@example.com",
        full_name="Other User",
        hashed_password="hashed_password",
        role="athlete",
        is_active=True
    )
    db.add(other_user)
    db.commit()
    
    other_athlete = Athlete(
        athlete_id="ATH002",
        user_id=other_user.id,
        sport_type="running",
        position="forward",
        age=25,
        height=175.0,
        weight=70.0
    )
    db.add(other_athlete)
    db.commit()
    
    video_content = b"fake video content"
    video_file = BytesIO(video_content)
    video_file.name = "test_video.mp4"
    
    response = client.post(
        "/api/v1/videos",
        headers=auth_headers,
        data={
            "athlete_id": other_athlete.id,
            "activity_type": "squat"
        },
        files={"video": ("test_video.mp4", video_file, "video/mp4")}
    )
    
    assert response.status_code == 403


def test_upload_video_invalid_format(client, test_athlete, auth_headers):
    """Test that invalid file formats are rejected."""
    video_content = b"fake content"
    video_file = BytesIO(video_content)
    video_file.name = "test.txt"
    
    response = client.post(
        "/api/v1/videos",
        headers=auth_headers,
        data={
            "athlete_id": test_athlete.id,
            "activity_type": "squat"
        },
        files={"video": ("test.txt", video_file, "text/plain")}
    )
    
    assert response.status_code == 400


def test_get_video(client, test_athlete, auth_headers, db):
    """Test getting video details."""
    # First upload a video
    video_content = b"fake video content"
    video_file = BytesIO(video_content)
    video_file.name = "test_video.mp4"
    
    upload_response = client.post(
        "/api/v1/videos",
        headers=auth_headers,
        data={
            "athlete_id": test_athlete.id,
            "activity_type": "squat"
        },
        files={"video": ("test_video.mp4", video_file, "video/mp4")}
    )
    
    video_id = upload_response.json()["id"]
    
    # Get the video
    response = client.get(f"/api/v1/videos/{video_id}", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == video_id


def test_get_video_unauthorized(client, db, auth_headers):
    """Test IDOR protection - users cannot access other users' videos."""
    # Create another user and athlete
    other_user = User(
        email="other@example.com",
        full_name="Other User",
        hashed_password="hashed_password",
        role="athlete",
        is_active=True
    )
    db.add(other_user)
    db.commit()
    
    other_athlete = Athlete(
        athlete_id="ATH002",
        user_id=other_user.id,
        sport_type="running",
        position="forward",
        age=25,
        height=175.0,
        weight=70.0
    )
    db.add(other_athlete)
    db.commit()
    
    # Upload video as other user
    other_token = create_access_token(data={"sub": other_user.email})
    other_headers = {"Authorization": f"Bearer {other_token}"}
    
    video_content = b"fake video content"
    video_file = BytesIO(video_content)
    video_file.name = "test_video.mp4"
    
    upload_response = client.post(
        "/api/v1/videos",
        headers=other_headers,
        data={
            "athlete_id": other_athlete.id,
            "activity_type": "squat"
        },
        files={"video": ("test_video.mp4", video_file, "video/mp4")}
    )
    
    video_id = upload_response.json()["id"]
    
    # Try to access with original user (should fail)
    response = client.get(f"/api/v1/videos/{video_id}", headers=auth_headers)
    
    assert response.status_code == 403


def test_list_videos(client, test_athlete, auth_headers):
    """Test listing videos."""
    response = client.get("/api/v1/videos", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
