"""Configuration management."""

from typing import Any, List

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from .env"""

    # App settings
    APP_NAME: str
    DEBUG: bool
    VERSION: str

    # CORS settings
    CORS_ORIGINS: List[str]

    # Database settings - PostgreSQL
    DATABASE_URL: str

    # API settings
    API_V1_PREFIX: str
    SKIP_DB_STARTUP: bool = False

    # Gemini settings
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Celery settings
    @property
    def CELERY_BROKER_URL(self) -> str:
        """Use SQLAlchemy transport for Postgres broker."""
        return self.DATABASE_URL.replace("postgresql://", "sqla+postgresql://")

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        """Use Database backend for Postgres results."""
        return self.DATABASE_URL.replace("postgresql://", "db+postgresql://")

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug(cls, value: Any) -> bool:
        """Accept common environment-style debug strings."""

        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production"}:
                return False
        return bool(value)

    class Config:
        env_file = ".env"
        case_sensitive = True

    @classmethod
    def from_env(cls):
        """Load settings from environment"""
        return cls()


settings = Settings()
