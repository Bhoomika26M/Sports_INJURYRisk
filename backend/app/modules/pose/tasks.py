"""Video processing worker task — YOLO tracking + MediaPipe pose + biomechanics."""

import asyncio
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select, update

from app.config import settings
from app.database import async_session_factory
from app.modules.users.models import User
from app.modules.athletes.models import Athlete, InjuryHistory, TrainingLoadEntry
from app.modules.video.models import Video, VideoProcessingStatus, PoseFrame, BiomechanicalMetric
from app.modules.risk_scoring.models import MovementBaseline, RiskScore
from app.modules.recommendations.models import Recommendation
from app.modules.pose.pipeline import (
    track_persons, run_mediapipe_full_pass, extract_thumbnail, compute_stride, probe_video,
    detect_every, subject_boxes_for,
)
from app.modules.pose.coverage import assess_coverage, summarize_tracking
from app.modules.pose.processing import analyze_frames, compute_biomechanics, identify_labels  # noqa: F401  (compute_biomechanics re-exported)
from app.modules.biomechanics.classification import AUTO
from app.modules.biomechanics.calculations import (
    knee_flexion_angle, trunk_lean_angle, knee_valgus_flag, limb_symmetry_index, METRIC_CONFIDENCE
)
from app.modules.biomechanics.registry import get_calculator

logger = logging.getLogger(__name__)


class VideoProcessingError(Exception):
    """The video itself is the problem. ``person_count_detected`` / ``detection_rate`` are persisted with
    the failure so the UI can explain it (previously both were NULL on every failed video)."""

    def __init__(self, code: str, message: str, *, person_count_detected: int | None = None,
                 detection_rate: float | None = None):
        self.code = code
        self.message = message
        self.person_count_detected = person_count_detected
        self.detection_rate = detection_rate
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
    """For local development, the 'storage_key' is the file path inside settings.upload_dir."""
    path = os.path.join(settings.upload_dir, os.path.basename(storage_key))
    if not os.path.exists(path):
        raise VideoProcessingError("storage_error", f"File not found at {path}")
    return path


def cleanup_local_file(local_path: str):
    """Clean up local temp file. For local dev with the upload dir, we leave it since it's the only copy."""
    pass


async def update_video_progress(db, video_id: str, progress_pct: int):
    await db.execute(update(Video).where(Video.id == video_id).values(progress_pct=progress_pct))
    await db.commit()


def _keypoints_payload(fr: dict) -> dict:
    """Raw world landmarks {"0": [x,y,z], ...} plus "_vis": per-landmark visibility list.

    Stored RAW (no smoothing/cleaning) so analysis is reproducible from the database.
    The "_vis" key is additive: readers that index landmarks by "0".."32" are unaffected.
    """
    payload = dict(fr["world_landmarks"])
    if fr.get("visibility") is not None:
        payload["_vis"] = [round(float(v), 3) for v in fr["visibility"]]
    return payload


