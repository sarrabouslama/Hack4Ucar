"""API routes for environment and infrastructure."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def environment_health():
    """Temporary health endpoint until environment routes are implemented."""

    return {"module": "environment_infrastructure", "status": "ok"}
