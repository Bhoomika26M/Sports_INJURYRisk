"""Sports Injury Risk Detection Platform — Backend API."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.health import router as health_router
from app.modules.auth.router import router as auth_router
from app.modules.athletes.router import router as athletes_router
from app.modules.video.router import VIDEO_EXTENSIONS, router as videos_router
from app.modules.risk_scoring.router import router as risk_scoring_router
from app.modules.notifications.router import router as notifications_router
from app.modules.analytics.router import router as analytics_router
from app.modules.pose import jobs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    await jobs.start()   # video analysis runs in this process; see app/modules/pose/jobs.py
    yield
    await jobs.stop()


app = FastAPI(
    title="Sports Injury Risk Detection API",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(athletes_router)
app.include_router(videos_router)
app.include_router(risk_scoring_router)
app.include_router(notifications_router)
app.include_router(analytics_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


import aiofiles
import os
import re
from fastapi import Request, Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.core.deps import get_current_user
from app.core.errors import api_error
from app.modules.users.models import User
from app.modules.video.models import Video, VideoProcessingStatus

os.makedirs(settings.upload_dir, exist_ok=True)

STORAGE_KEY_PATTERN = re.compile(rf'^[a-f0-9-]{{36}}_[\w\-. ]{{1,200}}\.({VIDEO_EXTENSIONS})$', re.IGNORECASE)

@app.put("/api/v1/local-storage/{key:path}")
async def upload_local_file(
    key: str,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Mock local-disk stand-in for a real presigned upload. Dev only — see docs/DECISIONS.md."""
    if not STORAGE_KEY_PATTERN.match(key):
        raise api_error(400, "invalid_key", "Invalid storage key")

    video = await db.scalar(
        select(Video).where(Video.storage_key == key, Video.processing_status == VideoProcessingStatus.pending_upload)
    )
    if not video:
        raise api_error(404, "NOT_FOUND", "No matching pending upload")
    if video.uploaded_by != current_user.id:
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Not the owner of this upload")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > max_bytes:
        raise api_error(413, "file_too_large", f"File exceeds {settings.max_upload_mb} MB")

    filepath = os.path.join(settings.upload_dir, key)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    written = 0
    try:
        async with aiofiles.open(filepath, "wb") as f:
            async for chunk in request.stream():
                written += len(chunk)
                if written > max_bytes:   # Content-Length can be absent or wrong: count what actually arrives
                    raise api_error(413, "file_too_large", f"File exceeds {settings.max_upload_mb} MB")
                await f.write(chunk)
    except BaseException:
        # too big, client disconnected, disk error: never leave a partial file behind
        try:
            os.remove(filepath)
        except OSError:
            pass
        raise
    return {"status": "ok"}
