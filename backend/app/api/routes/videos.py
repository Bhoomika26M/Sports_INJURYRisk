from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
from app.db.database import get_db
from app.core.security import get_current_active_user
from app.core.dependencies import require_admin
from app.models.user import User
from app.models.video import Video, ProcessingStatus
from app.models.pose_analysis import PoseAnalysis
from app.models.biomechanical_analysis import BiomechanicalAnalysis
from app.schemas.video import VideoCreate, VideoResponse
from app.services.video_service import VideoService
from app.services.processing_service import VideoProcessingService
from app.core.audit import log_security_event

router = APIRouter()


@router.post("", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def upload_video(
    athlete_id: int = Form(...),
    activity_type: str = Form(...),
    video: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload a video for an athlete.
    
    Security:
    - Requires authentication
    - Athletes can only upload to their own profile
    - Other roles require appropriate permissions
    - File size and type validation
    - Safe filename generation
    """
    # Check athlete access
    athlete = VideoService.check_athlete_access(current_user, athlete_id, db)
    
    # Validate file
    file_size = 0
    video.file.seek(0, 2)  # Seek to end
    file_size = video.file.tell()
    video.file.seek(0)  # Seek back to beginning
    
    VideoService.validate_video_file(file_size, video.filename)
    
    # Create video record
    video_record = VideoService.create_video(
        athlete_id=athlete_id,
        uploaded_by=current_user.id,
        original_filename=video.filename,
        activity_type=activity_type,
        file_size=file_size,
        db=db
    )
    
    # Save file to disk
    try:
        with open(video_record.storage_path, "wb") as buffer:
            buffer.write(video.file.read())
    except Exception as e:
        # Cleanup if file save fails
        VideoService.update_processing_status(
            video_record.id,
            ProcessingStatus.FAILED,
            f"Failed to save file: {str(e)}",
            db
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save video file"
        )
    
    return video_record


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get video details by ID.
    
    Security:
    - Requires authentication
    - Athletes can only access their own videos
    - IDOR protection
    """
    return VideoService.get_video(video_id, current_user, db)


@router.get("", response_model=List[VideoResponse])
def list_videos(
    athlete_id: int = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List videos, optionally filtered by athlete.
    
    Security:
    - Requires authentication
    - Athletes can only see their own videos
    """
    query = db.query(Video)
    
    if athlete_id:
        # Check athlete access
        athlete = VideoService.check_athlete_access(current_user, athlete_id, db)
        query = query.filter(Video.athlete_id == athlete_id)
    else:
        # If no athlete filter, only show user's own videos (if athlete)
        if current_user.role == "athlete":
            from app.models.athlete import Athlete
            athlete = db.query(Athlete).filter(Athlete.user_id == current_user.id).first()
            if athlete:
                query = query.filter(Video.athlete_id == athlete.id)
    
    return query.all()


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a video.
    
    Security:
    - Requires administrator role
    - Deletes file from disk and database record
    """
    VideoService.delete_video(video_id, current_user, db)


@router.post("/{video_id}/process")
def process_video(
    video_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Trigger video processing (pose estimation, biomechanics).
    
    Security:
    - Requires authentication
    - User must have access to the video
    """
    video = VideoService.get_video(video_id, current_user, db)
    
    if video.processing_status == ProcessingStatus.PREPROCESSING or video.processing_status == ProcessingStatus.POSE_ESTIMATION or video.processing_status == ProcessingStatus.ANALYZING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video is already being processed"
        )
    
    if video.processing_status == ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video has already been processed"
        )
    
    # Process video synchronously (in production, this should be async)
    processing_service = VideoProcessingService()
    
    try:
        results = processing_service.process_video(video_id, db)
        
        log_security_event("video_processing_completed", {
            "video_id": video_id,
            "user_id": current_user.id,
            "results": results
        })
        
        return {
            "message": "Video processed successfully",
            "results": results
        }
    except Exception as e:
        log_security_event("video_processing_failed", {
            "video_id": video_id,
            "user_id": current_user.id,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video processing failed: {str(e)}"
        )


@router.get("/{video_id}/analysis")
def get_video_analysis(
    video_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get video analysis results.
    
    Security:
    - Requires authentication
    - User must have access to the video
    """
    video = VideoService.get_video(video_id, current_user, db)
    
    pose_analysis = db.query(PoseAnalysis).filter(PoseAnalysis.video_id == video_id).first()
    if not pose_analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found for this video"
        )
    
    biomechanical_analysis = db.query(BiomechanicalAnalysis).filter(
        BiomechanicalAnalysis.pose_analysis_id == pose_analysis.id
    ).first()
    
    return {
        "video": video,
        "pose_analysis": pose_analysis,
        "biomechanical_analysis": biomechanical_analysis
    }


@router.post("/{video_id}/annotated-video")
def generate_annotated_video(
    video_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate annotated video with skeleton visualization.
    
    Security:
    - Requires authentication
    - User must have access to the video
    """
    video = VideoService.get_video(video_id, current_user, db)
    
    if video.processing_status != ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video must be processed before generating annotated video"
        )
    
    processing_service = VideoProcessingService()
    
    try:
        result = processing_service.generate_annotated_video(video_id, db)
        
        return {
            "message": "Annotated video generated successfully",
            "output_path": result["output_path"],
            "frames_annotated": result["frames_annotated"],
            "fps": result["fps"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate annotated video: {str(e)}"
        )


@router.get("/{video_id}/annotated-video")
def get_annotated_video(
    video_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get annotated video file.
    
    Security:
    - Requires authentication
    - User must have access to the video
    """
    video = VideoService.get_video(video_id, current_user, db)
    
    # Construct annotated video path
    video_path = Path(video.storage_path)
    annotated_path = video_path.parent / f"annotated_{video_path.name}"
    
    if not annotated_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotated video not found. Generate it first using POST /{video_id}/annotated-video"
        )
    
    return FileResponse(
        path=str(annotated_path),
        media_type="video/mp4",
        filename=f"annotated_{video.original_filename}"
    )
