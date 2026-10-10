import os
import shutil
import uuid
import cv2
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.config import UPLOAD_DIR, SAMPLE_DIR
from app.models.video import VideoRecord
from app.models.athlete import Athlete
from app.schemas.video import VideoResponse
from app.services.sample_generator import generate_athletic_movement_video

router = APIRouter(prefix="/videos", tags=["Videos"])

@router.get("", response_model=List[VideoResponse])
def list_videos(athlete_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(VideoRecord)
    if athlete_id:
        query = query.filter(VideoRecord.athlete_id == athlete_id)
    return query.order_by(VideoRecord.id.desc()).all()

@router.post("/upload", response_model=VideoResponse)
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(...),
    activity_type: str = Form("Jumping"),
    athlete_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    ext = Path(file.filename).suffix.lower()
    if ext not in [".mp4", ".mov", ".avi", ".webm", ".mkv"]:
        raise HTTPException(status_code=400, detail="Unsupported video format. Please upload MP4, MOV, or WebM.")

    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = UPLOAD_DIR / unique_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    # Extract video properties via OpenCV
    cap = cv2.VideoCapture(str(file_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
    duration = round(frame_count / fps, 2) if fps > 0 else 0.0
    cap.release()

    video_record = VideoRecord(
        athlete_id=athlete_id,
        title=title,
        activity_type=activity_type,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        duration_seconds=duration,
        fps=fps,
        frame_count=frame_count,
        resolution=f"{w}x{h}",
        status="uploaded"
    )
    db.add(video_record)
    db.commit()
    db.refresh(video_record)
    return video_record

@router.post("/generate_sample", response_model=VideoResponse)
def create_sample_video(
    movement_type: str = "Jump Landing (High Knee Valgus)",
    athlete_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    unique_filename = f"sample_{uuid.uuid4().hex[:8]}.mp4"
    sample_path = str(SAMPLE_DIR / unique_filename)

    generate_athletic_movement_video(
        output_path=sample_path,
        movement_type=movement_type,
        num_frames=120,
        fps=30
    )

    cap = cv2.VideoCapture(sample_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 120
    cap.release()

    video_record = VideoRecord(
        athlete_id=athlete_id or 1,
        title=f"Sample: {movement_type}",
        activity_type=movement_type.split("(")[0].strip(),
        original_filename=unique_filename,
        file_path=sample_path,
        file_size=os.path.getsize(sample_path),
        duration_seconds=round(frame_count / fps, 2),
        fps=fps,
        frame_count=frame_count,
        resolution="1280x720",
        status="uploaded"
    )
    db.add(video_record)
    db.commit()
    db.refresh(video_record)
    return video_record

@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: int, db: Session = Depends(get_db)):
    record = db.query(VideoRecord).filter(VideoRecord.id == video_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Video not found")
    return record

@router.get("/{video_id}/stream")
def stream_video(video_id: int, db: Session = Depends(get_db)):
    record = db.query(VideoRecord).filter(VideoRecord.id == video_id).first()
    if not record or not os.path.exists(record.file_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(record.file_path, media_type="video/mp4")

@router.get("/{video_id}/processed_stream")
def stream_processed_video(video_id: int, db: Session = Depends(get_db)):
    record = db.query(VideoRecord).filter(VideoRecord.id == video_id).first()
    if not record or not record.processed_video_path or not os.path.exists(record.processed_video_path):
        raise HTTPException(status_code=404, detail="Processed video not found. Run analysis first.")
    return FileResponse(record.processed_video_path, media_type="video/mp4")
