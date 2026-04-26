"""
API routes for education research
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def education_status() -> dict:
    """Minimal status endpoint for the education module."""

    return {"module": "education_research", "status": "ready"}
