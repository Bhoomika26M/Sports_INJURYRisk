import os
import secrets
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.video import Video, ProcessingStatus
from app.models.athlete import Athlete
from app.models.user import User
from app.core.config import settings
from app.core.audit import log_security_event


class VideoService:
    @staticmethod
    def generate_safe_filename(original_filename: str) -> str:
        """Generate a safe server-side filename."""
        # Generate random filename with original extension
        ext = os.path.splitext(original_filename)[1].lower()
        # Validate extension
        allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. Allowed formats: mp4, avi, mov, mkv, webm"
            )
        return f"{secrets.token_urlsafe(32)}{ext}"
    
    @staticmethod
    def validate_video_file(file_size: int, filename: str) -> None:
        """Validate video file size and type."""
        # Check file size
        if file_size > settings.MAX_VIDEO_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.MAX_VIDEO_SIZE / (1024*1024)} MB"
            )
        
        # Check file extension
        ext = os.path.splitext(filename)[1].lower()
        allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. Allowed formats: mp4, avi, mov, mkv, webm"
            )
    
    @staticmethod
    def check_athlete_access(user: User, athlete_id: int, db: Session) -> Athlete:
        """Check if user can access the athlete."""
        athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
        if not athlete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Athlete not found"
            )
        
        # Athletes can only access their own profile
        if user.role == "athlete":
            if athlete.user_id != user.id:
                log_security_event("unauthorized_athlete_access", {
                    "user_id": user.id,
                    "athlete_id": athlete_id
                })
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only upload videos for your own athlete profile"
                )
        
        # Other roles (coach, physiotherapist, sports_scientist, admin) can access
        # This will be refined based on business rules
        
        return athlete
    
    @staticmethod
    def create_video(
        athlete_id: int,
        uploaded_by: int,
        original_filename: str,
        activity_type: str,
        file_size: int,
        db: Session
    ) -> Video:
        """Create a video record."""
        safe_filename = VideoService.generate_safe_filename(original_filename)
        storage_path = os.path.join(settings.VIDEO_UPLOAD_DIR, safe_filename)
        
        video = Video(
            athlete_id=athlete_id,
            uploaded_by=uploaded_by,
            filename=safe_filename,
            original_filename=original_filename,
            storage_path=storage_path,
            activity_type=activity_type,
            file_size=file_size,
            processing_status=ProcessingStatus.UPLOADED
        )
        
        db.add(video)
        db.commit()
        db.refresh(video)
        
        log_security_event("video_uploaded", {
            "video_id": video.id,
            "athlete_id": athlete_id,
            "uploaded_by": uploaded_by,
            "filename": original_filename
        })
        
        return video
    
    @staticmethod
    def get_video(video_id: int, user: User, db: Session) -> Video:
        """Get a video with authorization check."""
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Check authorization
        if user.role == "athlete":
            # Athletes can only access their own videos
            athlete = db.query(Athlete).filter(Athlete.id == video.athlete_id).first()
            if athlete and athlete.user_id != user.id:
                log_security_event("unauthorized_video_access", {
                    "user_id": user.id,
                    "video_id": video_id
                })
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only access your own videos"
                )
        
        return video
    
    @staticmethod
    def delete_video(video_id: int, user: User, db: Session) -> None:
        """Delete a video with authorization check."""
        video = VideoService.get_video(video_id, user, db)
        
        # Only administrators can delete videos
        if user.role != "administrator":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can delete videos"
            )
        
        # Delete file from disk
        if os.path.exists(video.storage_path):
            os.remove(video.storage_path)
        
        # Delete from database
        db.delete(video)
        db.commit()
        
        log_security_event("video_deleted", {
            "video_id": video_id,
            "deleted_by": user.id
        })
    
    @staticmethod
    def update_processing_status(
        video_id: int,
        status: ProcessingStatus,
        error: Optional[str] = None,
        db: Session = None
    ) -> None:
        """Update video processing status."""
        from app.db.database import SessionLocal
        if db is None:
            db = SessionLocal()
        
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.processing_status = status
                if error:
                    video.processing_error = error
                
                if status == ProcessingStatus.PREPROCESSING:
                    from datetime import datetime
                    video.processing_started_at = datetime.utcnow()
                elif status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
                    from datetime import datetime
                    video.processing_completed_at = datetime.utcnow()
                
                db.commit()
        finally:
            if db is None:
                db.close()
