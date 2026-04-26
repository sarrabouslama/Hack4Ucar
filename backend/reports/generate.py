"""
Compatibility wrapper for report generation.
"""

from app.modules.finance_partnerships_hr.reports.generate import (  # noqa: F401
    aggregate_kpis,
    celery_app,
    generate_report,
    run_report_generation,
)
