from datetime import datetime
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: str = Field(default="healthy", description="Current service health state")
    project_name: str = Field(..., description="Project name")
    version: str = Field(..., description="API Version")
    environment: str = Field(..., description="Active runtime environment")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Server response UTC timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "project_name": "Sports Injury Risk Detection",
                "version": "0.1.0",
                "environment": "development",
                "timestamp": "2026-09-18T15:00:00Z"
            }
        }
    }
