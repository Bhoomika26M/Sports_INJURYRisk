"""AI Video Observation Service.

Coordinates multimodal video observation via scripts.gemini_video and manages
saving observations into video.analysis for baseline-free scoring and visual feedback.
"""

import asyncio
import importlib
import logging
import os
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.risk_scoring.baselines import min_baseline_athletes, min_baseline_videos
from app.modules.risk_scoring.features import fetch_baseline_set
from app.modules.video.models import Video

logger = logging.getLogger(__name__)


async def check_baseline_sufficiency(
    db: AsyncSession,
    movement_type: str,
    exclude_video_id: str | None = None,
    required_features: list[str] | None = None,
) -> tuple[bool, int, int, int, int]:
    """Check if the movement type has enough completed peer videos and athletes.

    Returns:
        (is_sufficient, have_videos, need_videos, have_athletes, need_athletes)
    """
    need_v = min_baseline_videos()
    need_a = min_baseline_athletes()
    req = sorted(required_features) if required_features else []

    exclude_id = str(exclude_video_id) if exclude_video_id else "00000000-0000-0000-0000-000000000000"
    try:
        baseline = await fetch_baseline_set(db, movement_type, exclude_id, req)
        have_v = baseline.videos
        have_a = baseline.athletes
    except Exception as e:
        logger.warning(f"Error checking baseline set for {movement_type}: {e}")
        have_v, have_a = 0, 0

    is_sufficient = (have_v >= need_v and have_a >= need_a)
    return is_sufficient, have_v, need_v, have_a, need_a


def _build_kinematic_context(video: Video, analysis: dict[str, Any] | None) -> str | None:
    """Ground Gemini observation with pose tracking metrics when available."""
    kin_summary = []
    if video.movement_type:
        kin_summary.append(f"Movement: {video.movement_type}")
    if video.camera_view:
        kin_summary.append(f"Camera plane: {video.camera_view}")

    an = analysis or video.analysis or {}
    reps_data = (an.get("movement") or {}).get("reps")
    if reps_data and "reps" in reps_data:
        kin_summary.append(f"Pose tracking rep count: {len(reps_data['reps'])}")
    q_rep = an.get("quality") or {}
    if q_rep.get("usable_pct") is not None:
        kin_summary.append(f"Landmark visibility coverage: {q_rep.get('usable_pct')}%")

    return "; ".join(kin_summary) if kin_summary else None


async def run_gemini_observation_for_video(
    db: AsyncSession,
    video: Video,
    local_path: str | None = None,
    kinematic_context: str | None = None,
    fps: float = 4.0,
    chunk_seconds: float | None = None,
) -> dict[str, Any] | None:
    """Run Gemini multimodal observation and save result to video.analysis.

    Returns existing cached observation if already present, or executes
    observation and commits to the database.
    """
    current_analysis = dict(video.analysis or {})
    obs_key = "gemini_observation"

    # Return cached observation if already present
    if current_analysis.get(obs_key):
        return current_analysis[obs_key]

    try:
        ai_mod = importlib.import_module("scripts.gemini_video")
    except Exception as e:
        logger.error(f"Could not import scripts.gemini_video: {e}")
        return None

    ai_key = ai_mod.get_key()
    if not ai_key:
        logger.info(f"Gemini API key not configured; skipping AI observation for video {video.id}")
        return None

    # Resolve local video path
    resolved_path = local_path
    if not resolved_path:
        # Check both direct filename and basename in upload_dir
        candidate = os.path.join(settings.upload_dir, os.path.basename(video.storage_key))
        if os.path.exists(candidate):
            resolved_path = candidate
        else:
            candidate_raw = os.path.join(settings.upload_dir, video.storage_key)
            if os.path.exists(candidate_raw):
                resolved_path = candidate_raw

    if not resolved_path or not os.path.exists(resolved_path):
        logger.warning(f"Video file not found for video {video.id} (storage_key={video.storage_key})")
        return None

    context = kinematic_context or _build_kinematic_context(video, current_analysis)

    def _do_observe() -> dict[str, Any]:
        with ai_mod.make_client(ai_key) as client:
            return ai_mod.analyze(
                resolved_path,
                client,
                height=480,
                fps=fps,
                media_resolution="high",
                chunk_seconds=chunk_seconds,
                models=ai_mod.MODELS,
                movement=video.movement_type,
                kinematic_context=context,
            )

    try:
        logger.info(f"Starting Gemini video observation for video {video.id} ({video.movement_type})...")
        observation = await asyncio.to_thread(_do_observe)
    except Exception as e:
        logger.warning(f"Gemini observation execution failed for video {video.id}: {e}")
        return None

    if observation:
        current_analysis[obs_key] = observation
        video.analysis = current_analysis
        await db.execute(
            update(Video)
            .where(Video.id == video.id)
            .values(analysis=current_analysis)
        )
        await db.commit()
        logger.info(f"Gemini observation successfully saved for video {video.id} (model={observation.get('model')})")
        return observation

    return None

