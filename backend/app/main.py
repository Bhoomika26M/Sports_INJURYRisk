import os
import time
import uuid
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.logging_config import setup_logging, request_id_ctx
from app.api.api import api_router

# Initialize structured logging
setup_logging()
logger = logging.getLogger("athletiq.main")

def ensure_database_schema():
    """Guarantees all tables and columns exist across SQLite and PostgreSQL."""
    try:
        from app.db.session import engine, Base
        from sqlalchemy import inspect, text
        import app.models.user
        import app.models.athlete
        import app.models.assignment
        import app.models.video
        import app.models.notification

        Base.metadata.create_all(bind=engine)
        inspector = inspect(engine)
        if "videos" in inspector.get_table_names():
            existing = {c["name"] for c in inspector.get_columns("videos")}
            missing = {
                "movement_type": "VARCHAR DEFAULT 'general'",
                "processing_progress": "INTEGER DEFAULT 0",
                "quality_score": "FLOAT",
                "quality_issues": "VARCHAR"
            }
            with engine.connect() as conn:
                for col_name, col_sql in missing.items():
                    if col_name not in existing:
                        conn.execute(text(f"ALTER TABLE videos ADD COLUMN {col_name} {col_sql}"))
                conn.commit()
    except Exception as e:
        logger.error(f"Database schema auto-migration error: {e}")

ensure_database_schema()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AthletiQ Sports Movement Screening & Kinematic Injury Risk Assessment Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 1. Performance: GZip Compression for responses > 1KB (reduces pose landmark JSON transfer payload by ~80%)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 2. Monitoring & Logging: Request ID & Timing Middleware
class RequestMonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_ctx.set(req_id)
        
        start_time = time.time()
        try:
            response: Response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}s"
            
            # Security Headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            
            return response
        finally:
            request_id_ctx.reset(token)

app.add_middleware(RequestMonitoringMiddleware)

# 3. Static Files Mounting
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# 4. CORS Setup
default_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
]
configured_origins = [str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS] if settings.BACKEND_CORS_ORIGINS else []
cors_origins = list(dict.fromkeys(default_origins + [o for o in configured_origins if o != "*"]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time", "Content-Disposition"]
)

# 5. Base Health & Root Endpoints
@app.get("/", tags=["health"])
def root_index():
    return {
        "service": settings.PROJECT_NAME,
        "status": "online",
        "documentation": "/docs",
        "health_check": "/api/v1/health"
    }

# 6. Include API Routers
app.include_router(api_router, prefix="/api/v1")