async def store_pose_frames(db, video_id: str, frame_results: list[dict]):
    frames = [
        PoseFrame(
            video_id=video_id,
            frame_number=fr["frame_number"],
            timestamp_ms=fr["timestamp_ms"],
            keypoints=_keypoints_payload(fr),
            model_used="mediapipe"
        )
        for fr in frame_results
    ]
    db.add_all(frames)
    await db.commit()


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
    Job body, run by app.modules.pose.jobs after confirm-upload validated the file. Every failure marks the video
    `failed` with a code (nothing stays `processing`); there are no automatic retries, because re-running a
    multi-minute pass cannot fix a bad clip or a missing model.
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
            fps = float(video.fps) if video.fps else probe_video(local_path)["fps"]
            # Slow-motion clips (>60 fps) are processed every Nth frame; tracking and pose
            # must use the same stride so subject boxes line up with processed frames.
            stride = compute_stride(fps)

            # Progress callbacks run on a worker thread while this coroutine awaits the executor, so they MUST NOT
            # touch this job's `db` session (two coroutines on one AsyncSession raise IllegalStateChangeError):
            # each write gets its own short-lived session. Tracking is 0-40 %, pose 40-95 %, storing the rest.
            loop = asyncio.get_running_loop()

            async def _progress(pct):
                async with async_session_factory() as progress_db:
                    await update_video_progress(progress_db, video_id, pct)

            def progress_between(lo, hi):
                last = [-1]

                def report(pct):
                    value = lo + (hi - lo) * min(pct, 100) // 100
                    if value - last[0] >= 2:
                        last[0] = value
                        asyncio.run_coroutine_threadsafe(_progress(value), loop)
                return report

            # Blocking model work runs in a thread: on the API process an inline call would freeze every request.
            every = detect_every(fps, stride)
            tracking = await loop.run_in_executor(None, lambda: track_persons(
                local_path, ctx.get("yolo_model"), stride=stride, fps=fps, every=every,
                progress_callback=progress_between(0, 40)))
            person_counts = tracking["person_counts"]
            if tracking["max_persons"] == 0:
                raise VideoProcessingError(
                    "no_person_detected", "No person detected in any frame.",
                    person_count_detected=0, detection_rate=0.0,
                )
            main_track_id = tracking["main_track_id"]
            summary = summarize_tracking(tracking)
            logger.info(
                f"Coverage inputs for {video_id}: {summary.substantive_tracks} substantive track(s) of "
                f"{summary.tracks_seen} ID(s), max {summary.max_persons} in one frame, subject height "
                f"{summary.subject_height_px} px, main track coverage {summary.main_track_coverage:.0%}"
            )
            subject_boxes: dict[int, tuple | None] | None = None
            if main_track_id is not None:
                main_frames = tracking["tracks"][main_track_id]
                # YOLO ran every `step` frames: boxes for the frames in between are interpolated (see subject_boxes_for)
                subject_boxes = subject_boxes_for(main_frames, tracking["frames_processed"], tracking.get("step", 1))
                logger.info(
                    f"Tracking {tracking['max_persons']} person(s), main subject is track {main_track_id} "
                    f"(followed in {summary.main_track_coverage:.0%} of {summary.frames_processed} tracked frames)"
                )
            else:
                logger.warning("No track IDs available — running untracked full-frame pose")

            # Generate thumbnail before long processing starts
            thumbnail_filename = f"thumb_{video_id}.jpg"
            thumbnail_path = os.path.join(settings.upload_dir, thumbnail_filename)
            try:
                extract_thumbnail(local_path, thumbnail_path)
                await update_video_status(db, video_id, VideoProcessingStatus.processing, thumbnail_key=thumbnail_path)
            except Exception as e:
                logger.warning(f"Thumbnail generation failed for {video_id}, continuing without it: {e}")

            annotated_filename = f"annotated_{video_id}.mp4"
            annotated_path = os.path.join(settings.upload_dir, annotated_filename)

            # Step 2 — full MediaPipe pass, every frame, world landmarks only.
            # Frames with a tracked-subject box are cropped to the main athlete.
            diagnostics: dict = {}
            frame_results, detection_rate = await loop.run_in_executor(
                None,
                lambda: run_mediapipe_full_pass(
                    local_path,
                    annotate_output_path=annotated_path,
                    progress_callback=progress_between(40, 95),
                    subject_boxes=subject_boxes,
                    diagnostics=diagnostics,
                    stride=stride,
                    # Several people: never fall back to full-frame pose on frames where the athlete is
                    # untracked, or another person gets measured as the athlete.
                    full_frame_fallback=not summary.multi_person,
                )
            )

            assessment = assess_coverage(summary, detection_rate)
            if assessment.outcome == "reject":
                raise VideoProcessingError(
                    assessment.code, assessment.message,
                    person_count_detected=max(person_counts), detection_rate=detection_rate,
                )
            # "partial" is accepted with an explicit caveat; "ok" carries a note only for multi-person clips.

            # An "auto" upload declared no labels: the footage decides, or the upload fails (before anything is stored).
            movement_type, camera_view, auto = video.movement_type, video.camera_view, video.movement_type == AUTO
            if auto:
                labels = identify_labels(frame_results, fps)
                if labels is None:
                    raise VideoProcessingError(
                        "movement_not_identified",
                        "The movement and camera angle could not be identified confidently from this clip. "
                        "Upload it again and choose them yourself.",
                    )
                movement_type, camera_view = labels
                await update_video_status(db, video_id, VideoProcessingStatus.processing,
                                          movement_type=movement_type, camera_view=camera_view)

            await store_pose_frames(db, video_id, frame_results)

            # Step 3 — clean landmarks (visibility gating, gap-fill, despike, smoothing), compute
            # movement-type metrics, movement-specific analysis and the quality report.
            metrics, analysis = analyze_frames(frame_results, movement_type, camera_view, fps, diagnostics, auto=auto)
            await store_biomechanical_metrics(db, video_id, metrics)

            # Step 4 — Run AI Multimodal Observation automatically if API key is present
            try:
                import importlib
                _mod_name = "scripts.gemini_video"
                ai_mod = importlib.import_module(_mod_name)
                ai_key = getattr(ai_mod, "get_key")()
                if ai_key:
                    make_client = getattr(ai_mod, "make_client")
                    analyze_func = getattr(ai_mod, "analyze")
                    candidate_models = getattr(ai_mod, "MODELS")

                    # Ground the AI observation with precise kinematic data from the pose estimation pass
                    kin_summary = []
                    if movement_type:
                        kin_summary.append(f"Movement: {movement_type}")
                    if camera_view:
                        kin_summary.append(f"Camera plane: {camera_view}")
                    reps_data = (analysis.get("movement") or {}).get("reps")
                    if reps_data and "reps" in reps_data:
                        kin_summary.append(f"Pose tracking rep count: {len(reps_data['reps'])}")
                    if metrics:
                        l_knees = [m["metric_value"] for m in metrics if m.get("metric_name") == "knee_flexion_angle_left"]
                        r_knees = [m["metric_value"] for m in metrics if m.get("metric_name") == "knee_flexion_angle_right"]
                        if l_knees:
                            kin_summary.append(f"Peak left knee flexion: {max(l_knees):.1f}°")
                        if r_knees:
                            kin_summary.append(f"Peak right knee flexion: {max(r_knees):.1f}°")
                        trunks = [m["metric_value"] for m in metrics if m.get("metric_name") == "trunk_lean_angle"]
                        if trunks:
                            kin_summary.append(f"Max trunk lean: {max(trunks):.1f}°")
                    q_rep = analysis.get("quality") or {}
                    if q_rep.get("usable_pct") is not None:
                        kin_summary.append(f"Landmark visibility coverage: {q_rep.get('usable_pct')}%")
                    kin_context = "; ".join(kin_summary) if kin_summary else None

                    def _call_ai():
                        with make_client(ai_key) as client:
                            return analyze_func(
                                local_path, client, height=480, fps=4.0, media_resolution="high",
                                models=candidate_models, movement=movement_type,
                                kinematic_context=kin_context
                            )
                    ai_obs = await loop.run_in_executor(None, _call_ai)
                    if ai_obs:
                        _obs_key = "gemini_observation"
                        analysis[_obs_key] = ai_obs
            except Exception as e:
                logger.warning(f"Automatic multimodal video observation failed for {video_id}: {e}")

            await update_video_status(
                db, video_id, VideoProcessingStatus.completed,
                processing_completed_at=now(),
                person_count_detected=max(person_counts),
                detection_rate=detection_rate,
                coverage_caveat=assessment.caveat,
                annotated_video_key=annotated_path if os.path.exists(annotated_path) else None,   # none when there was no encoder
                analysis=analysis,
                progress_pct=100
            )
            return {
                "status": "completed",
                "frames_processed": len(frame_results),
                "tracked_subject_id": main_track_id,
                "max_persons": max(person_counts, default=0),
                "coverage": assessment.outcome,
            }

        except VideoProcessingError as e:
            diagnostics = {}
            if e.person_count_detected is not None:
                diagnostics["person_count_detected"] = e.person_count_detected
            if e.detection_rate is not None:
                diagnostics["detection_rate"] = e.detection_rate
            await update_video_status(
                db, video_id, VideoProcessingStatus.failed, error_code=e.code, error_message=e.message, **diagnostics
            )
            return {"status": "failed", "reason": e.code}
        except Exception as e:
            logger.exception(f"Unexpected error processing video {video_id}")
            await update_video_status(db, video_id, VideoProcessingStatus.failed, error_code="internal_error", error_message=str(e))
            raise
        finally:
            if local_path:
                cleanup_local_file(local_path)