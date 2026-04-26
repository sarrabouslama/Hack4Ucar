"""API routes for education research."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def education_health():
    """Temporary health endpoint until education routes are implemented."""

    return {"module": "education_research", "status": "ok"}
