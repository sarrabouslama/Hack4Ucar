"""
Configuration management
"""

from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env"""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # App settings
    APP_NAME: str = "Hack4Ucar AI Modules"
    DEBUG: bool = False
    VERSION: str = "0.1.0"

    # CORS settings
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"]
    )

    # Database settings - Supabase/PostgreSQL
    DATABASE_URL: str = "sqlite:///./hack4ucar.db"
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # API settings
    API_V1_PREFIX: str = "/api/v1"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug_value(cls, value):
        """Accept common string environment values for DEBUG."""

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development", "dev"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value

    @classmethod
    def from_env(cls):
        """Load settings from environment"""
        return cls()


settings = Settings()
