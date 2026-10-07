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
    job_timeout = 300          # 5 minutes, pessimistic
    max_tries = 3              # 1 original attempt + 2 retries
    keep_result = 3600         # job result available for 1 hour