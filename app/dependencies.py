"""
Shared dependencies for FastAPI
"""

from typing import Generator

from app.config import settings
from app.core.database import get_db


async def get_settings():
    """Get application settings"""
    return settings
