from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.core.config import settings
from app.api.api import api_router

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
        print(f"Database schema auto-migration error: {e}")

ensure_database_schema()

app = FastAPI(title=settings.PROJECT_NAME)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

default_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]
configured_origins = [str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS] if settings.BACKEND_CORS_ORIGINS else []
cors_origins = list(dict.fromkeys(default_origins + [o for o in configured_origins if o != "*"]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router, prefix="/api/v1")

