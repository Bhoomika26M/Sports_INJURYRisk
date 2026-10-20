from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
from app.db.database import get_db, SessionLocal
from app.core.security import get_current_active_user
from app.core.dependencies import require_admin
from app.models.user import User
from app.models.video import Video, ProcessingStatus
from app.models.pose_analysis import PoseAnalysis
from app.models.biomechanical_analysis import BiomechanicalAnalysis
from app.schemas.video import VideoCreate, VideoResponse
from app.schemas.history import BaselineComparison
from app.services.video_service import VideoService
from app.services.processing_service import VideoProcessingService
from app.services import progress_service
from app.services import baseline_service
from app.core.audit import log_security_event

router = APIRouter()


def _run_video_processing(video_id: int, activity: str) -> None:
    """
    Background worker for video analysis.
    
    Runs after the HTTP response is sent (FastAPI BackgroundTasks) so
    POST /process returns immediately and the client can poll
    GET /videos/{id} for processing_status.
    
    Uses its own DB session because the request-scoped session is closed
    by the time the task runs.
    """
    db = SessionLocal()
    try:
        processing_service = VideoProcessingService()
        results = processing_service.process_video(video_id, db, activity=activity)
        log_security_event(
            "video_processing_completed",
            details={"video_id": video_id, "results": results}
        )
    except Exception as e:
        # process_video already marks the video as failed
        try:
            progress_service.set_stage(video_id, "failed", error=str(e))
        except Exception:
            pass
        log_security_event(
            "video_processing_failed",
            details={"video_id": video_id, "error": str(e)},
            success=False
        )
    finally:
        db.close()


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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Trigger video processing (pose estimation, biomechanics).
    
    Runs asynchronously: returns immediately with status "preprocessing";
    the client polls GET /api/v1/videos/{video_id} for processing_status.
    
    Security:
    - Requires authentication
    - User must have access to the video
    """
    video = VideoService.get_video(video_id, current_user, db)
    
    if video.processing_status in (
        ProcessingStatus.PREPROCESSING,
        ProcessingStatus.POSE_ESTIMATION,
        ProcessingStatus.ANALYZING
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video is already being processed"
        )
    
    if video.processing_status == ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video has already been processed"
        )
    
    # Claim the video immediately so a double-click cannot start two runs
    VideoService.update_processing_status(
        video_id, ProcessingStatus.PREPROCESSING, db=db
    )
    
    # Heavy analysis runs in the background, not in the request
    background_tasks.add_task(
        _run_video_processing, video_id, video.activity_type
    )
    
    return {
        "message": "Video processing started",
        "video_id": video_id,
        "status": ProcessingStatus.PREPROCESSING.value
    }


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


@router.get("/{video_id}/comparison", response_model=BaselineComparison)
def get_video_comparison(
    video_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Compare this video's analysis against the athlete's rolling baseline.

    The baseline is the mean of the athlete's most recent prior analyses of the
    **same activity type**, and deliberately excludes this video. This compares
    the *recorded* snapshot, so the answer is stable: it will not drift as the
    athlete uploads more videos.

    Returns ``status="no_history"`` for the athlete's first analysis of an
    activity, and ``"insufficient_history"`` until enough prior analyses exist.

    Security:
    - Requires authentication
    - User must have access to the video
    """
    video = VideoService.get_video(video_id, current_user, db)

    from app.models.analysis_snapshot import AnalysisSnapshot

    snapshot = (
        db.query(AnalysisSnapshot)
        .filter(AnalysisSnapshot.video_id == video_id)
        .first()
    )
    if snapshot is None:
        # No snapshot yet: the video has not been processed to completion, or
        # it predates history tracking. Say so explicitly rather than
        # pretending there is no history.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed analysis recorded for this video yet. Process the video first.",
        )

    comparison = snapshot.baseline_comparison
    if not comparison:
        return BaselineComparison(status="no_history", baseline_size=0)
    return BaselineComparison.model_validate(comparison)


@router.post("/{video_id}/annotated-video")
def generate_annotated_video(
    video_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate annotated video with skeleton visualization.
    
    Idempotent: if the overlay produced during analysis already exists,
    it is reused instead of re-decoding and re-encoding the whole video.
    
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
    
    # Reuse the annotated video written during analysis, if present
    video_path = Path(video.storage_path)
    annotated_path = video_path.parent / f"annotated_{video_path.name}"
    if annotated_path.exists():
        return {
            "message": "Annotated video already exists",
            "cached": True,
            "output_path": str(annotated_path),
            "fps": video.fps
        }
    
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
            detail="Annotated video not found. It is generated automatically during analysis; re-run POST /{video_id}/annotated-video for videos processed earlier."
        )
    
    return FileResponse(
        path=str(annotated_path),
        media_type="video/mp4",
        filename=f"annotated_{video.original_filename}"
    )


@router.get("/{video_id}/video")
def get_original_video(
    video_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get original video file.

    Security:
    - Requires authentication
    - User must have access to the video
    """
    video = VideoService.get_video(video_id, current_user, db)

    video_path = Path(video.storage_path)

    if not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original video file not found"
        )

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=video.original_filename
    )


@router.get("/{video_id}/progress")
def get_processing_progress(
    video_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Live step-by-step progress of the video analysis.
    
    Updated by the background worker after every processed chunk:
    stage, percent, frames processed, live joint angles, streaming
    risk summary, and a reference to the latest preview frame.
    
    Security:
    - Requires authentication
    - User must have access to the video
    """
    video = VideoService.get_video(video_id, current_user, db)
    
    state = progress_service.read(video_id)
    if state is None:
        # No background run recorded (video processed before live progress
        # existed): derive a minimal state from the video row
        status_val = video.processing_status.value
        state = {
            "video_id": video_id,
            "status": status_val,
            "stage": status_val,
            "stage_label": (
                "Analysis complete" if status_val == "completed"
                else status_val.replace("_", " ").title()
            ),
            "percent": 100 if status_val == "completed" else 0,
            "frames_processed": None,
            "total_frames": None,
            "mean_confidence": None,
            "current_angles": {},
            "risk": None,
            "error": video.processing_error,
            "updated_at": (
                video.updated_at.isoformat() if video.updated_at else None
            ),
        }
    return state


@router.get("/{video_id}/preview-frame")
def get_preview_frame(
    video_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Latest annotated frame (skeleton overlay) as JPEG.
    
    Refreshed by the background worker while analysis runs, giving a
    step-by-step live view of the skeleton mapping. Cache is disabled
    so <img> tags poll the newest frame.
    
    Security:
    - Requires authentication
    - User must have access to the video
    """
    VideoService.get_video(video_id, current_user, db)
    
    preview = progress_service.preview_path(video_id)
    if not preview.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preview frame not available yet"
        )
    
    return FileResponse(
        path=str(preview),
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store, max-age=0"}
    )
