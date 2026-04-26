"""
Business logic for finance, partnerships, and HR.
"""

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, Optional

import openpyxl
from sqlalchemy import func

from app.core.database import SessionLocal
from app.modules.kpis.db_models import KPIMetric
from app.modules.finance_partnerships_hr.analytics.predictions import get_predictions
from app.modules.finance_partnerships_hr.db_models import Absenteeism, Budget, Employee
from app.modules.finance_partnerships_hr.models import BudgetReportInput, HrHeadcountInput, ResearchProjectInput
from app.modules.finance_partnerships_hr.rankings.scoring import (
    compute_composite_score as compute_composite_score_sync,
    get_anonymous_rankings,
    get_full_rankings,
)
from app.modules.finance_partnerships_hr.reports.generate import run_report_generation


class ReportService:
    def __init__(self, db_session=None):
        self.db = db_session

    async def generate_monthly_report(self) -> Dict[str, Any]:
        return run_report_generation(period="monthly", report_type="executive", institution_id="UCAR")


class DashboardService:
    def __init__(self, db_session=None):
        self.db = db_session

    def _get_session(self):
        return self.db if self.db is not None else SessionLocal()

    async def get_budget_kpis(self):
        db = self._get_session()
        created_session = db is not self.db
        try:
            rows = (
                db.query(
                    Budget.department,
                    func.sum(Budget.allocated_amount),
                    func.sum(Budget.spent_amount),
                )
                .group_by(Budget.department)
                .all()
            )
            output = []
            for department, allocated, spent in rows:
                allocated_value = float(allocated or 0.0)
                spent_value = float(spent or 0.0)
                pct = (spent_value / allocated_value * 100.0) if allocated_value else 0.0
                output.append(
                    {
                        "department": department,
                        "allocated": round(allocated_value, 2),
                        "spent": round(spent_value, 2),
                        "utilization_pct": round(pct, 2),
                    }
                )
            return output
        finally:
            if created_session:
                db.close()

    async def get_hr_kpis(self):
        db = self._get_session()
        created_session = db is not self.db
        try:
            total_employees = int(db.query(func.count(Employee.id)).scalar() or 0)
            by_department_rows = (
                db.query(Employee.department, func.count(Employee.id))
                .group_by(Employee.department)
                .all()
            )
            total_missed_hours = float(db.query(func.sum(Absenteeism.hours_missed)).scalar() or 0.0)
            absenteeism_rate = (total_missed_hours / max(total_employees * 160.0, 1.0)) * 100.0
            return {
                "total_employees": total_employees,
                "by_department": {dept: count for dept, count in by_department_rows},
                "absenteeism_rate_pct": round(absenteeism_rate, 2),
            }
        finally:
            if created_session:
                db.close()

    async def get_research_kpis(self):
        db = self._get_session()
        created_session = db is not self.db
        try:
            publications = float(
                db.query(func.sum(KPIMetric.value))
                .filter(func.lower(KPIMetric.indicator).like("%publication%"))
                .scalar()
                or 0.0
            )
            funding = float(
                db.query(func.sum(KPIMetric.value))
                .filter(
                    func.lower(KPIMetric.indicator).like("%fund%")
                )
                .scalar()
                or 0.0
            )
            active_projects = float(
                db.query(func.sum(KPIMetric.value))
                .filter(func.lower(KPIMetric.indicator).like("%project%"))
                .scalar()
                or 0.0
            )
            return {
                "publications": round(publications, 2),
                "funding": round(funding, 2),
                "active_projects": round(active_projects, 2),
            }
        finally:
            if created_session:
                db.close()

    async def get_budget_trend(self):
        return get_predictions(institution_id="UCAR", indicator="budget")


class GamificationService:
    async def compute_composite_score(self, institution_code: str) -> Dict[str, Any]:
        return compute_composite_score_sync(institution_code)

    async def award_badges(self, institution_code: str):
        score_result = compute_composite_score_sync(institution_code)
        return score_result.get("badges", [])

    async def get_leaderboard(self, viewer_role: str, current_institution_id: Optional[str] = None):
        if viewer_role.lower() == "ucar":
            return get_full_rankings()
        return get_anonymous_rankings(current_institution_id=current_institution_id)


class FormService:
    def __init__(self, db_session=None):
        self.db = db_session

    def _get_session(self):
        return self.db if self.db is not None else SessionLocal()

    async def submit_budget_report(self, data: BudgetReportInput):
        db = self._get_session()
        created_session = db is not self.db
        try:
            entry = Budget(
                department=data.department,
                fiscal_year=data.fiscal_year,
                allocated_amount=data.allocated_amount,
                spent_amount=data.spent_amount,
                category=data.category,
            )
            db.add(entry)
            db.commit()
            return {"status": "saved", "id": str(entry.id)}
        except Exception as exc:
            db.rollback()
            print(f"[ERROR] submit_budget_report failed: {exc}")
            return {"status": "error", "message": str(exc)}
        finally:
            if created_session:
                db.close()

    async def submit_hr_headcount(self, data: HrHeadcountInput):
        return {"status": "not_implemented", "message": "Dedicated headcount table is not defined in schema"}

    async def submit_research_project(self, data: ResearchProjectInput):
        return {"status": "not_implemented", "message": "Research projects table is not defined in schema"}

    async def import_excel_financial(self, file_bytes: bytes):
        db = self._get_session()
        created_session = db is not self.db
        try:
            wb = openpyxl.load_workbook(BytesIO(file_bytes))
            ws = wb.active
            inserted = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or len(row) < 5:
                    continue
                department, fiscal_year, allocated, spent, category = row[:5]
                if not department:
                    continue
                entry = Budget(
                    department=str(department),
                    fiscal_year=int(fiscal_year or datetime.utcnow().year),
                    allocated_amount=float(allocated or 0.0),
                    spent_amount=float(spent or 0.0),
                    category=str(category or "general"),
                )
                db.add(entry)
                inserted += 1
            db.commit()
            return {"status": "ok", "inserted_rows": inserted}
        except Exception as exc:
            db.rollback()
            print(f"[ERROR] import_excel_financial failed: {exc}")
            return {"status": "error", "message": str(exc)}
        finally:
            if created_session:
                db.close()
