"""Video router — presigned uploads, confirm, listing, biomechanics."""

import logging
import os
import re
import shutil
import uuid
import json
import subprocess
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.access import can_access_athlete as _can_access_athlete
from app.core.deps import UuidPath, get_current_user, require_role
from app.core.errors import api_error
from app.database import get_db
from app.modules.users.models import User, UserRole
from app.modules.athletes.models import Athlete
from app.modules.video.models import Video, VideoProcessingStatus, BiomechanicalMetric
from app.modules.video.schemas import (
    VideoUploadRequest, VideoUploadResponse, VideoResponse, VideoListResponse,
    BiomechanicsResponse, BiomechanicsSummary, BiomechanicsFrame,
)
from app.modules.biomechanics.calculations import limb_symmetry_index
from app.modules.biomechanics.classification import AUTO
from app.modules.video.comparison_schemas import (
    CompareVideosRequest, CompareVideosResponse, VectorPostureData,
)
from app.modules.video.comparison_service import compare_two_videos
from app.modules.video.vector_service import extract_inflection_vector_for_video, get_textbook_ideal_landmarks
from app.modules.risk_scoring.models import RiskScore

# One list for the filename gate AND the storage-key gate (main.py): they drifted once (storage PUT still said mp4|mov).
VIDEO_EXTENSIONS = "mp4|mov|webm|avi|mkv|m4v"
SAFE_FILENAME_PATTERN = re.compile(rf'^[\w\-. ]{{1,200}}\.({VIDEO_EXTENSIONS})$', re.IGNORECASE)

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
    raise api_error(400, code, message)

from app.modules.pose.jobs import enqueue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])


def _ensure_uuid_or_422(value: str | None, field: str = "athlete_id") -> None:
    """Query-param UUIDs reach Postgres raw: a malformed value must be 422, never a 500 DBAPIError."""
    if value is None:
        return
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise api_error(422, "VALIDATION_ERROR", f"Invalid {field}: not a UUID")

