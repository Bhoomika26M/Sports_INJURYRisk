"""Video processing worker task — YOLO tracking + MediaPipe pose + biomechanics."""

import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select, update

from app.database import async_session_factory
from app.modules.users.models import User
from app.modules.athletes.models import Athlete, InjuryHistory, TrainingLoadEntry
from app.modules.video.models import Video, VideoProcessingStatus, PoseFrame, BiomechanicalMetric
from app.modules.risk_scoring.models import MovementBaseline, RiskScore
from app.modules.recommendations.models import Recommendation
from app.modules.pose.pipeline import track_persons, run_mediapipe_full_pass, extract_thumbnail
from app.modules.biomechanics.calculations import (
    knee_flexion_angle, trunk_lean_angle, knee_valgus_flag, limb_symmetry_index, METRIC_CONFIDENCE
)
from app.modules.biomechanics.registry import get_calculator

logger = logging.getLogger(__name__)


class VideoProcessingError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def now():
    return datetime.now(tz=ZoneInfo("UTC"))


async def update_video_status(db, video_id: str, status: str, **kwargs):
    update_data = {"processing_status": status}
    update_data.update(kwargs)
    await db.execute(update(Video).where(Video.id == video_id).values(**update_data))
    await db.commit()


async def get_video(db, video_id: str) -> Video:
    result = await db.execute(select(Video).where(Video.id == video_id))
    return result.scalar_one()


async def download_from_storage(storage_key: str) -> str:
    """For local development, the 'storage_key' is the file path inside /uploads."""
    path = os.path.join("/uploads", os.path.basename(storage_key))
    if not os.path.exists(path):
        raise VideoProcessingError("storage_error", f"File not found at {path}")
    return path


def cleanup_local_file(local_path: str):
    """Clean up local temp file. For local dev with /uploads, we leave it since it's the only copy."""
    pass


async def update_video_progress(db, video_id: str, progress_pct: int):
    await db.execute(update(Video).where(Video.id == video_id).values(progress_pct=progress_pct))
    await db.commit()


async def store_pose_frames(db, video_id: str, frame_results: list[dict]):
    frames = [
        PoseFrame(
            video_id=video_id,
            frame_number=fr["frame_number"],
            timestamp_ms=fr["timestamp_ms"],
            keypoints=fr["world_landmarks"],
            model_used="mediapipe"
        )
        for fr in frame_results
    ]
    db.add_all(frames)
    await db.commit()


def compute_biomechanics(frame_results: list[dict], calculator, camera_view: str) -> list[dict]:
    """Compute biomechanics using the movement-type-specific calculator."""
    metrics = []
    failed_frames = 0

    for fr in frame_results:
        landmarks = fr["world_landmarks"]
        f_num = fr["frame_number"]

        try:
            frame_metrics = calculator.compute_all(landmarks, camera_view)
            for m in frame_metrics:
                m["frame_number"] = f_num
                metrics.append(m)
        except KeyError as e:
            failed_frames += 1
            logger.warning(f"Frame {f_num}: missing landmark {e}, skipping this frame's biomechanics")
            continue

    if failed_frames:
        logger.info(f"compute_biomechanics: {failed_frames}/{len(frame_results)} frames had missing landmarks")
    if not metrics and frame_results:
        logger.error(f"compute_biomechanics produced ZERO metrics from {len(frame_results)} frames — investigate immediately")

    return metrics


async def store_biomechanical_metrics(db, video_id: str, metrics: list[dict]):
    db_metrics = [
        BiomechanicalMetric(
            video_id=video_id,
            frame_number=m["frame_number"],
            metric_name=m["name"],
            metric_value=m["value"],
            plane=m["plane"],
            confidence=m["confidence"],
            movement_phase=m.get("phase"),
        )
        for m in metrics
    ]
    db.add_all(db_metrics)
    await db.commit()


