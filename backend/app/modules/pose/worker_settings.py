import os
from arq.connections import RedisSettings

from app.modules.pose.tasks import process_video

def redis_settings_from_env() -> RedisSettings:
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379")
    # Parse standard redis URL
    import urllib.parse
    url = urllib.parse.urlparse(redis_url)
    host = url.hostname or "redis"
    port = url.port or 6379
    password = url.password
    return RedisSettings(host=host, port=port, password=password)

from ultralytics import YOLO

async def startup(ctx):
    # Use yolov8n-pose.pt as yolo26n-pose.pt does not exist in ultralytics yet
    ctx["yolo_model"] = YOLO("yolov8n-pose.pt")

class WorkerSettings:
    functions = [process_video]
    on_startup = startup
    redis_settings = redis_settings_from_env()
    job_timeout = 300          # 5 minutes, pessimistic
    max_tries = 3               # 1 original attempt + 2 retries
    keep_result = 3600           # job result available for 1 hour