@router.get("/movement-types")
async def list_movement_types(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all supported movement types with their metrics."""
    from app.modules.video.models import MovementType, MovementMetric
    types = list((await db.scalars(select(MovementType))).all())
    result = []
    for mt in types:
        metrics = list((await db.scalars(select(MovementMetric).where(MovementMetric.movement_type == mt.code))).all())
        result.append({
            "code": mt.code,
            "display_name": mt.display_name,
            "camera_views": mt.camera_views,
            "phases": mt.phases,
            "metrics": [
                {
                    "metric_name": m.metric_name,
                    "plane": m.plane,
                    "confidence": m.confidence,
                    "unit": m.unit,
                    "description": m.description,
                } for m in metrics
            ]
        })
    return result

async def _get_or_create_benchmark_athlete(db: AsyncSession, current_user: User) -> str:
    """Finds or creates an athlete record for the current user so benchmark uploads never require manual athlete creation."""
    from datetime import date
    if current_user.role == UserRole.athlete:
        ath = await db.scalar(select(Athlete).where(Athlete.user_id == current_user.id))
        if ath:
            return ath.id
        ath = Athlete(
            user_id=current_user.id,
            sport_type="General",
            date_of_birth=date(2000, 1, 1),
        )
        db.add(ath)
        await db.commit()
        await db.refresh(ath)
        return ath.id

    # Coach, physiotherapist, scientist, admin:
    ath = await db.scalar(select(Athlete).where(
        Athlete.coach_id == current_user.id,
        Athlete.sport_type == "Benchmark Reference"
    ))
    if ath:
        return ath.id
    ath = await db.scalar(select(Athlete).where(Athlete.coach_id == current_user.id))
    if ath:
        return ath.id

    ath = Athlete(
        coach_id=current_user.id,
        sport_type="Benchmark Reference",
        position="Reference",
        date_of_birth=date(2000, 1, 1),
    )
    db.add(ath)
    await db.commit()
    await db.refresh(ath)
    return ath.id


@router.post("/upload-url", response_model=VideoUploadResponse)
async def create_upload_url(
    data: VideoUploadRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
):
    """Generate a mock presigned URL and create a pending video record."""
    target_athlete_id = data.athlete_id
    if not target_athlete_id:
        target_athlete_id = await _get_or_create_benchmark_athlete(db, current_user)
    else:
        athlete = await db.scalar(select(Athlete).where(Athlete.id == target_athlete_id))
        if not athlete:
            raise api_error(404, "NOT_FOUND", "Athlete not found")
        if not _can_access_athlete(current_user, athlete):
            raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")
        if current_user.role == UserRole.athlete and athlete.user_id != current_user.id:
            raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Athletes can only upload for themselves")

    if data.movement_type != AUTO:  # "auto" (both labels, enforced by the schema) is resolved from the footage by the worker
        # Validate movement_type exists
        from app.modules.video.models import MovementType
        mt = await db.scalar(select(MovementType).where(MovementType.code == data.movement_type))
        if not mt:
            raise api_error(400, "INVALID_MOVEMENT_TYPE", f"Unsupported movement type: {data.movement_type}")

        # Validate camera_view is allowed for this movement_type
        if data.camera_view not in mt.camera_views:
            raise api_error(400, "INVALID_CAMERA_VIEW", f"Camera view '{data.camera_view}' not supported for {mt.display_name}. Allowed: {mt.camera_views}")

    safe_name = _safe_filename(data.original_filename)
    video = Video(
        athlete_id=target_athlete_id,
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
    video_id: UuidPath,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Confirm upload, validate via ffprobe, and queue it for processing."""
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")

    if video.uploaded_by != current_user.id:
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Must be the creator to confirm upload")

    if video.processing_status != VideoProcessingStatus.pending_upload:   # a second confirm would queue (and store) the clip twice
        raise api_error(409, "ALREADY_CONFIRMED", f"This upload is already {video.processing_status.value}")

    local_path = os.path.join(settings.upload_dir, video.storage_key)
    if not os.path.exists(local_path):
        raise api_error(404, "NOT_FOUND", "File not found in storage")

    # Format validation
    if not video.original_filename.lower().endswith((".mp4", ".mov", ".webm", ".avi", ".mkv", ".m4v")):
        await _reject_upload(db, video, "invalid_format", "Only .mp4, .mov, .webm, .avi, .mkv or .m4v files are allowed", local_path)

    # Run ffprobe (PATH first, static-ffmpeg bundle fallback for hosts
    # without a system install — Docker images ship ffmpeg already)
    ffprobe_bin = shutil.which("ffprobe")
    if ffprobe_bin is None:
        try:
            from static_ffmpeg.run import get_or_fetch_platform_executables_else_raise
            _, ffprobe_bin = get_or_fetch_platform_executables_else_raise()
        except Exception as e:
            logger.error(f"no ffprobe available: {e}")
    if ffprobe_bin is None:
        await _reject_upload(db, video, "validator_unavailable", "Video validator (ffprobe) is not installed on this host", local_path)
    cmd = [
        ffprobe_bin, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration:format=duration",
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
        # WebM / Matroska carry no per-stream duration: fall back to the container's
        d = stream.get("duration")
        duration = float(d if d not in (None, "N/A") else data["format"]["duration"])
    except Exception as e:
        logger.error(f"ffprobe failed: {e}")
        await _reject_upload(db, video, "invalid_format", "Could not parse video format", local_path)

    # Validate limits
    file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
    if file_size_mb > settings.max_upload_mb:
        await _reject_upload(db, video, "file_too_large", f"File size is {file_size_mb:.1f} MB (exceeds {settings.max_upload_mb} MB limit)", local_path)

    if duration < settings.min_video_seconds or duration > settings.max_video_seconds:
        await _reject_upload(db, video, "duration_out_of_range",
                             f"Video duration is {duration:.1f}s (must be between {settings.min_video_seconds:g} and {settings.max_video_seconds:g}s)", local_path)

    if height < settings.min_video_height:
        await _reject_upload(db, video, "resolution_too_low",
                             f"Video resolution is {width}x{height} ({height}p). Minimum height required for biomechanical tracking is {settings.min_video_height}p.", local_path)

    video.resolution_width = width
    video.resolution_height = height
    video.fps = fps
    video.duration_seconds = duration

    # Commit BEFORE queueing: the job writes this row's status, and a write that lands first must not be overwritten.
    video.processing_status = VideoProcessingStatus.processing
    await db.commit()
    enqueue(video_id)

    return {"status": "processing"}


@router.post("/compare", response_model=CompareVideosResponse)
async def compare_videos_endpoint(
    req: CompareVideosRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Deep dual-video form benchmark and kinematic comparison."""
    try:
        return await compare_two_videos(
            db,
            video_a_id=req.video_a_id,
            video_b_id=req.video_b_id,
            run_gemini=req.run_gemini,
        )
    except ValueError as e:
        raise api_error(404, "NOT_FOUND", str(e))
    except Exception as e:
        logger.exception("Video comparison failed")
        raise api_error(500, "COMPARISON_FAILED", f"Comparison failed: {e}")


@router.get("/benchmark-presets")
async def list_benchmark_presets(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List pre-loaded benchmark clips and textbook standards for 1-click comparison."""
    db_videos = list((await db.scalars(
        select(Video)
        .where(Video.processing_status == VideoProcessingStatus.completed)
        .order_by(desc(Video.created_at))
        .limit(10)
    )).all())

    presets = [
        {
            "id": v.id,
            "title": f"{v.movement_type.capitalize()} Standard ({v.original_filename or 'Clip'})",
            "movement_type": v.movement_type,
            "camera_view": v.camera_view,
            "duration_seconds": v.duration_seconds,
            "is_builtin": True,
        }
        for v in db_videos
    ]

    standard_types = ["squatting", "jumping", "sprinting", "landing", "cutting", "throwing"]
    existing_types = {p["movement_type"] for p in presets}
    for st in standard_types:
        if st not in existing_types:
            presets.append({
                "id": f"textbook_{st}",
                "title": f"Textbook Ideal {st.capitalize()} (Biomechanical Standard)",
                "movement_type": st,
                "camera_view": "sagittal" if st in ("squatting", "sprinting", "running") else "frontal",
                "duration_seconds": 3.0,
                "is_builtin": True,
                "is_textbook": True,
            })

    return {"presets": presets}


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video_endpoint(
    video_id: UuidPath,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")

    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    return video


@router.get("/{video_id}/vector-posture", response_model=VectorPostureData)
async def get_vector_posture_endpoint(
    video_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get the SVG skeletal posture twin coordinates for a video at its peak inflection frame."""
    if video_id.startswith("textbook_"):
        movement_type = video_id.replace("textbook_", "")
        return get_textbook_ideal_landmarks(movement_type)

    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")

    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if athlete and not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    vector_dict = await extract_inflection_vector_for_video(db, video_id)
    return VectorPostureData(**vector_dict)

 
 
@router.post("/{video_id}/ai-observe")
async def ai_observe_video(
    video_id: UuidPath,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    fps: float = Query(4.0, ge=0.1, le=30.0),
    chunk_seconds: float | None = Query(None, ge=2.0, le=60.0),
):
    """Run qualitative multimodal video observation on stored clip and save to video.analysis."""
    import asyncio
    import importlib
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")

    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    local_path = os.path.join(settings.upload_dir, os.path.basename(video.storage_key))
    if not os.path.exists(local_path):
        local_path = os.path.join(settings.upload_dir, video.storage_key)
    if not os.path.exists(local_path):
        raise api_error(404, "NOT_FOUND", "Video file not found in storage")

    from app.modules.video.ai_service import run_gemini_observation_for_video
    observation = await run_gemini_observation_for_video(
        db, video, local_path=local_path, fps=fps, chunk_seconds=chunk_seconds
    )
    if not observation:
        raise api_error(502, "OBSERVATION_FAILED", "Video observation could not be completed with Gemini")

    return observation




@router.get("/{video_id}/file")
async def get_video_file(
    video_id: UuidPath,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")
    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")
    path = os.path.join(settings.upload_dir, video.storage_key)
    if not os.path.exists(path):
        raise api_error(404, "NOT_FOUND", "File not found")
    return FileResponse(path, media_type="video/mp4")


@router.get("/{video_id}/thumbnail")
async def get_video_thumbnail(
    video_id: UuidPath,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video or not video.thumbnail_key:
        raise api_error(404, "NOT_FOUND", "Not found")
    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")
    if not os.path.exists(video.thumbnail_key):
        raise api_error(404, "NOT_FOUND", "File not found")
    return FileResponse(video.thumbnail_key, media_type="image/jpeg")


@router.get("/{video_id}/annotated")
async def get_annotated_video(
    video_id: UuidPath,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")
    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")
    if not video.annotated_video_key or not os.path.exists(video.annotated_video_key):
        raise api_error(404, "NOT_FOUND", "Annotated video not available")
    return FileResponse(video.annotated_video_key, media_type="video/mp4")


@router.get("", response_model=VideoListResponse)
async def list_videos(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    athlete_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    _ensure_uuid_or_422(athlete_id)
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

    return VideoListResponse(items=videos, total=total or 0, page=page, page_size=page_size)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: UuidPath,
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.coach))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")

    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")
    if current_user.role == UserRole.coach and athlete.coach_id != current_user.id:
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    # Clean up local storage files (storage_key is bare; thumbnail/annotated are absolute paths)
    for key in filter(None, [video.storage_key, video.thumbnail_key, video.annotated_video_key]):
        path = key if os.path.isabs(key) else os.path.join(settings.upload_dir, os.path.basename(key))
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    await db.delete(video)
    await db.commit()


@router.get("/{video_id}/biomechanics", response_model=BiomechanicsResponse)
async def get_biomechanics(
    video_id: UuidPath,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")

    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    # Hero stats query
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
    video_id: UuidPath,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")

    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    frames = list((await db.scalars(
        select(BiomechanicalMetric)
        .where(BiomechanicalMetric.video_id == video_id)
        .order_by(BiomechanicalMetric.frame_number)
    )).all())

    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["frame_number", "metric_name", "value", "plane", "confidence", "movement_phase"])
    for r in frames:
        writer.writerow([r.frame_number, r.metric_name, r.metric_value, r.plane, r.confidence, r.movement_phase or ""])

    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="video_{video_id}_metrics.csv"'},
    )

