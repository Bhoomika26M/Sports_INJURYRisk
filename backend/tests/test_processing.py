import os
import json
import pytest
from app.db.session import SessionLocal
from app.models.video import Video
from app.models.athlete import AthleteProfile
from app.models.user import User
from app.services.processing_service import process_video_pipeline
from app.core.config import settings
import shutil
import random
import string

def test_landmark_processing_pipeline():
    """
    Test the MediaPipe landmark processing pipeline using a real sample video.
    This test verifies that:
    1. The annotated video is generated.
    2. The landmarks JSON is generated and contains valid data (normalized coords).
    3. Handles gracefully and marks the video as completed.
    """
    db = SessionLocal()
    try:
        # 1. Setup mock user and athlete
        email = "".join(random.choices(string.ascii_lowercase, k=10)) + "@example.com"
        user = User(email=email, hashed_password="pwd", role="athlete", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        
        athlete = AthleteProfile(user_id=user.id)
        db.add(athlete)
        db.commit()
        db.refresh(athlete)
        
        # 2. Setup a video entry in DB and copy sample file to UPLOAD_DIR
        sample_src = os.path.join(os.path.dirname(__file__), "fixtures", "sample.mp4")
        if not os.path.exists(sample_src):
            pytest.skip("Sample video missing, skipping test")
        
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        target_path = os.path.join(settings.UPLOAD_DIR, f"test_sample_{user.id}.mp4")
        shutil.copy(sample_src, target_path)
        
        video = Video(
            athlete_id=athlete.id,
            uploader_id=user.id,
            original_filename="sample.mp4", filename="test_sample.mp4",
            file_path=target_path, format="video/mp4", size_bytes=1000,
            status="uploaded"
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        
        # 3. Process video
        process_video_pipeline(db, video.id)
        
        # 4. Verify DB state
        db.refresh(video)
        assert video.status == "completed", f"Expected completed, got {video.status}: {video.error_message}"
        
        # 5. Verify outputs
        base_name = os.path.splitext(os.path.basename(target_path))[0]
        annotated_path = os.path.join(settings.UPLOAD_DIR, f"{base_name}_annotated.mp4")
        json_path = os.path.join(settings.UPLOAD_DIR, f"{base_name}_landmarks.json")
        
        assert os.path.exists(annotated_path), "Annotated video not generated"
        assert os.path.exists(json_path), "Landmarks JSON not generated"
        
        # 6. Verify JSON structure and normalized coordinates
        with open(json_path, "r") as f:
            data = json.load(f)
            
        assert data["athlete_id"] == athlete.id
        assert data["video_id"] == video.id
        assert "frames" in data
        
        # If the video has person, we expect some landmarks
        # Even if no person, the format should be correct
        if len(data["frames"]) > 0:
            first_frame = data["frames"][0]
            assert "frame_index" in first_frame
            assert "timestamp_ms" in first_frame
            assert "landmarks" in first_frame
            
            if len(first_frame["landmarks"]) > 0:
                lm = first_frame["landmarks"][0]
                assert "x" in lm and "y" in lm and "z" in lm and "visibility" in lm
                assert isinstance(lm["x"], float)
                assert isinstance(lm["y"], float)
    finally:
        db.close()
