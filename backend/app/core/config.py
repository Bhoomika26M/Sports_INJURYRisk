from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, overridable through environment variables or .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Sports Injury Risk Detection from Video"
    API_PREFIX: str = "/api/v1"

    # --- Security -----------------------------------------------------------
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GOOGLE_CLIENT_ID: str = ""
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    CORS_ORIGINS: str = "http://localhost:5173"
    RATE_LIMIT_PER_MINUTE: int = 240

    # --- Databases ----------------------------------------------------------
    DATABASE_URL: str = "sqlite:///./injury_risk.db"
    MONGO_URL: str = ""  # optional; falls back to JSON files in POSE_DIR
    MONGO_DB: str = "injury_risk"

    # --- Storage ------------------------------------------------------------
    UPLOAD_DIR: str = "./storage/uploads"
    POSE_DIR: str = "./storage/pose"
    REPORT_DIR: str = "./storage/reports"
    MODEL_PATH: str = "./models/injury_model.joblib"

    # --- Video validation ---------------------------------------------------
    MAX_UPLOAD_MB: int = 500
    MIN_VIDEO_FPS: float = 15.0
    MIN_VIDEO_WIDTH: int = 320
    MIN_VIDEO_HEIGHT: int = 240
    MIN_VIDEO_SECONDS: float = 1.0
    MAX_VIDEO_SECONDS: float = 600.0

    # --- Pose estimation ----------------------------------------------------
    POSE_FRAME_STRIDE: int = 1
    POSE_MODEL_COMPLEXITY: int = 1  # legacy MediaPipe only (0, 1 or 2)
    # Current MediaPipe needs a model file. It is downloaded automatically on first use.
    POSE_MODEL_PATH: str = "./models/pose_landmarker_full.task"
    POSE_MODEL_URL: str = (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
    )
    MIN_KEYPOINT_VISIBILITY: float = 0.5
    USE_YOLO_PERSON_DETECTOR: bool = False
    YOLO_WEIGHTS: str = "yolov8n.pt"

    # --- Risk categories (score is 0-100) -----------------------------------
    RISK_MODERATE_THRESHOLD: float = 25.0
    RISK_HIGH_THRESHOLD: float = 50.0
    RISK_CRITICAL_THRESHOLD: float = 75.0

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
