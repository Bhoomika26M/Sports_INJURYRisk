from fastapi import APIRouter
from app.api.endpoints import (
    health,
    users,
    auth,
    athletes,
    videos,
    analysis,
    assessment,
    risk,
    anomaly,
    recommendations,
    dashboard,
    datasets,
    notifications,
    reports
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(athletes.router, prefix="/athletes", tags=["athletes"])
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(assessment.router, prefix="/assessment", tags=["assessment"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
api_router.include_router(anomaly.router, prefix="/anomaly", tags=["anomaly"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
