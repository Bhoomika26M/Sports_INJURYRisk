from datetime import datetime
from fastapi import APIRouter, status
from app.core.config import settings
from app.schemas.health import HealthCheckResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
    description="Returns the operational status, service metadata, and server time.",
)
async def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(
        status="healthy",
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.utcnow(),
    )
