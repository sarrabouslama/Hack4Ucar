"""
Centralized document routing service.
Maps Gemini-extracted module fields → KPI entries via KPIService.
All document-to-KPI routing goes through here, eliminating duplication
between upload_and_process, extract_document_data, and process-scan.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.kpis.services import KPIService, AlertService


# ---------------------------------------------------------------------------
# Per-module routing functions
# Each receives (db, kpi_service, alert_service, institution_id, fields, period_label)
# and returns a list of created KPI dicts for audit/response.
# ---------------------------------------------------------------------------

def _route_environment(
    kpi_service: KPIService,
    alert_service: AlertService,
    institution_id: UUID,
    fields: Dict[str, Any],
    period_label: str,
) -> List[Dict[str, Any]]:
    from app.modules.environment_infrastructure.db_models import EnergyConsumption, CarbonFootprint
    import uuid

    created = []
    now = datetime.utcnow()

    # 1. Electricity consumption (kWh)
    elec_qty = fields.get("electricity_consumption_quantity") or fields.get("consumption_value") or fields.get("electricity_consumption_kwh")
    if elec_qty is not None:
        # standard KPI
        kpi = kpi_service.create_kpi(
            institution_id=institution_id,
            domain="environment",
            indicator="electricity_consumption_kwh",
            period=period_label,
            value=float(elec_qty),
            unit="kWh",
            reporting_date=now,
            data_source="document_ingestion",
            notes=f"Extracted from document",
        )
        alert_service.check_and_create_alerts(institution_id, "environment", "electricity_consumption_kwh")
        created.append({"indicator": "electricity_consumption_kwh", "value": float(elec_qty), "kpi_id": str(kpi.id)})

        # module-specific table
        try:
            db = kpi_service.db
            energy = EnergyConsumption(
                id=uuid.uuid4(),
                facility_id=str(institution_id),
                consumption_kwh=float(elec_qty),
                energy_type="electricity",
                reporting_month=period_label,
                measurement_date=now
            )
            db.add(energy)
        except Exception:
            pass

    # 2. Carbon footprint
    co2 = fields.get("carbon_footprint_kg")
    if co2 is not None:
        # standard KPI
        kpi = kpi_service.create_kpi(
            institution_id=institution_id,
            domain="environment",
            indicator="carbon_footprint_kg",
            period=period_label,
            value=float(co2),
            unit="kg",
            reporting_date=now,
            data_source="document_ingestion",
        )
        alert_service.check_and_create_alerts(institution_id, "environment", "carbon_footprint_kg")
        created.append({"indicator": "carbon_footprint_kg", "value": float(co2), "kpi_id": str(kpi.id)})

        # module-specific table
        try:
            db = kpi_service.db
            carbon = CarbonFootprint(
                id=uuid.uuid4(),
                reporting_period=period_label,
                co2_emissions=float(co2) / 1000.0, # Convert kg to tons as expected by model
                scope="scope2",
                measurement_date=now
            )
            db.add(carbon)
        except Exception:
            pass

    return created


def _route_finance(
    db: Session,
    kpi_service: KPIService,
    alert_service: AlertService,
    institution_id: UUID,
    fields: Dict[str, Any],
    period_label: str,
) -> List[Dict[str, Any]]:
    from app.modules.finance_partnerships_hr.services import FormService
    from app.modules.finance_partnerships_hr.models import BudgetReportInput
    import asyncio

    created = []
    allocated = float(fields.get("allocated_amount") or fields.get("total_revenue") or 0.0)
    spent = float(fields.get("spent_amount") or fields.get("total_expenses") or fields.get("total_amount_due") or 0.0)
    department = str(fields.get("department", "general"))
    fiscal_year = int(fields.get("fiscal_year") or datetime.utcnow().year)
    category = str(fields.get("category", "general"))

    if spent > 0 or allocated > 0:
        form_service = FormService(db)
        budget_input = BudgetReportInput(
            department=department,
            fiscal_year=fiscal_year,
            allocated_amount=allocated,
            spent_amount=spent,
            category=category,
        )
        # Run async in sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, form_service.submit_budget_report(budget_input))
                    result = future.result()
            else:
                result = loop.run_until_complete(form_service.submit_budget_report(budget_input))
        except Exception:
            result = {"status": "error"}

        created.append({
            "indicator": "budget_entry",
            "value": spent,
            "department": department,
            "status": result.get("status", "unknown"),
        })

    return created


def _route_education_research(
    kpi_service: KPIService,
    alert_service: AlertService,
    institution_id: UUID,
    fields: Dict[str, Any],
    period_label: str,
) -> List[Dict[str, Any]]:
    created = []
    now = datetime.utcnow()

    courses = fields.get("courses", [])
    if courses:
        grades = [c.get("grade") for c in courses if c.get("grade") is not None]
        if grades:
            avg_grade = sum(grades) / len(grades)
            # Map to success_rate: grade >= 10 out of 20 = passing
            passing = [g for g in grades if g >= 10]
            success_rate = (len(passing) / len(grades)) * 100

            kpi = kpi_service.create_kpi(
                institution_id=institution_id,
                domain="academic",
                indicator="success_rate",
                period=period_label,
                value=round(success_rate, 2),
                unit="%",
                reporting_date=now,
                data_source="document_ingestion",
                notes=f"Derived from {len(courses)} courses; student: {fields.get('student_full_name', 'unknown')}",
            )
            alert_service.check_and_create_alerts(institution_id, "academic", "success_rate")
            created.append({"indicator": "success_rate", "value": round(success_rate, 2), "kpi_id": str(kpi.id)})

    # Direct numeric indicators from fields
    direct_map = {
        "success_rate": ("%", "success_rate"),
        "dropout_rate": ("%", "dropout_rate"),
        "attendance_rate": ("%", "attendance_rate"),
        "grade_repetition_rate": ("%", "grade_repetition_rate"),
        "exam_pass_rate": ("%", "exam_pass_rate"),
        "publication_count": ("count", "publication_count"),
        "research_funding": ("DT", "research_funding"),
    }
    for field_key, (unit, indicator) in direct_map.items():
        val = fields.get(field_key)
        if val is not None:
            kpi = kpi_service.create_kpi(
                institution_id=institution_id,
                domain="academic",
                indicator=indicator,
                period=period_label,
                value=float(val),
                unit=unit,
                reporting_date=now,
                data_source="document_ingestion",
            )
            alert_service.check_and_create_alerts(institution_id, "academic", indicator)
            created.append({"indicator": indicator, "value": float(val), "kpi_id": str(kpi.id)})

    return created


def _route_hr(
    kpi_service: KPIService,
    alert_service: AlertService,
    institution_id: UUID,
    fields: Dict[str, Any],
    period_label: str,
) -> List[Dict[str, Any]]:
    created = []
    now = datetime.utcnow()

    salary = fields.get("salary")
    if salary is not None:
        kpi = kpi_service.create_kpi(
            institution_id=institution_id,
            domain="hr",
            indicator="average_salary",
            period=period_label,
            value=float(salary),
            unit="DT",
            reporting_date=now,
            data_source="document_ingestion",
            notes=f"Position: {fields.get('position', 'unknown')}",
        )
        alert_service.check_and_create_alerts(institution_id, "hr", "average_salary")
        created.append({"indicator": "average_salary", "value": float(salary), "kpi_id": str(kpi.id)})

    return created


def _route_partnerships(
    kpi_service: KPIService,
    alert_service: AlertService,
    institution_id: UUID,
    fields: Dict[str, Any],
    period_label: str,
) -> List[Dict[str, Any]]:
    created = []
    now = datetime.utcnow()

    contract_value = fields.get("contract_value")
    if contract_value is not None:
        kpi = kpi_service.create_kpi(
            institution_id=institution_id,
            domain="partnerships",
            indicator="contract_value",
            period=period_label,
            value=float(contract_value),
            unit="DT",
            reporting_date=now,
            data_source="document_ingestion",
            notes=f"Partner: {fields.get('partner_name', 'unknown')}",
        )
        alert_service.check_and_create_alerts(institution_id, "partnerships", "contract_value")
        created.append({"indicator": "contract_value", "value": float(contract_value), "kpi_id": str(kpi.id)})

    return created


def _route_infrastructure(
    kpi_service: KPIService,
    alert_service: AlertService,
    institution_id: UUID,
    fields: Dict[str, Any],
    period_label: str,
) -> List[Dict[str, Any]]:
    created = []
    now = datetime.utcnow()

    budget = fields.get("budget")
    if budget is not None:
        kpi = kpi_service.create_kpi(
            institution_id=institution_id,
            domain="infrastructure",
            indicator="infrastructure_budget",
            period=period_label,
            value=float(budget),
            unit="DT",
            reporting_date=now,
            data_source="document_ingestion",
            notes=f"Project: {fields.get('project_name', 'unknown')}, Status: {fields.get('status', 'unknown')}",
        )
        alert_service.check_and_create_alerts(institution_id, "infrastructure", "infrastructure_budget")
        created.append({"indicator": "infrastructure_budget", "value": float(budget), "kpi_id": str(kpi.id)})

    return created


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

ROUTER_MAP = {
    "environment": _route_environment,
    "finance": _route_finance,
    "education_research": _route_education_research,
    "hr": _route_hr,
    "partnerships": _route_partnerships,
    "infrastructure": _route_infrastructure,
}


def route_gemini_modules(
    db: Session,
    institution_id: UUID,
    modules: List[Dict[str, Any]],
    period_label: str = "monthly",
) -> Dict[str, Any]:
    kpi_service = KPIService(db)
    alert_service = AlertService(db)
    results: Dict[str, Any] = {}

    for entry in modules:
        module_name = entry.get("module", "")
        fields = entry.get("fields", {}) or {}
        confidence = entry.get("confidence", 0.0)

        if module_name == "documents_ingestion" or not fields:
            continue

        router_fn = ROUTER_MAP.get(module_name)
        if router_fn is None:
            continue

        try:
            if module_name == "finance":
                created = router_fn(db, kpi_service, alert_service, institution_id, fields, period_label)
            else:
                created = router_fn(kpi_service, alert_service, institution_id, fields, period_label)

            results[module_name] = {
                "confidence": confidence,
                "kpis_created": len(created),
                "entries": created,
            }
        except Exception as exc:
            results[module_name] = {"error": str(exc), "kpis_created": 0}

    return results


def route_scan_json(
    db: Session,
    institution_id: UUID,
    scan_data: Dict[str, Any],
    period_label: str = "monthly",
) -> Dict[str, Any]:
    from app.services.kpi_calculator import KPICalculator

    kpi_service = KPIService(db)
    alert_service = AlertService(db)
    calculator = KPICalculator()
    result = calculator.calculate_all(scan_data)
    indicators = result.get("indicators", {})
    warnings = result.get("warnings", [])

    now = datetime.utcnow()
    created = []

    for indicator, value in indicators.items():
        if value is None:
            continue
        kpi = kpi_service.create_kpi(
            institution_id=institution_id,
            domain="academic",
            indicator=indicator,
            period=period_label,
            value=float(value),
            unit="%",
            reporting_date=now,
            data_source="scan_form",
        )
        alert_service.check_and_create_alerts(institution_id, "academic", indicator)
        created.append({"indicator": indicator, "value": float(value), "kpi_id": str(kpi.id)})

    return {
        "indicators": indicators,
        "warnings": warnings,
        "kpis_persisted": len(created),
        "kpis": created,
        "metadata": result.get("metadata", {}),
    }