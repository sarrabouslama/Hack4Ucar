"""
Database models for finance, partnerships, and HR
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Date
from sqlalchemy import Uuid as UUID
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


class Ranking(BaseModel):
    """Institution ranking model"""

    __tablename__ = "rankings"

    ranking_organization = Column(String(255), nullable=False)
    rank_year = Column(Integer, nullable=False)
    overall_rank = Column(Integer, nullable=False)
    category = Column(String(100), nullable=False)
    score = Column(Float, nullable=True)


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
