import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.models.user import User
from app.models.athlete import AthleteProfile
from app.models.video import Video
from app.services.processing_service import process_video_pipeline

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_database():
    from app.db.session import SessionLocal
    db = SessionLocal()
    
    user = User(email="assessor@example.com", hashed_password="hashed_password", full_name="Assessor", role="athlete", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    profile = AthleteProfile(user_id=user.id, sport_type="Running")
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    # We will copy sample.mp4 to create a real processing case
    sample_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample.mp4")
    upload_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    import shutil
    dest_path = os.path.join(upload_dir, "test_assessment_sample.mp4")
    shutil.copy(sample_path, dest_path)
    
    video = Video(
        athlete_id=profile.id,
        uploader_id=user.id,
        filename="test_assessment_sample.mp4",
        original_filename="sample.mp4",
        file_path=dest_path,
        format="mp4",
        size_bytes=os.path.getsize(dest_path),
        status="uploaded"
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    
    # Process the video synchronously
    process_video_pipeline(db, video.id)
    
    yield {"user_id": user.id, "athlete_id": profile.id, "video_id": video.id}
    
    db.close()

def test_assessment_endpoint(setup_database):
    db_data = setup_database
    access_token = create_access_token(subject=db_data["user_id"])
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = client.get(f"/api/v1/assessment/{db_data['video_id']}?activity=running", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["activity"] == "running"
    assert data["status"] == "success"
    assert "summary" in data
    assert isinstance(data["flags"], list)
    assert isinstance(data["warnings"], list)
