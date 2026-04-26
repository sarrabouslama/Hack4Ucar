"""Configuration management."""

from typing import Any, List

from pydantic import Field, field_validator
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


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

    # Database settings - PostgreSQL
    DATABASE_URL: str

    # API settings
    API_V1_PREFIX: str
    SKIP_DB_STARTUP: bool = False

    # Gemini settings
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

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

    @classmethod
    def from_env(cls):
        """Load settings from environment"""
        return cls()


settings = Settings()
