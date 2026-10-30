import os
import mimetypes
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

ALLOWED_MOVEMENTS = {
    "Drop Jump", "Side Cut", "Deep Squat", "Running", "Sprinting", "Throwing"
}

@router.get("", response_model=List[VideoResponse])
def list_videos(athlete_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(VideoRecord)
    if athlete_id:
        query = query.filter(VideoRecord.athlete_id == athlete_id)
    records = query.order_by(VideoRecord.id.desc()).all()
    # Ensure processed_video_path points to an existing file
    for r in records:
        if r.processed_video_path and not os.path.exists(r.processed_video_path):
            r.processed_video_path = None
    return records

@router.post("/upload", response_model=VideoResponse)
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(...),
    activity_type: str = Form(...),
    athlete_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    title = title.strip()
    activity_type = activity_type.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Enter a session title.")
    if activity_type not in ALLOWED_MOVEMENTS:
        raise HTTPException(status_code=400, detail="Select a supported movement before uploading: Drop Jump, Side Cut, Deep Squat, Running, Sprinting, or Throwing.")

    ext = Path(file.filename).suffix.lower()
    allowed_extensions = [".mp4", ".mov", ".avi", ".webm", ".mkv"]
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format '{ext}'. Supported formats: {', '.join(allowed_extensions)}"
        )

    safe_original_name = Path(file.filename or "").name
    if not safe_original_name:
        raise HTTPException(status_code=400, detail="Choose a video file with a valid filename.")
    unique_filename = f"{uuid.uuid4().hex}_{safe_original_name}"
    file_path = UPLOAD_DIR / unique_filename

    MAX_SIZE = 250 * 1024 * 1024  # 250 MB
    if file.size is not None and file.size > MAX_SIZE:
        raise HTTPException(status_code=400, detail=f"File exceeds maximum allowed size of 250 MB ({round(file.size/(1024*1024), 1)} MB uploaded).")

    file_size = 0
    try:
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                file_size += len(chunk)
                if file_size > MAX_SIZE:
                    raise HTTPException(status_code=400, detail="File exceeds maximum allowed size of 250 MB.")
                buffer.write(chunk)
    except Exception:
        if file_path.exists():
            file_path.unlink()
        raise

    if file_size == 0:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

    await file.seek(0)

    # Verify video properties and stream integrity via OpenCV
    cap = cv2.VideoCapture(str(file_path))
    if not cap.isOpened():
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail="Could not open video stream. Please ensure file contains valid video data.")

    ret, first_frame = cap.read()
    if not ret or first_frame is None:
        cap.release()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail="Video stream contains unreadable or corrupt frames.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or first_frame.shape[1]
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or first_frame.shape[0]
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

