"""Video router — presigned uploads, confirm, listing, biomechanics."""

import logging
import os
import uuid
import csv
import io
import subprocess
from typing import Annotated

from app.core.errors import api_error
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.deps import get_current_user, require_role
from app.database import get_db
from app.modules.users.models import User, UserRole
from app.modules.athletes.models import Athlete
from app.modules.videos.models import Video, VideoProcessingStatus, BiomechanicalMetric
from app.modules.videos.schemas import (
    VideoUploadRequest, VideoUploadResponse, VideoResponse, VideoListResponse,
    BiomechanicsResponse, BiomechanicsSummary, BiomechanicsFrame
)
from app.modules.biomechanics.calculations import limb_symmetry_index
import re
from fastapi.responses import FileResponse
import json

SAFE_FILENAME_PATTERN = re.compile(r'^[\w\-. ]{1,200}\.(mp4|mov)$', re.IGNORECASE)

def _safe_filename(original: str) -> str:
    base = os.path.basename(original)
    if not SAFE_FILENAME_PATTERN.match(base):
        return "upload.mp4"
    return base

async def _reject_upload(db, video, code: str, message: str, local_path: str):
    await db.delete(video)
    await db.commit()
    if os.path.exists(local_path):
        try:
            os.remove(local_path)
        except OSError:
            pass
    raise HTTPException(status_code=400, detail={"error": {"code": code, "message": message}})


# Arq redis pool
from arq import create_pool
from app.modules.pose.worker_settings import redis_settings_from_env

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])

async def get_arq_pool():
    return await create_pool(redis_settings_from_env())

def _can_access_athlete(user: User, athlete: Athlete) -> bool:
    if user.role in (UserRole.admin, UserRole.physiotherapist, UserRole.sports_scientist):
        return True
    if user.role == UserRole.coach and athlete.coach_id == user.id:
        return True
    if user.role == UserRole.athlete and athlete.user_id == user.id:
        return True
    return False

