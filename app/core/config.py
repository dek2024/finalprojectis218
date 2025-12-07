from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Application
    APP_NAME: str = "CareerLens"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-powered resume analysis and job matching platform"
    DEBUG: bool = False

    # Frontend + Backend URLs (required for email verification)
    BACKEND_BASE_URL: str = "http://127.0.0.1:8001"
    FRONTEND_BASE_URL: str = "http://127.0.0.1:8001"

    # Database
    DATABASE_URL: str = "sqlite:///./careerlens.db"
    DATABASE_URL_TEST: str = "sqlite:///./test.db"

    # JWT
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_SECRET_KEY: str = "dev-jwt-secret-key-change-in-production"

    # Email
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = ""

    # OpenAI
    OPENAI_API_KEY: str | None = None

    # JSearch API
    JSEARCH_API_KEY: str = ""
    JSEARCH_API_HOST: str = "jsearch.p.rapidapi.com"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost", "http://localhost:8000"]

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
