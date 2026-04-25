"""API routes for chatbot and automation."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def chatbot_health():
    """Temporary health endpoint until chatbot routes are implemented."""

    return {"module": "chatbot_automation", "status": "ok"}