@router.post("/upload-url", response_model=VideoUploadResponse)
async def create_upload_url(
    data: VideoUploadRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
):
    """Generate a mock presigned URL and create a pending video record."""
    athlete = await db.scalar(select(Athlete).where(Athlete.id == data.athlete_id))
    if not athlete:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Athlete not found"}})
    
    if not _can_access_athlete(current_user, athlete):
        raise HTTPException(status_code=403, detail={"error": {"code": "INSUFFICIENT_PERMISSIONS", "message": "Access denied"}})
    
    if current_user.role == UserRole.athlete and athlete.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={"error": {"code": "INSUFFICIENT_PERMISSIONS", "message": "Athletes can only upload for themselves"}})

    safe_name = _safe_filename(data.original_filename)
    video = Video(
        athlete_id=data.athlete_id,
        uploaded_by=current_user.id,
        movement_type=data.movement_type,
        storage_key=f"{uuid.uuid4()}_{safe_name}",
        original_filename=safe_name,
        camera_view=data.camera_view,
        processing_status=VideoProcessingStatus.pending_upload
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # For local dev, we provide a URL to our local mock endpoint
    base_url = str(request.base_url).rstrip('/')
    upload_url = f"{base_url}/api/v1/local-storage/{video.storage_key}"

    return VideoUploadResponse(
        video_id=video.id,
        upload_url=upload_url,
        storage_key=video.storage_key,
        expires_in=3600
    )


@router.post("/{video_id}/confirm-upload")
async def confirm_upload(
    video_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Confirm upload, validate via ffprobe, and enqueue for processing."""
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")
        
    if video.uploaded_by != current_user.id:
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Must be the creator to confirm upload")

    local_path = os.path.join("/uploads", video.storage_key)
    if not os.path.exists(local_path):
        raise HTTPException(status_code=400, detail={"error": {"code": "NOT_FOUND", "message": "File not found in storage"}})

    # M6 format validation
    if not (video.original_filename.lower().endswith(".mp4") or video.original_filename.lower().endswith(".mov")):
        await _reject_upload(db, video, "invalid_format", "Only .mp4 or .mov files are allowed", local_path)

    # Run ffprobe
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration",
        "-of", "json", local_path
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
        data = json.loads(output)
        stream = data["streams"][0]
        width, height = int(stream["width"]), int(stream["height"])
        fps_str = stream["r_frame_rate"]
        if '/' in fps_str:
            num, den = fps_str.split('/')
            fps = float(num) / float(den) if float(den) != 0 else 0.0
        else:
            fps = float(fps_str)
        duration = float(stream["duration"])
    except Exception as e:
        logger.error(f"ffprobe failed: {e}")
        await _reject_upload(db, video, "invalid_format", "Could not parse video format", local_path)

    # Validate limits
    file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
    if file_size_mb > 200:
        await _reject_upload(db, video, "file_too_large", "File exceeds 200MB", local_path)

    if duration < 2 or duration > 60:
        await _reject_upload(db, video, "duration_out_of_range", "Duration must be between 2 and 60 seconds", local_path)

    if height < 480:
        await _reject_upload(db, video, "resolution_too_low", "Minimum height is 480p", local_path)

    video.resolution_width = width
    video.resolution_height = height
    video.fps = fps
    video.duration_seconds = duration
    # Enqueue job first, then mark as processing
    arq = await get_arq_pool()
    job = await arq.enqueue_job("process_video", video_id)
    
    video.processing_status = VideoProcessingStatus.processing
    video.job_id = job.job_id
    await db.commit()

    return {"status": "processing"}


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video_endpoint(
    video_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")
    
    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")
        
    return video

@router.get("/{video_id}/file")
async def get_video_file(
    video_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")
    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")
    path = os.path.join("/uploads", video.storage_key)
    if not os.path.exists(path):
        raise api_error(404, "NOT_FOUND", "File not found")
    return FileResponse(path, media_type="video/mp4")

@router.get("/{video_id}/thumbnail")
async def get_video_thumbnail(
    video_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video or not video.thumbnail_key:
        raise api_error(404, "NOT_FOUND", "Not found")
    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")
    if not os.path.exists(video.thumbnail_key):
        raise api_error(404, "NOT_FOUND", "File not found")
    return FileResponse(video.thumbnail_key, media_type="image/jpeg")




@router.get("", response_model=VideoListResponse)
async def list_videos(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    athlete_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(Video).order_by(desc(Video.created_at))
    count_query = select(func.count()).select_from(Video)

    if current_user.role == UserRole.coach:
        query = query.join(Athlete).where(Athlete.coach_id == current_user.id)
        count_query = count_query.join(Athlete).where(Athlete.coach_id == current_user.id)
    elif current_user.role == UserRole.athlete:
        query = query.join(Athlete).where(Athlete.user_id == current_user.id)
        count_query = count_query.join(Athlete).where(Athlete.user_id == current_user.id)

    if athlete_id:
        query = query.where(Video.athlete_id == athlete_id)
        count_query = count_query.where(Video.athlete_id == athlete_id)

    total = await db.scalar(count_query)
    query = query.offset((page - 1) * page_size).limit(page_size)
    videos = list((await db.scalars(query)).all())

    return VideoListResponse(items=videos, total=total, page=page, page_size=page_size)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: str,
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.coach))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")

    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if current_user.role == UserRole.coach and athlete.coach_id != current_user.id:
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    # Clean up local storage files
    for key in filter(None, [video.storage_key, video.thumbnail_key, video.annotated_video_key]):
        path = os.path.join("/uploads", os.path.basename(key)) if not key.startswith("/uploads") else key
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    await db.delete(video)
    await db.commit()


@router.get("/{video_id}/biomechanics", response_model=BiomechanicsResponse)
async def get_biomechanics(
    video_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")
        
    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    # 10x Patch: Hero stats query
    stmt = (
        select(
            BiomechanicalMetric.metric_name,
            func.max(BiomechanicalMetric.metric_value).label("peak_value"),
            func.min(BiomechanicalMetric.metric_value).label("min_value")
        )
        .where(BiomechanicalMetric.video_id == video_id, BiomechanicalMetric.confidence == 'validated')
        .group_by(BiomechanicalMetric.metric_name)
    )
    result = await db.execute(stmt)
    
    summary = []
    peaks = {}
    for row in result:
        peak = float(row.peak_value) if row.peak_value is not None else None
        min_v = float(row.min_value) if row.min_value is not None else None
        rom = (peak - min_v) if (peak is not None and min_v is not None) else None
        
        summary.append(BiomechanicsSummary(
            metric_name=row.metric_name,
            peak_value=peak,
            min_value=min_v,
            range_of_motion=rom
        ))
        if peak is not None:
            peaks[row.metric_name] = peak

    lsi = None
    if "knee_flexion_angle_left" in peaks and "knee_flexion_angle_right" in peaks:
        lsi = limb_symmetry_index(peaks["knee_flexion_angle_left"], peaks["knee_flexion_angle_right"])

    frames = list((await db.scalars(
        select(BiomechanicalMetric)
        .where(BiomechanicalMetric.video_id == video_id)
        .order_by(BiomechanicalMetric.frame_number)
    )).all())

    return BiomechanicsResponse(
        video_id=video_id,
        detection_rate=video.detection_rate,
        limb_symmetry_index=lsi,
        summary=summary,
        frames=frames
    )


@router.get("/{video_id}/biomechanics/export.csv")
async def export_csv(
    video_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")
        
    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    frames = list((await db.scalars(
        select(BiomechanicalMetric)
        .where(BiomechanicalMetric.video_id == video_id)
        .order_by(BiomechanicalMetric.frame_number)
    )).all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["frame_number", "metric_name", "value", "plane", "confidence"])
    for r in frames:
        writer.writerow([r.frame_number, r.metric_name, r.metric_value, r.plane, r.confidence])
        
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=video_{video_id}_metrics.csv"},
    )
