"""Application configuration — reads from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://injury_user:changeme_in_production@postgres:5432/injury_detection"
    database_url_sync: str = "postgresql+psycopg2://injury_user:changeme_in_production@postgres:5432/injury_detection"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # JWT
    jwt_secret_key: str = "change-this-to-a-long-random-string-in-production"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    # Backend
    backend_cors_origins: str = "http://localhost:3000"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Frontend
    next_public_api_url: str = "http://localhost:8000/api/v1"

    @property
    def backend_cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
