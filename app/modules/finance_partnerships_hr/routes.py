"""
API routes for finance, partnerships, and HR.
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import validate_token
from app.dependencies import get_db
from app.modules.finance_partnerships_hr.analytics.predictions import get_predictions
from app.modules.finance_partnerships_hr.db_models import FinancialReport, KpiTarget
from app.modules.finance_partnerships_hr.rankings.scoring import get_anonymous_rankings, get_full_rankings
from app.modules.finance_partnerships_hr.reports.generate import generate_report as generate_report_task
from app.modules.finance_partnerships_hr.services import DashboardService, FormService

router = APIRouter()


class ReportGenerationRequest(BaseModel):
    period: str
    report_type: str
    institution_id: str = "UCAR"


def require_ucar(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_role: Optional[str] = Header(default=None, alias="X-Role"),
) -> bool:
    if authorization:
        token = authorization.replace("Bearer", "").strip()
        if not validate_token(token):
            raise HTTPException(status_code=401, detail="Invalid authentication token")
    if (x_role or "").strip().lower() != "ucar":
        raise HTTPException(status_code=403, detail="UCAR access required")
    return True


@router.post("/reports/generate")
async def trigger_report_generation(
    payload: ReportGenerationRequest = Body(...),
    _: bool = Depends(require_ucar),
):
    """
    Triggers Celery report generation for monthly/semestrial/annual periods.
    """
    try:
        async_result = generate_report_task.delay(
            payload.period,
            payload.report_type,
            payload.institution_id,
        )
        return {"task_id": async_result.id, "status": "queued"}
    except Exception as exc:
        print(f"[ERROR] Celery task dispatch failed: {exc}")
        raise HTTPException(status_code=503, detail="Unable to queue report generation task")


@router.get("/reports")
async def list_reports(db: Session = Depends(get_db)):
    rows = db.query(FinancialReport).order_by(FinancialReport.report_date.desc()).all()
    return [
        {
            "id": str(row.id),
            "institution_id": row.institution_id,
            "report_type": row.report_type,
            "fiscal_period": row.fiscal_period,
            "report_date": row.report_date.isoformat() if row.report_date else None,
            "pdf_path": row.pdf_path,
            "excel_path": row.excel_path,
        }
        for row in rows
    ]


@router.get("/reports/{report_id}/download")
async def download_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(FinancialReport).filter(FinancialReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not report.pdf_path:
        raise HTTPException(status_code=404, detail="PDF path is not available for this report")

    path = Path(report.pdf_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    return FileResponse(
        str(path),
        media_type="application/pdf",
        filename=path.name,
    )


@router.get("/objectives")
async def list_objectives(db: Session = Depends(get_db)):
    rows = db.query(KpiTarget).order_by(KpiTarget.created_at.desc()).all()
    return [
        {
            "id": str(row.id),
            "report_id": row.report_id,
            "domain": row.domain,
            "title": row.title,
            "objective": row.objective,
            "metric": row.metric,
            "target_value": row.target_value,
            "deadline": row.deadline.isoformat() if row.deadline else None,
            "responsible_role": row.responsible_role,
            "priority": row.priority,
            "status": row.status,
            "ai_generated": row.ai_generated,
        }
        for row in rows
    ]


@router.get("/rankings/full")
async def rankings_full(_: bool = Depends(require_ucar)):
    return get_full_rankings()


@router.get("/rankings/anonymous")
async def rankings_anonymous(current_institution_id: Optional[str] = None):
    return get_anonymous_rankings(current_institution_id=current_institution_id)


@router.get("/gamification/leaderboard")
async def leaderboard(role: str = "institution", current_institution_id: Optional[str] = None):
    if role.strip().lower() == "ucar":
        return get_full_rankings()
    return get_anonymous_rankings(current_institution_id=current_institution_id)


@router.get("/analytics/predictions")
async def analytics_predictions(institution_id: Optional[str] = None, indicator: str = "budget"):
    return get_predictions(institution_id=institution_id, indicator=indicator)


@router.get("/dashboard/budget")
async def budget_dashboard(db: Session = Depends(get_db)):
    service = DashboardService()
    return await service.get_budget_kpis()


@router.post("/forms/import-excel")
async def import_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    service = FormService()
    contents = await file.read()
    return await service.import_excel_financial(contents)
