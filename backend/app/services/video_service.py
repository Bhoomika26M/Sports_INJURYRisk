import os
import shutil
import uuid
import logging
from typing import List, Optional
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.models.video import Video
from app.core.config import settings
from app.utils.video_utils import extract_video_metadata, validate_video_suitability, verify_magic_bytes

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}
ALLOWED_MIME_TYPES = {
    "video/mp4", 
    "video/quicktime", 
    "video/x-msvideo", 
    "video/avi", 
    "video/webm", 
    "application/octet-stream"
}

VALID_MOVEMENT_TYPES = {
    "running", 
    "sprinting", 
    "squatting", 
    "jumping", 
    "landing", 
    "cutting", 
    "throwing", 
    "general"
}

def get_video_by_id(db: Session, video_id: int) -> Optional[Video]:
    return db.query(Video).filter(Video.id == video_id).first()

def get_videos_for_athlete(db: Session, athlete_id: int, skip: int = 0, limit: int = 100) -> List[Video]:
    return db.query(Video).filter(Video.athlete_id == athlete_id).order_by(Video.created_at.desc()).offset(skip).limit(limit).all()

def process_and_save_upload(
    db: Session, 
    file: UploadFile, 
    athlete_id: int, 
    uploader_id: int,
    movement_type: str = "general"
) -> Video:
    # 1. Validate extension & MIME
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, detail=f"Unsupported file format '{ext}'. Allowed video formats: MP4, MOV, AVI, WEBM.")
        
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, detail=f"Invalid MIME content type: '{file.content_type}'. Must be a valid video stream.")

    # Validate movement type
    clean_movement = (movement_type or "general").lower().strip()
    if clean_movement not in VALID_MOVEMENT_TYPES:
        clean_movement = "general"

    # 2. Check file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > settings.MAX_VIDEO_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, detail=f"File exceeds maximum allowed size ({settings.MAX_VIDEO_SIZE_MB}MB). Please compress or trim the clip.")
    
    if file_size == 0:
        raise HTTPException(400, detail="Uploaded file is empty (0 bytes).")

    # Inspect initial bytes for header verification
    header_sample = file.file.read(64)
    file.file.seek(0)
    
    # 3. Create safe filename and directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 4. Extract & validate suitability (duration, resolution, decodability)
        try:
            fps, width, height, duration_sec = extract_video_metadata(file_path)
            
            # Duration checks
            if duration_sec < 0.5:
                raise ValueError(f"Video is too short ({duration_sec:.1f}s). Requires at least 0.5s for biomechanical movement analysis.")
            if duration_sec > settings.MAX_VIDEO_DURATION_SEC:
                raise ValueError(f"Video duration ({duration_sec:.1f}s) exceeds maximum allowed limit of {settings.MAX_VIDEO_DURATION_SEC} seconds.")
                
        except ValueError as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(400, detail=str(e))
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(400, detail=f"Invalid or unreadable video file: {str(e)}")
            
        # 5. Create database record
        db_video = Video(
            athlete_id=athlete_id,
            uploader_id=uploader_id,
            filename=safe_filename,
            original_filename=file.filename or "video" + ext,
            file_path=file_path,
            format=ext.replace(".", ""),
            size_bytes=file_size,
            duration_sec=round(duration_sec, 2),
            fps=round(fps, 2),
            width=width,
            height=height,
            status="uploaded",
            movement_type=clean_movement,
            processing_progress=0
        )
        db.add(db_video)
        db.commit()
        db.refresh(db_video)
        
        return db_video
        
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Error saving upload: {e}")
        raise HTTPException(500, detail=f"An error occurred while saving the uploaded video: {str(e)}")

def delete_video_and_files(db: Session, video_id: int) -> bool:
    """Safely removes video record and associated annotated video & landmark JSON artifacts from storage."""
    video = get_video_by_id(db, video_id)
    if not video:
        return False
        
    # Remove raw video file
    if video.file_path and os.path.exists(video.file_path):
        try:
            os.remove(video.file_path)
        except OSError as e:
            logger.warning(f"Could not remove raw video {video.file_path}: {e}")
            
    # Remove annotated video and landmarks json
    base_name = os.path.splitext(os.path.basename(video.filename))[0]
    annotated_path = os.path.join(settings.UPLOAD_DIR, f"{base_name}_annotated.mp4")
    json_path = os.path.join(settings.UPLOAD_DIR, f"{base_name}_landmarks.json")
    
    for path in [annotated_path, json_path]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError as e:
                logger.warning(f"Could not remove generated artifact {path}: {e}")
                
    db.delete(video)
    db.commit()
    return True
