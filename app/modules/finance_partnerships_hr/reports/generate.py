"""
Automated report generation for finance, HR, and research KPIs.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import anthropic
from celery import Celery
from celery.schedules import crontab
from openpyxl import Workbook
from sqlalchemy import func

from app.config import settings
from app.core.database import SessionLocal
from app.modules.education_research.db_models import ResearchIndicator
from app.modules.finance_partnerships_hr.db_models import (
    Absenteeism,
    Budget,
    Contract,
    Employee,
    EmploymentOutcome,
    FinancialReport,
    Partnership,
)
from app.modules.finance_partnerships_hr.reports.objectives import generate_smart_objectives

REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "generated_reports")).resolve()
DEFAULT_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
DEFAULT_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", DEFAULT_BROKER_URL)

celery_app = Celery(
    "finance_reports",
    broker=DEFAULT_BROKER_URL,
    backend=DEFAULT_RESULT_BACKEND,
)

celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "reports-monthly": {
        "task": "finance_reports.generate_report",
        "schedule": crontab(minute=0, hour=4, day_of_month=1),
        "args": ("monthly", "executive"),
    },
    "reports-semestrial": {
        "task": "finance_reports.generate_report",
        "schedule": crontab(minute=15, hour=4, day_of_month=1, month_of_year="1,7"),
        "args": ("semestrial", "executive"),
    },
    "reports-annual": {
        "task": "finance_reports.generate_report",
        "schedule": crontab(minute=30, hour=4, day_of_month=1, month_of_year=1),
        "args": ("annual", "executive"),
    },
}


def _period_bounds(period: str) -> Tuple[datetime, datetime]:
    now = datetime.utcnow()
    normalized = period.strip().lower()
    if normalized == "monthly":
        start = datetime(now.year, now.month, 1)
        return start, now
    if normalized == "semestrial":
        start = datetime(now.year, 1, 1) if now.month <= 6 else datetime(now.year, 7, 1)
        return start, now
    if normalized == "annual":
        start = datetime(now.year, 1, 1)
        return start, now
    raise ValueError("period must be one of: monthly, semestrial, annual")


def _anthropic_client() -> anthropic.Anthropic:
    api_key = settings.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured")
    return anthropic.Anthropic(api_key=api_key)


def _extract_claude_text(response: Any) -> str:
    parts: List[str] = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def aggregate_kpis(db_session, period: str) -> Dict[str, Dict[str, Any]]:
    start_date, end_date = _period_bounds(period)
    current_year = end_date.year

    total_allocated = _safe_float(
        db_session.query(func.coalesce(func.sum(Budget.allocated_amount), 0.0))
        .filter(Budget.fiscal_year == current_year)
        .scalar()
    )
    total_spent = _safe_float(
        db_session.query(func.coalesce(func.sum(Budget.spent_amount), 0.0))
        .filter(Budget.fiscal_year == current_year)
        .scalar()
    )
    budget_utilization = (total_spent / total_allocated * 100.0) if total_allocated else 0.0

    total_employees = int(db_session.query(func.count(Employee.id)).scalar() or 0)
    active_contracts = int(
        db_session.query(func.count(Contract.id))
        .filter(func.lower(Contract.status) == "active")
        .scalar()
        or 0
    )
    missed_hours = _safe_float(
        db_session.query(func.coalesce(func.sum(Absenteeism.hours_missed), 0.0))
        .filter(Absenteeism.absence_date >= start_date.date())
        .filter(Absenteeism.absence_date <= end_date.date())
        .scalar()
    )
    available_hours = max(total_employees * 160.0, 1.0)
    absenteeism_rate = missed_hours / available_hours * 100.0

    publications = _safe_float(
        db_session.query(func.coalesce(func.sum(ResearchIndicator.value), 0.0))
        .filter(func.lower(ResearchIndicator.metric_name).like("%publication%"))
        .filter(ResearchIndicator.reporting_date >= start_date)
        .filter(ResearchIndicator.reporting_date <= end_date)
        .scalar()
    )
    research_funding = _safe_float(
        db_session.query(func.coalesce(func.sum(ResearchIndicator.value), 0.0))
        .filter(
            func.lower(ResearchIndicator.metric_name).like("%fund%")
            | func.lower(ResearchIndicator.category).like("%fund%")
        )
        .filter(ResearchIndicator.reporting_date >= start_date)
        .filter(ResearchIndicator.reporting_date <= end_date)
        .scalar()
    )
    active_projects = _safe_float(
        db_session.query(func.coalesce(func.sum(ResearchIndicator.value), 0.0))
        .filter(func.lower(ResearchIndicator.metric_name).like("%project%"))
        .filter(ResearchIndicator.reporting_date >= start_date)
        .filter(ResearchIndicator.reporting_date <= end_date)
        .scalar()
    )

    active_partnerships = int(
        db_session.query(func.count(Partnership.id))
        .filter(func.lower(Partnership.status) == "active")
        .scalar()
        or 0
    )
    new_partnerships = int(
        db_session.query(func.count(Partnership.id))
        .filter(Partnership.start_date >= start_date)
        .filter(Partnership.start_date <= end_date)
        .scalar()
        or 0
    )
    ending_partnerships = int(
        db_session.query(func.count(Partnership.id))
        .filter(Partnership.end_date.isnot(None))
        .filter(Partnership.end_date >= start_date)
        .filter(Partnership.end_date <= end_date)
        .scalar()
        or 0
    )

    latest_outcome = (
        db_session.query(EmploymentOutcome)
        .order_by(EmploymentOutcome.graduate_year.desc())
        .first()
    )
    employment_rate = _safe_float(getattr(latest_outcome, "employment_rate", 0.0))
    average_salary = _safe_float(getattr(latest_outcome, "average_salary", 0.0))
    total_graduates = int(getattr(latest_outcome, "total_graduates", 0) or 0)

    return {
        "metadata": {
            "period": period,
            "generated_at": datetime.utcnow().isoformat(),
            "window_start": start_date.isoformat(),
            "window_end": end_date.isoformat(),
        },
        "finance": {
            "budget_total_alloue": round(total_allocated, 2),
            "budget_total_depense": round(total_spent, 2),
            "execution_budget_pct": round(budget_utilization, 2),
            "resultat_net": round(total_allocated - total_spent, 2),
        },
        "hr": {
            "effectif_total": total_employees,
            "contrats_actifs": active_contracts,
            "heures_absence": round(missed_hours, 2),
            "taux_absenteisme_pct": round(absenteeism_rate, 2),
        },
        "research": {
            "publications": round(publications, 2),
            "financement_recherche": round(research_funding, 2),
            "projets_actifs": round(active_projects, 2),
        },
        "partnerships": {
            "partenariats_actifs": active_partnerships,
            "nouveaux_partenariats": new_partnerships,
            "partenariats_finissants": ending_partnerships,
        },
        "employment": {
            "annee_reference": getattr(latest_outcome, "graduate_year", None),
            "total_diplomes": total_graduates,
            "taux_insertion_pct": round(employment_rate, 2),
            "salaire_moyen": round(average_salary, 2),
        },
    }


def generate_executive_summary(kpis: Dict[str, Any], period: str, report_type: str) -> str:
    prompt = (
        "Tu es un analyste de gouvernance universitaire.\n"
        "Redige un resume executif en francais, structure en 4 a 6 paragraphes courts, "
        "avec une lecture manageriale claire.\n"
        "Mentionne les tendances positives, les risques majeurs, et des recommandations concises.\n"
        f"Periode: {period}\n"
        f"Type de rapport: {report_type}\n"
        "Donnees KPI (JSON):\n"
        f"{json.dumps(kpis, ensure_ascii=False, indent=2)}\n"
    )
    try:
        response = _anthropic_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = _extract_claude_text(response)
        return text or "Resume indisponible (reponse vide de l'IA)."
    except Exception as exc:
        print(f"[ERROR] Claude summary generation failed: {exc}")
        return "Resume indisponible suite a une erreur IA."


def _summary_html_rows(domain_data: Dict[str, Any]) -> str:
    rows: List[str] = []
    for key, value in domain_data.items():
        rows.append(
            f"<tr><td style='padding:6px;border:1px solid #ddd'>{key}</td>"
            f"<td style='padding:6px;border:1px solid #ddd'>{value}</td></tr>"
        )
    return "".join(rows)


def render_pdf_report(
    summary_text: str,
    kpis: Dict[str, Dict[str, Any]],
    output_path: Path,
    period: str,
    report_type: str,
) -> None:
    try:
        from weasyprint import HTML
    except Exception as exc:
        print(f"[ERROR] WeasyPrint import failed: {exc}")
        raise

    sections = []
    for domain in ("finance", "hr", "research", "partnerships", "employment"):
        rows = _summary_html_rows(kpis.get(domain, {}))
        sections.append(
            "<section style='margin-bottom:20px'>"
            f"<h2 style='margin:0 0 8px 0'>{domain.upper()}</h2>"
            "<table style='border-collapse:collapse;width:100%'>"
            f"{rows}</table></section>"
        )

    html_doc = (
        "<html><body style='font-family:Arial,sans-serif;padding:24px;color:#111'>"
        f"<h1>Rapport {report_type} - {period}</h1>"
        f"<p><strong>Date de generation:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>"
        "<h2>Resume executif</h2>"
        f"<div style='white-space:pre-wrap;line-height:1.5'>{summary_text}</div>"
        f"{''.join(sections)}"
        "</body></html>"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_doc).write_pdf(str(output_path))


def export_excel_report(kpis: Dict[str, Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    workbook.remove(workbook.active)

    for domain in ("finance", "hr", "research", "partnerships", "employment"):
        sheet = workbook.create_sheet(title=domain[:31])
        sheet.append(["kpi", "value"])
        for key, value in (kpis.get(domain) or {}).items():
            sheet.append([key, value])

    workbook.save(str(output_path))


def run_report_generation(period: str, report_type: str, institution_id: str = "UCAR") -> Dict[str, Any]:
    db_session = SessionLocal()
    try:
        kpis = aggregate_kpis(db_session, period)
        summary = generate_executive_summary(kpis, period, report_type)

        finance = kpis.get("finance", {})
        report = FinancialReport(
            report_type=report_type,
            fiscal_period=period,
            total_revenue=_safe_float(finance.get("budget_total_alloue")),
            total_expenses=_safe_float(finance.get("budget_total_depense")),
            net_result=_safe_float(finance.get("resultat_net")),
            institution_id=institution_id,
            executive_summary=summary,
            kpi_snapshot=kpis,
        )
        db_session.add(report)
        db_session.flush()

        now_tag = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base_dir = REPORTS_DIR / period
        pdf_path = base_dir / f"report_{report.id}_{now_tag}.pdf"
        excel_path = base_dir / f"report_{report.id}_{now_tag}.xlsx"

        render_pdf_report(summary, kpis, pdf_path, period, report_type)
        export_excel_report(kpis, excel_path)

        report.pdf_path = str(pdf_path)
        report.excel_path = str(excel_path)
        db_session.flush()

        objectives = generate_smart_objectives(db_session, str(report.id), kpis)
        db_session.commit()

        return {
            "status": "success",
            "report_id": str(report.id),
            "pdf_path": str(pdf_path),
            "excel_path": str(excel_path),
            "objectives_count": len(objectives),
        }
    except Exception as exc:
        print(f"[ERROR] Report generation failed: {exc}")
        db_session.rollback()
        return {"status": "error", "message": str(exc)}
    finally:
        db_session.close()


@celery_app.task(name="finance_reports.generate_report")
def generate_report(period: str, report_type: str, institution_id: str = "UCAR") -> Dict[str, Any]:
    """Celery task entrypoint for periodic and manual report generation."""
    return run_report_generation(period=period, report_type=report_type, institution_id=institution_id)
