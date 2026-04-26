"""
API routes for chatbot and automation
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def chatbot_status() -> dict:
    """Minimal status endpoint for the chatbot module."""

    return {"module": "chatbot_automation", "status": "ready"}
