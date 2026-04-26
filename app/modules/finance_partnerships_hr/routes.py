"""API routes for finance, partnerships, and HR."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def finance_hr_health():
    """Temporary health endpoint until finance and HR routes are implemented."""

    return {"module": "finance_partnerships_hr", "status": "ok"}
