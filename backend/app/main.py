from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings, UPLOAD_DIR, SAMPLE_DIR
from app.database import engine, Base, SessionLocal
from app.services.seed_data import seed_database
from app.routers import (
    auth,
    athletes,
    videos,
    biomechanics,
    injury_risk,
    datasets,
    dashboards
)

# Initialize database schema immediately
Base.metadata.create_all(bind=engine)

# Seed database immediately so tables are ready for TestClient and app
with SessionLocal() as init_db:
    try:
        seed_database(init_db)
    except Exception as e:
        print(f"Seed error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="AI-Powered Sports Injury Risk Detection Platform (FastAPI + MediaPipe + React)",
    lifespan=lifespan
)

# Enable CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folders for video files
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/samples", StaticFiles(directory=str(SAMPLE_DIR)), name="samples")

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(athletes.router, prefix=settings.API_V1_STR)
app.include_router(videos.router, prefix=settings.API_V1_STR)
app.include_router(biomechanics.router, prefix=settings.API_V1_STR)
app.include_router(injury_risk.router, prefix=settings.API_V1_STR)
app.include_router(datasets.router, prefix=settings.API_V1_STR)
app.include_router(dashboards.router, prefix=settings.API_V1_STR)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "mediapipe_ready": True
    }
