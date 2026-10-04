"""Re-derive metrics + analysis for already-processed videos from their STORED raw landmarks.

Pose extraction (the slow, model-bound step) is NOT repeated: `pose_frames` keeps the raw
landmarks, so cleaning, metrics, movement analysis and the quality report can be recomputed
whenever the analysis improves. Use after upgrading the engine so old videos get the new
conventions (e.g. hip flexion, trunk lean) and gating.
"""

from __future__ import annotations

import logging

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pose.processing import analyze_frames
from app.modules.video.models import BiomechanicalMetric, PoseFrame, Video, VideoProcessingStatus

logger = logging.getLogger(__name__)


async def reprocess_video(db: AsyncSession, video: Video) -> dict:
    rows = (await db.scalars(
        select(PoseFrame).where(PoseFrame.video_id == video.id).order_by(PoseFrame.frame_number)
    )).all()
    if not rows:
        return {"video_id": video.id, "status": "skipped", "reason": "no stored pose frames"}

    frames = []
    for r in rows:
        kp = dict(r.keypoints)
        vis = kp.pop("_vis", None)
        frames.append({"frame_number": r.frame_number, "timestamp_ms": r.timestamp_ms,
                       "world_landmarks": kp, "visibility": vis})

    fps = float(video.fps) if video.fps else None
    metrics, analysis = analyze_frames(frames, video.movement_type, video.camera_view, fps,
                                       {"frames_processed": len(frames)})

    await db.execute(delete(BiomechanicalMetric).where(BiomechanicalMetric.video_id == video.id))
    if metrics:
        await db.execute(insert(BiomechanicalMetric), [
            {"video_id": video.id, "frame_number": m["frame_number"], "metric_name": m["name"],
             "metric_value": m["value"], "plane": m["plane"], "confidence": m["confidence"],
             "movement_phase": m.get("phase")} for m in metrics
        ])
    video.analysis = analysis
    await db.commit()
    return {"video_id": video.id, "status": "reprocessed", "metrics": len(metrics),
            "grade": analysis["quality"]["grade"]}


async def reprocess_all(db: AsyncSession, video_id: str | None = None, dry_run: bool = False) -> list[dict]:
    q = select(Video).where(Video.processing_status == VideoProcessingStatus.completed)
    if video_id:
        q = q.where(Video.id == video_id)
    results = []
    for video in (await db.scalars(q)).all():
        if dry_run:
            n = len((await db.scalars(select(PoseFrame.id).where(PoseFrame.video_id == video.id))).all())
            results.append({"video_id": video.id, "status": "dry-run", "stored_frames": n})
            continue
        try:
            results.append(await reprocess_video(db, video))
        except Exception as e:  # noqa: BLE001 — one bad video must not stop the batch
            await db.rollback()
            logger.exception("reprocess failed for %s", video.id)
            results.append({"video_id": video.id, "status": "error", "error": str(e)})
    return results
