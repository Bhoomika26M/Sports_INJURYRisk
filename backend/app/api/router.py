from fastapi import APIRouter

from app.api import analyses, athletes, auth, dashboards, health, notifications, reports, users, videos

api_router = APIRouter()
for module in (auth, users, athletes, videos, analyses, dashboards, notifications, reports):
    api_router.include_router(module.router)

# /health is mounted separately in main.py (outside the versioned prefix)
health_router = health.router
