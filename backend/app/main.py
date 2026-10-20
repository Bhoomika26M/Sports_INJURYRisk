import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.router import api_router, health_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import RateLimitMiddleware, RequestLoggingMiddleware
from app.core.security import hash_password
from app.db.session import SessionLocal, init_db
from app.models.user import Role, User

logger = logging.getLogger(__name__)


def bootstrap_admin() -> None:
    """Create the first administrator from ADMIN_EMAIL / ADMIN_PASSWORD, if set."""
    if not (settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD):
        return
    with SessionLocal() as db:
        email = settings.ADMIN_EMAIL.lower()
        if db.scalar(select(User).where(User.email == email)) is None:
            db.add(
                User(
                    email=email,
                    full_name="Administrator",
                    hashed_password=hash_password(settings.ADMIN_PASSWORD),
                    role=Role.administrator.value,
                )
            )
            db.commit()
            logger.info("Bootstrapped administrator %s", email)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    if settings.SECRET_KEY == "change-me-in-production":
        logger.warning("SECRET_KEY is the default value. Set a strong secret before deploying.")
    for directory in (settings.UPLOAD_DIR, settings.POSE_DIR, settings.REPORT_DIR):
        os.makedirs(directory, exist_ok=True)
    init_db()
    bootstrap_admin()
    yield


app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0", lifespan=lifespan)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(api_router, prefix=settings.API_PREFIX)
