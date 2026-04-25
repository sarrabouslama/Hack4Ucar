"""Configuration management."""

from typing import Any, List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from .env"""

    # App settings
    APP_NAME: str
    DEBUG: bool
    VERSION: str

    # CORS settings
    CORS_ORIGINS: List[str]

    # Database settings - Supabase/PostgreSQL
    DATABASE_URL: str
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # API settings
    API_V1_PREFIX: str

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
