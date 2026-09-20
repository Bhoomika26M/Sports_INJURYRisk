from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "test-secret-key-for-development"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    model_config = ConfigDict(env_file=".env")


settings = Settings()
