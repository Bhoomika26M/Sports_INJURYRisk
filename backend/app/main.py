import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine

# Import all models to ensure schema creation
from app.models.user import User
from app.models.athlete import Athlete
from app.models.analysis import AnalysisRecord
from app.models.prediction import InjuryAssessmentRecord
from app.models.notification import Notification
from app.models.report import ReportRecord

# Import all routers
from app.routes.auth import router as auth_router
from app.routes.athletes import router as athlete_router
from app.routes.analysis import router as analysis_router
from app.routes.prediction import router as prediction_router
from app.routes.users import router as users_router
from app.routes.notifications import router as notifications_router
from app.routes.dashboard import router as dashboard_router
from app.routes.reports import router as reports_router

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sports Injury Risk Detection API",
    description="AI-powered sports injury risk detection, biomechanical analytics, and prevention platform",
    version="2.0.0"
)

# Allow React frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount videos directory for streaming sample videos to web UI
videos_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "videos"))
if os.path.exists(videos_dir):
    app.mount("/videos", StaticFiles(directory=videos_dir), name="videos")

# Include all routers
app.include_router(auth_router)
app.include_router(athlete_router)
app.include_router(analysis_router)
app.include_router(prediction_router)
app.include_router(users_router)
app.include_router(notifications_router)
app.include_router(dashboard_router)
app.include_router(reports_router)


@app.get("/")
def home():
    return {
        "message": "Sports Injury Risk Detection API is running",
        "status": "operational",
        "version": "2.0.0"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "sports-injury-ai-backend",
        "version": "2.0.0"
    }
