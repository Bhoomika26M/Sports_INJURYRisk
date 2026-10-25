import os
import json
from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.session import get_db, SessionLocal
from app.models.user import User
from app.schemas.video import VideoResponse, VideoStatusResponse
from app.services import video_service, athlete_service
from app.services.processing_service import process_video_pipeline
from app.api.deps import get_current_active_user, RoleChecker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

allow_staff = RoleChecker(["coach", "physiotherapist", "sports_scientist", "administrator"])

def process_video_bg(video_id: int):
    db = SessionLocal()
    try:
        process_video_pipeline(db, video_id)
    except Exception as e:
        logger.error(f"Background processing failed for video {video_id}: {e}")
    finally:
        db.close()

@router.post("/", response_model=VideoResponse)
def upload_video(
    background_tasks: BackgroundTasks,
    athlete_id: int = Form(...),
    movement_type: str = Form("general"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Upload and register a movement trial video for an athlete:
    - Validates file format, duration, and resolution.
    - Captures movement pattern context (running, squatting, jumping, cutting, etc.).
    - Launches background MediaPipe Pose Estimation & kinematic pipeline.
    """
    profile = athlete_service.get_profile_by_id(db, athlete_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Athlete profile not found")
        
    # Authorization check
    if current_user.role == "athlete":
        if profile.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Athletes can only upload videos for their own profile")
    elif current_user.role != "administrator":
        is_assigned = athlete_service.check_staff_assigned_to_athlete(db, staff_id=current_user.id, athlete_id=athlete_id)
        if not is_assigned:
            raise HTTPException(status_code=403, detail="Not authorized to upload videos for this athlete")

    video = video_service.process_and_save_upload(
        db=db, 
        file=file, 
        athlete_id=athlete_id, 
        uploader_id=current_user.id,
        movement_type=movement_type
    )
    
    # Queue asynchronous MediaPipe processing task
    background_tasks.add_task(process_video_bg, video.id)
    
    return video

@router.get("/athlete/{athlete_id}", response_model=List[VideoResponse])
def get_athlete_videos(
    athlete_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get all videos for a specific athlete."""
    profile = athlete_service.get_profile_by_id(db, athlete_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Athlete profile not found")
        
    # Authorization check
    if current_user.role == "athlete":
        if profile.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Cannot access other athletes' videos")
    elif current_user.role != "administrator":
        is_assigned = athlete_service.check_staff_assigned_to_athlete(db, staff_id=current_user.id, athlete_id=athlete_id)
        if not is_assigned:
            raise HTTPException(status_code=403, detail="Not authorized to view videos for this athlete")
            
    return video_service.get_videos_for_athlete(db, athlete_id, skip=skip, limit=limit)

@router.get("/{video_id}", response_model=VideoResponse)
def get_video_details(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get metadata for a single video."""
    video = video_service.get_video_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    profile = athlete_service.get_profile_by_id(db, video.athlete_id)
    if current_user.role == "athlete" and profile and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this video")
        
    return video

@router.get("/{video_id}/status", response_model=VideoStatusResponse)
def get_video_status(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Poll live processing progress and quality status."""
    video = video_service.get_video_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    return {
        "id": video.id,
        "status": video.status,
        "processing_progress": video.processing_progress or 0,
        "quality_score": video.quality_score,
        "quality_issues": video.quality_issues,
        "error_message": video.error_message
    }

@router.get("/{video_id}/landmarks")
def get_video_landmarks(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Retrieve full timestamped keypoints, trajectories, and angle telemetry."""
    video = video_service.get_video_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    base_name = os.path.splitext(os.path.basename(video.filename))[0]
    json_path = os.path.join(settings.UPLOAD_DIR, f"{base_name}_landmarks.json")
    
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Landmarks telemetry not yet generated or video still processing")
        
    with open(json_path, "r") as f:
        return json.load(f)

@router.delete("/{video_id}")
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Delete video and clean up disk artifacts."""
    video = video_service.get_video_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    profile = athlete_service.get_profile_by_id(db, video.athlete_id)
    if current_user.role == "athlete" and profile and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this video")
        
    success = video_service.delete_video_and_files(db, video_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete video artifacts")
        
    return {"message": "Video trial and biomechanical artifacts successfully deleted"}
