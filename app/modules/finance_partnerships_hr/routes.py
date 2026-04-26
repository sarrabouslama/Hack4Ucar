"""
API routes for finance, partnerships, and HR
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def finance_status() -> dict:
    """Minimal status endpoint for the finance and HR module."""

    return {"module": "finance_partnerships_hr", "status": "ready"}
