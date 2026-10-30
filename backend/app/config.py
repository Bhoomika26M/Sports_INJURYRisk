"""Application configuration — reads from environment variables."""

import logging
from pathlib import Path
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings


_DEFAULT_JWT_SECRET = "change-this-to-a-long-random-string-in-production"


class Settings(BaseSettings):
    # "production" makes the app refuse to start with the placeholder JWT secret below.
    environment: str = "development"

    # Database
    database_url: str = "postgresql+asyncpg://injury_user:changeme_in_production@postgres:5432/injury_detection"
    database_url_sync: str = ""  # derived from database_url when unset (see _derive_sync_url)

    # JWT
    jwt_secret_key: str = _DEFAULT_JWT_SECRET
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    # Google OAuth2
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Browser-facing URL of the Next.js app. The OAuth callback redirects here once the refresh
    # cookie is set; no token is ever placed in a URL.
    frontend_url: str = "http://localhost:3000"

    # Secure flag on auth cookies. Default True (AGENTS.md: httpOnly, secure, SameSite=Lax).
    # Set COOKIE_SECURE=false ONLY for local plain-http development in a browser that refuses
    # Secure cookies on http://localhost (e.g. Safari).
    cookie_secure: bool = True

    # Backend
    backend_cors_origins: str = "http://localhost:3000"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Frontend
    next_public_api_url: str = "http://localhost:8000/api/v1"

    # Storage. Local-disk stand-in for S3.
    # Docker sets UPLOAD_DIR=/uploads (a volume); a host run defaults to backend/uploads.
    upload_dir: str = str(Path(__file__).resolve().parents[1] / "uploads")
    # Upload limits. The server is authoritative (the upload page mirrors them for instant feedback).
    max_upload_mb: int = 200
    min_video_seconds: float = 2.0
    max_video_seconds: float = 60.0
    min_video_height: int = 480
    use_s3_storage: bool = False
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None

    # AI engine: completed videos of a movement type required before a video can be scored.
    # The unit is VIDEOS (not metric rows — one video yields hundreds of rows). Lower only for
    # demos; the response always reports how many baseline videos were used.
    min_baseline_videos: int = 10
    # ...and they must come from at least this many DISTINCT athletes: ten clips of one athlete is that
    # athlete's personal envelope, not a population baseline (a different athlete's normal technique
    # would read as "anomalous"). Counted over the videos actually in the baseline.
    min_baseline_athletes: int = 3

    # Video analysis speed/accuracy knobs. They live here (not os.environ) so a host run honours them from .env.
    # See .env.example for what each trades off.
    yolo_imgsz: int = 384
    yolo_track_fps: float = 15
    yolo_tracker: str = "botsort.yaml"
    pose_landmarker_variant: str = "full"

    # Optional, OFF by default: after pose analysis, also send the clip to the standalone Gemini observation script
    # (scripts/gemini_video.py; needs GEMINI_API_KEY). The result is shown to the user and is NEVER used in scoring.
    # It uploads footage of the athlete to Google, so enable it only with the athlete's consent.
    auto_gemini_observation: bool = False

    # Email (SendGrid)
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: str = "noreply@injury-detection.local"

    @property
    def backend_cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _refuse_placeholder_secret_in_production(self):
        if self.jwt_secret_key == _DEFAULT_JWT_SECRET:
            if self.environment.lower() == "production":
                raise ValueError("JWT_SECRET_KEY is still the placeholder value: set a long random secret before running with ENVIRONMENT=production")
            logging.getLogger(__name__).warning("JWT_SECRET_KEY is the placeholder value: fine for local development, never for a deployment")
        return self

    @model_validator(mode="after")
    def _derive_sync_url(self):
        if not self.database_url_sync:
            self.database_url_sync = self.database_url.replace("+asyncpg", "+psycopg2")
        return self

    # "../.env" = the repo-root .env the README tells you to create, found when running from backend/.
    model_config = {"env_file": ("../.env", ".env"), "extra": "ignore"}


settings = Settings()