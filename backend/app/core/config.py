from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
from pydantic import field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "AthletiQ"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if not v.strip():
                return []
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(i).strip() for i in v if str(i).strip()]
        return []

    # Database
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "sports_injury_db"
    
    # Optional override for testing / cloud deployments
    DATABASE_URL_OVERRIDE: str | None = None

    @property
    def DATABASE_URL(self) -> str:
        import os
        from pathlib import Path
        url = os.environ.get("DATABASE_URL_OVERRIDE") or self.DATABASE_URL_OVERRIDE or os.environ.get("DATABASE_URL")
        if url and url.strip():
            # Adapt postgres:// and postgresql:// to postgresql+psycopg2:// for SQLAlchemy
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgresql://") and "+psycopg2" not in url:
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            
            # If SQLite relative path is provided, resolve to absolute path to prevent "unable to open database file"
            if url.startswith("sqlite:///") and not url.startswith("sqlite:////") and ":memory:" not in url:
                rel_path = url.replace("sqlite:///", "").replace("backend/", "")
                backend_dir = Path(__file__).resolve().parent.parent.parent
                abs_db_path = (backend_dir / rel_path.lstrip("./\\")).resolve()
                return f"sqlite:///{abs_db_path.as_posix()}"
            return url
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # JWT & OAuth
    SECRET_KEY: str = "athletiq-production-secret-key-change-in-env-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days session persistence
    GOOGLE_CLIENT_ID: str = "286120016431-n54sspion4lmn93dqjiqlj2k76d5cnnb.apps.googleusercontent.com"
    ADMIN_REGISTRATION_CODE: str = ""
    
    # Uploads
    UPLOAD_DIR: str = "../uploads" # Outside public web directory
    MAX_VIDEO_SIZE_MB: int = 500
    MAX_VIDEO_DURATION_SEC: int = 300 # 5 minutes

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