async def process_video(ctx: dict, video_id: str) -> dict:
    """
    arq worker task. Enqueued automatically by confirm-upload on successful validation.
    Timeout: 5 minutes (pessimistic — arq marks it failed and does not silently hang).
    Retries: up to 2 on unhandled exceptions; VideoProcessingError is NOT retried
    (it means the video itself is the problem, not a transient failure — retrying won't fix it).
    """
    async with async_session_factory() as db:
        local_path = None
        try:
            await update_video_status(db, video_id, VideoProcessingStatus.processing, processing_started_at=now())
            video = await get_video(db, video_id)
            local_path = await download_from_storage(video.storage_key)

            # Step 1 — YOLO tracking across every frame: count people AND lock
            # onto the main athlete (most frames present, largest box on ties) so
            # multi-person videos analyze one consistent person instead of
            # failing. See docs/DECISIONS.md (multi-person tracking).
            tracking = track_persons(local_path, ctx.get("yolo_model"), stride=1)
            person_counts = tracking["person_counts"]
            if tracking["max_persons"] == 0:
                raise VideoProcessingError("no_person_detected", "No person detected in any frame.")
            main_track_id = tracking["main_track_id"]
            subject_boxes: dict[int, tuple | None] | None = None
            if main_track_id is not None:
                main_frames = tracking["tracks"][main_track_id]
                subject_boxes = {i: main_frames.get(i) for i in range(tracking["frames_processed"])}
                coverage = len(main_frames) / max(1, tracking["frames_processed"])
                logger.info(
                    f"Tracking {tracking['max_persons']} person(s), main subject is track {main_track_id} "
                    f"(present in {len(main_frames)}/{tracking['frames_processed']} frames, {coverage:.0%} coverage)"
                )
            else:
                logger.warning("No track IDs available — running untracked full-frame pose")

            # Generate thumbnail before long processing starts
            thumbnail_filename = f"thumb_{video_id}.jpg"
            thumbnail_path = os.path.join("/uploads", thumbnail_filename)
            try:
                extract_thumbnail(local_path, thumbnail_path)
                await update_video_status(db, video_id, VideoProcessingStatus.processing, thumbnail_key=thumbnail_path)
            except Exception as e:
                logger.warning(f"Thumbnail generation failed for {video_id}, continuing without it: {e}")

            annotated_filename = f"annotated_{video_id}.mp4"
            annotated_path = os.path.join("/uploads", annotated_filename)

            # Define progress callback for MediaPipe
            async def _progress(pct):
                await update_video_progress(db, video_id, pct)

            import asyncio
            loop = asyncio.get_running_loop()
            def sync_progress(pct):
                asyncio.run_coroutine_threadsafe(_progress(pct), loop)

            # Step 2 — full MediaPipe pass, every frame, world landmarks only.
            # Frames with a tracked-subject box are cropped to the main athlete.
            frame_results, detection_rate = await loop.run_in_executor(
                None,
                lambda: run_mediapipe_full_pass(
                    local_path,
                    annotate_output_path=annotated_path,
                    progress_callback=sync_progress,
                    subject_boxes=subject_boxes,
                )
            )

            if detection_rate < 0.70:
                raise VideoProcessingError(
                    "low_detection_quality",
                    f"Pose detected in only {detection_rate:.0%} of frames — below the 70% floor. "
                    f"Check lighting, framing, and that the full body is in view."
                )

            await store_pose_frames(db, video_id, frame_results)

            # Step 3 — biomechanics from world landmarks using movement-type calculator
            calculator = get_calculator(video.movement_type)
            metrics = compute_biomechanics(frame_results, calculator, camera_view=video.camera_view)
            await store_biomechanical_metrics(db, video_id, metrics)

            await update_video_status(
                db, video_id, VideoProcessingStatus.completed,
                processing_completed_at=now(),
                person_count_detected=max(person_counts),
                detection_rate=detection_rate,
                annotated_video_key=annotated_path,
                progress_pct=100
            )
            return {
                "status": "completed",
                "frames_processed": len(frame_results),
                "tracked_subject_id": main_track_id,
                "max_persons": max(person_counts, default=0),
            }

        except VideoProcessingError as e:
            await update_video_status(db, video_id, VideoProcessingStatus.failed, error_code=e.code, error_message=e.message)
            return {"status": "failed", "reason": e.code}
        except Exception as e:
            logger.exception(f"Unexpected error processing video {video_id}")
            await update_video_status(db, video_id, VideoProcessingStatus.failed, error_code="internal_error", error_message=str(e))
            raise
        finally:
            if local_path:
                cleanup_local_file(local_path)