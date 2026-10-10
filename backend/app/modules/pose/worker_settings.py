from arq.connections import RedisSettings

from app.config import settings
from app.modules.pose.tasks import process_video

def redis_settings_from_env() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)

from ultralytics import YOLO

async def startup(ctx):
    # Use yolov8n-pose.pt as yolo26n-pose.pt does not exist in ultralytics yet
    ctx["yolo_model"] = YOLO("yolov8n-pose.pt")

class WorkerSettings:
    functions = [process_video]
    on_startup = startup
    redis_settings = redis_settings_from_env()
    # Per-job wall clock. The shipped image is CPU-only (see backend/Dockerfile), where a 60 s clip at
    # 30 fps is ~1800 frames of YOLO tracking + MediaPipe pose, well past arq's 300 s default. 30 minutes
    # covers the longest accepted clip with headroom; a GPU host finishes in a fraction of this.
    job_timeout = 1800
    # Process one clip at a time. Each job loads YOLO + MediaPipe and runs its own executor thread,
    # so arq's default concurrency of 10 oversubscribes the CPU and RAM (the container is CPU-only).
    max_jobs = 1
    max_tries = 3              # 1 original attempt + 2 retries
    keep_result = 3600         # job result available for 1 hour