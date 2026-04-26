"""
Database models for finance, partnerships, and HR
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Date
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from app.core.models import BaseModel


class Budget(BaseModel):
    """Budget model"""

    __tablename__ = "budgets"

    department = Column(String(255), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    allocated_amount = Column(Float, nullable=False)
    spent_amount = Column(Float, default=0.0)
    category = Column(String(100), nullable=False)


class Partnership(BaseModel):
    """Partnership model"""

    __tablename__ = "partnerships"

    name = Column(String(255), nullable=False, unique=True)
    partner_type = Column(String(100), nullable=False)
    status = Column(String(50), default="active", nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    contact_email = Column(String(255), nullable=True)


class FinancialReport(BaseModel):
    """Financial report model"""

    __tablename__ = "financial_reports"

    report_type = Column(String(100), nullable=False)
    fiscal_period = Column(String(50), nullable=False)
    total_revenue = Column(Float, nullable=False)
    total_expenses = Column(Float, nullable=False)
    net_result = Column(Float, nullable=False)
    report_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    institution_id = Column(String(100), nullable=True)
    executive_summary = Column(Text, nullable=True)
    kpi_snapshot = Column(JSON, nullable=True)
    pdf_path = Column(String(500), nullable=True)
    excel_path = Column(String(500), nullable=True)


class Ranking(BaseModel):
    """Institution ranking model"""

    __tablename__ = "rankings"

    ranking_organization = Column(String(255), nullable=False)
    rank_year = Column(Integer, nullable=False)
    overall_rank = Column(Integer, nullable=False)
    category = Column(String(100), nullable=False)
    score = Column(Float, nullable=True)
    institution_id = Column(String(100), nullable=True)
    institution_name = Column(String(255), nullable=True)
    composite_score = Column(Float, nullable=True)
    academic_score = Column(Float, nullable=True)
    finance_score = Column(Float, nullable=True)
    hr_score = Column(Float, nullable=True)
    esg_score = Column(Float, nullable=True)
    research_score = Column(Float, nullable=True)
    domain_breakdown = Column(JSON, nullable=True)
    badges = Column(JSON, nullable=True)
    scored_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Employee(BaseModel):
    """Employee model"""

    __tablename__ = "employees"

    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    employee_id = Column(String(50), unique=True, nullable=False)
    department = Column(String(100), nullable=False)
    position = Column(String(100), nullable=False)
    hire_date = Column(Date, nullable=False)
    employment_status = Column(String(50), default="active", nullable=False)


class Contract(BaseModel):
    """Employment contract model"""

    __tablename__ = "contracts"

    employee_id = Column(UUID(as_uuid=True), nullable=False)
    contract_type = Column(String(100), nullable=False)  # permanent, temporary, etc.
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    salary = Column(Float, nullable=False)
    status = Column(String(50), default="active", nullable=False)


class Absenteeism(BaseModel):
    """Absenteeism record model"""

    __tablename__ = "absenteeism"

    employee_id = Column(UUID(as_uuid=True), nullable=False)
    absence_date = Column(Date, nullable=False)
    reason = Column(String(100), nullable=True)
    hours_missed = Column(Float, default=8.0)


class EmploymentOutcome(BaseModel):
    """Employment outcomes model"""

    __tablename__ = "employment_outcomes"

    graduate_year = Column(Integer, nullable=False)
    total_graduates = Column(Integer, nullable=False)
    employed_count = Column(Integer, nullable=False)
    employment_rate = Column(Float, nullable=False)
    average_salary = Column(Float, nullable=True)
    sector = Column(String(100), nullable=True)



class KpiTarget(BaseModel):
    """SMART KPI objectives generated after each report"""
    __tablename__ = "kpi_targets"

    report_id = Column(String, nullable=False)       # links to financial_reports
    domain = Column(String(100), nullable=False)     # e.g. "budget", "hr", "research"
    objective = Column(Text, nullable=False)         # SMART objective text
    title = Column(String(255), nullable=True)
    metric = Column(String(255), nullable=True)      # e.g. "reduce absenteeism by 10%"
    target_value = Column(String(255), nullable=True)
    deadline = Column(Date, nullable=True)
    responsible_role = Column(String(255), nullable=True)
    priority = Column(Integer, default=1)            # 1=highest priority, 5=lowest priority
    status = Column(String(50), default="pending")   # pending, in_progress, achieved
    ai_generated = Column(Boolean, default=False, nullable=False)

class Badge(BaseModel):
    """Badges earned by institutions per KPI domain"""
    __tablename__ = "badges"

    institution_code = Column(String(100), nullable=False)  # anonymized code
    domain = Column(String(100), nullable=False)            # e.g. "finance", "hr"
    badge_name = Column(String(255), nullable=False)        # e.g. "Budget Champion"
    badge_level = Column(String(50), default="bronze")      # bronze/silver/gold
    awarded_at = Column(DateTime, default=datetime.utcnow)
    score = Column(Float, nullable=True)


class KpiMetric(BaseModel):
    """Generic KPI metric store, including forecast values."""

    __tablename__ = "kpi_metrics"

    institution_id = Column(String(100), nullable=True)
    domain = Column(String(100), nullable=False)
    indicator = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_forecast = Column(Boolean, default=False, nullable=False)
    forecast_horizon_days = Column(Integer, nullable=True)
    lower_bound = Column(Float, nullable=True)
    upper_bound = Column(Float, nullable=True)
    source = Column(String(100), nullable=True)
