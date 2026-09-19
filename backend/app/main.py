"""Sports Injury Risk Detection Platform — Backend API."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.athletes.router import router as athletes_router
from app.modules.videos.router import router as videos_router
from app.modules.risk_scoring.router import router as risk_scoring_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sports Injury Risk Detection API",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(athletes_router)
app.include_router(videos_router)
app.include_router(risk_scoring_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

import aiofiles
import os
import re
from fastapi import Request, Depends, HTTPException
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.core.deps import get_current_user
from app.modules.users.models import User
from app.modules.videos.models import Video, VideoProcessingStatus

os.makedirs("/uploads", exist_ok=True)

STORAGE_KEY_PATTERN = re.compile(r'^[a-f0-9-]{36}_[\w\-. ]{1,200}\.(mp4|mov)$', re.IGNORECASE)

@app.put("/api/v1/local-storage/{key:path}")
async def upload_local_file(
    key: str,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Mock local-disk stand-in for a real presigned upload. Dev only — see docs/DECISIONS.md."""
    if not STORAGE_KEY_PATTERN.match(key):
        raise HTTPException(status_code=400, detail={"error": {"code": "invalid_key", "message": "Invalid storage key"}})
    
    video = await db.scalar(
        select(Video).where(Video.storage_key == key, Video.processing_status == VideoProcessingStatus.pending_upload)
    )
    if not video:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "No matching pending upload"}})
    if video.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail={"error": {"code": "INSUFFICIENT_PERMISSIONS", "message": "Not the owner of this upload"}})

    filepath = os.path.join("/uploads", key)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    async with aiofiles.open(filepath, "wb") as f:
        async for chunk in request.stream():
            await f.write(chunk)
    return {"status": "ok"}

