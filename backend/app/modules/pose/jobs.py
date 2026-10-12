"""In-process video job runner: one clip at a time, inside the API process. Replaces Redis + arq.

The analysis is CPU-bound and one machine does one clip at a time anyway, so a broker and a second copy of the
ML stack (torch + mediapipe, ~1.5 GB) only added processes that could fail to start. Videos left `processing`
when the process died are re-queued from the database on the next start, so nothing stays stuck.
ponytail: single process, in-memory queue. Past one API instance, put a real queue back.
"""

import asyncio
import logging

from sqlalchemy import select

from app.database import async_session_factory
from app.modules.pose.tasks import process_video, update_video_status
from app.modules.video.models import Video, VideoProcessingStatus

logger = logging.getLogger(__name__)

JOB_TIMEOUT_S = 1800     # a 60 s clip on a CPU-only laptop finishes well inside this; a hang must not block the queue

_queue: asyncio.Queue[str] = asyncio.Queue()
_ctx: dict = {}          # the YOLO model, loaded once and reused by every job
_runner: asyncio.Task | None = None


def enqueue(video_id: str) -> None:
    _queue.put_nowait(str(video_id))


async def _ensure_models() -> None:
    if "yolo_model" not in _ctx:
        from app.modules.pose.pipeline import load_models   # imported late: pulls in torch
        _ctx["yolo_model"] = await asyncio.to_thread(load_models)


async def _run() -> None:
    try:
        await _ensure_models()   # warm up now so the first upload does not pay for the imports
    except Exception as e:  # noqa: BLE001 — retried (and reported on the video) when a job needs it
        logger.warning(f"could not load the pose models yet: {e}")
    while True:
        video_id = await _queue.get()
        try:
            try:
                await _ensure_models()
            except Exception as e:  # noqa: BLE001 — fail in seconds, not after a tracking pass that needs them
                logger.exception("pose models unavailable")
                async with async_session_factory() as db:
                    await update_video_status(
                        db, video_id, VideoProcessingStatus.failed, error_code="models_unavailable",
                        error_message=f"The pose models could not be loaded ({e}). Run `python scripts/fetch_models.py` "
                                      "once with internet access, then upload again.")
                continue
            await asyncio.wait_for(process_video(_ctx, video_id), JOB_TIMEOUT_S)   # marks the video failed itself on error
        except asyncio.TimeoutError:
            logger.error(f"video {video_id} timed out after {JOB_TIMEOUT_S}s")
            async with async_session_factory() as db:
                await update_video_status(db, video_id, VideoProcessingStatus.failed, error_code="timeout",
                                          error_message="Processing took too long and was stopped.")
        except Exception:  # noqa: BLE001 — one bad clip must not stop the runner
            logger.exception(f"video {video_id} failed")
        finally:
            _queue.task_done()


async def start() -> None:
    """Re-queue videos a previous run left `processing`, then start working."""
    global _runner
    async with async_session_factory() as db:
        stuck = (await db.scalars(select(Video.id).where(
            Video.processing_status == VideoProcessingStatus.processing).order_by(Video.created_at))).all()
    for video_id in stuck:
        enqueue(video_id)
    if stuck:
        logger.info(f"re-queued {len(stuck)} video(s) left processing by the previous run")
    _runner = asyncio.create_task(_run())


async def stop() -> None:
    if _runner:
        _runner.cancel()
