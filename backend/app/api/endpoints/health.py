import os
import sys
import time
import shutil
import platform
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.core.config import settings

router = APIRouter()

APP_START_TIME = time.time()

@router.get("/health")
def health_check():
    """Standard healthcheck reporting basic service availability."""
    return {"status": "ok", "message": "Backend is healthy"}

@router.get("/health/live")
def liveness_probe():
    """Kubernetes/Container liveness probe to verify server event loop is responsive."""
    return {"status": "alive", "uptime_seconds": round(time.time() - APP_START_TIME, 1)}

@router.get("/health/ready")
def readiness_probe(db: Session = Depends(get_db)):
    """
    Readiness probe verifying that all subsystem dependencies are operable:
    1. Database connectivity
    2. Uploads storage write permissions
    3. Biomechanics ML models presence
    """
    checks = {}
    is_ready = True

    # 1. Database check
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"status": "connected", "type": db.bind.dialect.name}
    except Exception as e:
        checks["database"] = {"status": "unreachable", "error": str(e)}
        is_ready = False

    # 2. Storage write permission check
    try:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        probe_file = os.path.join(settings.UPLOAD_DIR, ".write_probe")
        with open(probe_file, "w") as f:
            f.write("ok")
        if os.path.exists(probe_file):
            os.remove(probe_file)
        checks["storage"] = {"status": "writable", "path": settings.UPLOAD_DIR}
    except Exception as e:
        checks["storage"] = {"status": "read_only_or_missing", "error": str(e)}
        is_ready = False

    # 3. ML Model files check
    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "models_ml")
    lite_model = os.path.exists(os.path.join(models_dir, "pose_landmarker_lite.task"))
    full_model = os.path.exists(os.path.join(models_dir, "pose_landmarker_full.task"))
    checks["ml_models"] = {
        "status": "available" if (lite_model or full_model) else "degraded",
        "pose_landmarker_lite": lite_model,
        "pose_landmarker_full": full_model
    }

    if not is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": checks}
        )

    return {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks
    }

@router.get("/health/db")
def health_check_db(db: Session = Depends(get_db)):
    """Database specific health probe."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database connection is healthy"}
    except Exception as e:
        return {"status": "error", "message": f"Database connection failed: {str(e)}"}

@router.get("/health/metrics")
def system_metrics(db: Session = Depends(get_db)):
    """
    Exposes operational runtime metrics for monitoring dashboards (Prometheus/Grafana/Datadog):
    Uptime, disk storage allocation, Python runtime environment, and high-level counters.
    """
    uptime_sec = round(time.time() - APP_START_TIME, 2)
    
    # Disk usage for upload directory
    storage_info = {}
    try:
        total, used, free = shutil.disk_usage(os.path.abspath(settings.UPLOAD_DIR))
        storage_info = {
            "total_gb": round(total / (1024 ** 3), 2),
            "used_gb": round(used / (1024 ** 3), 2),
            "free_gb": round(free / (1024 ** 3), 2),
            "percent_used": round((used / total) * 100, 1)
        }
    except Exception:
        storage_info = {"status": "unavailable"}

    # Database query counts
    db_metrics = {}
    try:
        from app.models.video import Video
        from app.models.user import User
        from app.models.notification import Notification
        
        user_count = db.query(User).count()
        video_count = db.query(Video).count()
        unread_notifs = db.query(Notification).filter(Notification.is_read == False).count()
        db_metrics = {
            "total_users": user_count,
            "total_videos": video_count,
            "unread_notifications": unread_notifs,
            "status": "online"
        }
    except Exception as e:
        db_metrics = {"status": "error", "error": str(e)}

    return {
        "service": settings.PROJECT_NAME,
        "uptime_seconds": uptime_sec,
        "runtime": {
            "python_version": sys.version.split(" ")[0],
            "os": platform.system(),
            "os_release": platform.release(),
            "cpu_architecture": platform.machine()
        },
        "storage": storage_info,
        "database_metrics": db_metrics,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
