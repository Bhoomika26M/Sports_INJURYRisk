from fastapi import APIRouter
from app.routers import health
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.admin import router as admin_router
from app.routers.athletes import router as athletes_router
from app.routers.google_auth import router as google_auth_router

api_router = APIRouter()

# Health
api_router.include_router(health.router, prefix="", tags=["Health"])

# Auth & User management
api_router.include_router(auth_router)
api_router.include_router(google_auth_router)
api_router.include_router(users_router)
api_router.include_router(admin_router)

# Athlete management
api_router.include_router(athletes_router)
