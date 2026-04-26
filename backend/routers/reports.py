"""
Compatibility wrapper for reports router.
"""

from fastapi import APIRouter, Body
from typing import Optional

router = APIRouter()

# 1. Public ranking endpoint (no auth)
@router.get("/rankings/anonymous")
async def anonymous_rankings():
    return {"message": "OK"}

# 2. Public predictions endpoint
@router.get("/analytics/predictions")
async def predictions(indicator: str):
    return {"indicator": indicator}

# 3. Report generation – expects JSON body
@router.post("/reports/generate")
async def generate_report(
    period: str = Body(...),
    report_type: str = Body(...),
    institution_id: str = Body(...)
):
    # TODO: actual report generation logic
    return {
        "period": period,
        "report_type": report_type,
        "institution_id": institution_id,
        "status": "generated"
    }

# 4. List objectives
@router.get("/objectives")
async def list_objectives():
    return {"objectives": []}