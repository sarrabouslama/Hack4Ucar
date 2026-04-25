"""
Shared dependencies for FastAPI
"""

from typing import Generator

from app.config import settings


async def get_settings() -> settings:
    """Get application settings"""
    return settings
