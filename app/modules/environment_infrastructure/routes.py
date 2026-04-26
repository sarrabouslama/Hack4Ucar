"""API routes for environment and infrastructure."""

from fastapi import APIRouter

from app.modules.environment_infrastructure.models import (
    EmailFootprintRequest,
    EmailFootprintResponse,
    EnvironmentalScorecardResponse,
    InstitutionScorecardRequest,
)
from app.modules.environment_infrastructure.services import environment_scoring_service

router = APIRouter()


@router.get("/health")
async def environment_health():
    """Basic health endpoint for the environment module."""

    return {"module": "environment_infrastructure", "status": "ok"}


@router.post("/scorecard", response_model=EnvironmentalScorecardResponse)
async def generate_environmental_scorecard(
    payload: InstitutionScorecardRequest,
) -> EnvironmentalScorecardResponse:
    """Compute gross CO2, optimized CO2, verdict, and ESG KPI for an institution."""

    return environment_scoring_service.build_scorecard(payload)


@router.post("/email-footprint", response_model=EmailFootprintResponse)
async def generate_email_footprint(
    payload: EmailFootprintRequest,
) -> EmailFootprintResponse:
    """Estimate digital energy and CO2 impact from email metadata."""

    return environment_scoring_service.estimate_email_footprint(payload)
