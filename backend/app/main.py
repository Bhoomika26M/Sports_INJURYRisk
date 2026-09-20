from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine

from app.models.user import User
from app.models.athlete import Athlete

from app.routes.auth import router as auth_router
from app.routes.athletes import router as athlete_router


# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Sports Injury Risk Detection API",
    description="AI-powered sports injury risk detection platform",
    version="1.0.0"
)


# Allow React frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Authentication routes
app.include_router(auth_router)
app.include_router(athlete_router)


@app.get("/")
def home():
    return {
        "message": "Sports Injury Risk Detection API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }