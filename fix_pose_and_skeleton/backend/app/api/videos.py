from pathlib import Path
from uuid import uuid4

import mimetypes

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import Role, User
from app.models.video import Video
from app.schemas.video import Activity, VideoOut
from app.services.access import accessible_athletes_query, get_athlete_for
from app.services.analysis_pipeline import run_analysis
from app.services.pose_store import load_pose
from app.services.video_processing import ALLOWED_EXTENSIONS, validate_video

router = APIRouter(prefix="/videos", tags=["videos"])

UPLOADERS = (Role.athlete.value, Role.coach.value, Role.physiotherapist.value, Role.administrator.value)


@router.post("/upload", response_model=VideoOut, status_code=201)
async def upload_video(
    background: BackgroundTasks,
    athlete_id: int = Form(...),
    activity: Activity = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*UPLOADERS)),
):
    athlete = get_athlete_for(db, user, athlete_id, write=True)

    original = Path(file.filename or "video").name
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{uuid4().hex}{ext}"  # never trust the client's filename on disk

    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    size = 0
    try:
        with dest.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_MB} MB")
                out.write(chunk)
    except Exception:
        dest.unlink(missing_ok=True)
        raise

    info = await run_in_threadpool(validate_video, dest)
    if info["errors"]:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail={"message": "Video failed quality validation", "errors": info["errors"]})

    video = Video(
        athlete_id=athlete.id,
        uploaded_by=user.id,
        activity=activity,
        original_filename=original[:255],
        stored_path=str(dest),
        fps=info["fps"],
        width=info["width"],
        height=info["height"],
        frame_count=info["frame_count"],
        duration_s=info["duration_s"],
        status="uploaded",
        quality={k: info[k] for k in ("brightness", "sharpness", "warnings")},
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    background.add_task(run_analysis, video.id)
    return video


@router.get("", response_model=list[VideoOut])
def list_videos(
    athlete_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if athlete_id is not None:
        get_athlete_for(db, user, athlete_id)
        query = select(Video).where(Video.athlete_id == athlete_id)
    else:
        ids = select(accessible_athletes_query(user).subquery().c.id)
        query = select(Video).where(Video.athlete_id.in_(ids))
    return db.scalars(query.order_by(Video.created_at.desc()).limit(200)).all()


def _get_video(db: Session, user: User, video_id: int, write: bool = False) -> Video:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    get_athlete_for(db, user, video.athlete_id, write=write)
    return video


@router.get("/{video_id}", response_model=VideoOut)
def get_video(video_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _get_video(db, user, video_id)


@router.get("/{video_id}/file")
def get_video_file(video_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """The uploaded video itself, for playback next to the skeleton overlay."""
    video = _get_video(db, user, video_id)
    path = Path(video.stored_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type)


@router.get("/{video_id}/pose")
def get_pose(video_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Keypoints per frame for drawing the skeleton overlay."""
    _get_video(db, user, video_id)
    payload = load_pose(video_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Pose data not available yet")
    return payload


@router.post("/{video_id}/analyze", response_model=VideoOut, status_code=202)
def reanalyze(
    video_id: int, background: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    video = _get_video(db, user, video_id, write=True)
    if video.status == "processing":
        raise HTTPException(status_code=409, detail="Analysis already running")
    video.status = "uploaded"
    db.commit()
    background.add_task(run_analysis, video.id)
    return video


@router.delete("/{video_id}", status_code=204)
def delete_video(video_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    video = _get_video(db, user, video_id, write=True)
    Path(video.stored_path).unlink(missing_ok=True)
    db.delete(video)
    db.commit()
