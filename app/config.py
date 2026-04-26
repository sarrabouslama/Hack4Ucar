"""Configuration management."""

from typing import Any, List

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from .env."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_NAME: str = "Hack4Ucar AI Modules"
    DEBUG: bool = False
    VERSION: str = "0.1.0"

    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"]
    )

    # Database settings - PostgreSQL
    DATABASE_URL: str

    # API settings
    API_V1_PREFIX: str
    SKIP_DB_STARTUP: bool = False

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
    def normalize_debug_value(cls, value: Any) -> bool:
        """Accept common string environment values for DEBUG."""

        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production"}:
                return False
        return bool(value)

    @classmethod
    def from_env(cls):
        """Load settings from environment."""

        return cls()


settings = Settings()