@router.get("/demo_samples")
def list_demo_samples():
    """List local sample videos available in backend/samples/ for demonstrations."""
    samples = []
    if not SAMPLE_DIR.exists():
        SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    valid_exts = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
    for f in sorted(SAMPLE_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in valid_exts:
            size_kb = round(f.stat().st_size / 1024, 1)
            size_str = f"{size_kb} KB" if size_kb < 1024 else f"{round(size_kb/1024, 2)} MB"
            name_lower = f.stem.lower()
            if "jump" in name_lower or "drop" in name_lower or "landing" in name_lower:
                suggested_activity = "Drop Jump"
            elif "cut" in name_lower or "side" in name_lower:
                suggested_activity = "Side Cut"
            elif "squat" in name_lower:
                suggested_activity = "Deep Squat"
            elif "sprint" in name_lower:
                suggested_activity = "Sprinting"
            elif "run" in name_lower:
                suggested_activity = "Running"
            elif "throw" in name_lower:
                suggested_activity = "Throwing"
            else:
                suggested_activity = "Drop Jump"

            is_synth = "synthetic" in name_lower or "sample" in name_lower or "marcus" in name_lower
            clean_title = f.stem.replace("synthetic_", "").replace("_", " ").replace("-", " ").title()
            samples.append({
                "filename": f.name,
                "title": clean_title,
                "file_size": f.stat().st_size,
                "file_size_formatted": size_str,
                "suggested_activity": suggested_activity,
                "is_synthetic": is_synth
            })
    return samples

@router.post("/demo_samples/load", response_model=VideoResponse)
def load_demo_sample(
    filename: str,
    title: Optional[str] = None,
    activity_type: Optional[str] = None,
    athlete_id: Optional[int] = 1,
    db: Session = Depends(get_db)
):
    """Load and register a local video from backend/samples/ as an active session."""
    safe_name = Path(filename).name
    sample_file = SAMPLE_DIR / safe_name
    if not sample_file.exists() or not sample_file.is_file():
        raise HTTPException(status_code=404, detail=f"Sample video '{safe_name}' not found in backend/samples/.")

    ext = sample_file.suffix.lower()
    if ext not in [".mp4", ".mov", ".avi", ".webm", ".mkv"]:
        raise HTTPException(status_code=400, detail="Unsupported video format.")

    cap = cv2.VideoCapture(str(sample_file))
    if not cap.isOpened():
        raise HTTPException(status_code=400, detail="Could not open video file.")

    ret, first_frame = cap.read()
    if not ret or first_frame is None:
        cap.release()
        raise HTTPException(status_code=400, detail="Sample video contains unreadable or corrupt frames.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or first_frame.shape[1]
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or first_frame.shape[0]
    duration = round(frame_count / fps, 2) if fps > 0 else 0.0
    cap.release()

    if not activity_type:
        name_lower = safe_name.lower()
        if "jump" in name_lower or "drop" in name_lower or "landing" in name_lower:
            inferred_activity = "Drop Jump"
        elif "cut" in name_lower or "side" in name_lower:
            inferred_activity = "Side Cut"
        elif "squat" in name_lower:
            inferred_activity = "Deep Squat"
        elif "sprint" in name_lower:
            inferred_activity = "Sprinting"
        elif "run" in name_lower:
            inferred_activity = "Running"
        elif "throw" in name_lower:
            inferred_activity = "Throwing"
        else:
            inferred_activity = "Drop Jump"
    else:
        inferred_activity = activity_type if activity_type in ALLOWED_MOVEMENTS else "Drop Jump"

    is_synth = "synthetic" in safe_name.lower() or "sample" in safe_name.lower() or "marcus" in safe_name.lower()
    clean_base = safe_name.replace("synthetic_", "").replace(".mp4", "").replace("_", " ").title()
    default_title = f"Synthetic Demo: {clean_base}" if is_synth else f"Demo: {clean_base}"
    session_title = title or default_title

    video_record = VideoRecord(
        athlete_id=athlete_id or 1,
        title=session_title,
        activity_type=inferred_activity,
        original_filename=safe_name,
        file_path=str(sample_file),
        file_size=sample_file.stat().st_size,
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
    if record.processed_video_path and not os.path.exists(record.processed_video_path):
        record.processed_video_path = None
    return record

@router.get("/{video_id}/stream")
def stream_video(video_id: int, db: Session = Depends(get_db)):
    record = db.query(VideoRecord).filter(VideoRecord.id == video_id).first()
    if not record or not os.path.exists(record.file_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(record.file_path, media_type=mimetypes.guess_type(record.file_path)[0] or "application/octet-stream")

@router.get("/{video_id}/processed_stream")
def stream_processed_video(video_id: int, db: Session = Depends(get_db)):
    record = db.query(VideoRecord).filter(VideoRecord.id == video_id).first()
    if not record or not record.processed_video_path or not os.path.exists(record.processed_video_path):
        raise HTTPException(status_code=404, detail="Processed video not found. Run analysis first.")
    return FileResponse(record.processed_video_path, media_type="video/mp4")
