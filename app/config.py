"""
Configuration management
"""

import json
from typing import List

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
    ANTHROPIC_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

    @classmethod
    def from_env(cls):
        """Load settings from environment"""
        return cls()


settings = Settings()
