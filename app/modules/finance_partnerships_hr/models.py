"""
Pydantic models for finance, partnerships, and HR
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class BudgetKPI(BaseModel):
    department: str
    allocated: float
    spent: float
    utilization_pct: float

class SmartObjective(BaseModel):
    domain: str
    objective: str
    metric: str
    deadline: date
    priority: int

class LeaderboardEntry(BaseModel):
    rank: int
    identifier: str   # real name for UCAR, anonymous code for institutions
    composite_score: float
    badges: List[str]

class BudgetReportInput(BaseModel):
    department: str
    fiscal_year: int
    allocated_amount: float
    spent_amount: float
    category: str

class HrHeadcountInput(BaseModel):
    department: str
    count: int
    as_of_date: date

class ResearchProjectInput(BaseModel):
    title: str
    principal_investigator: str
    funding_amount: float
    start_date: date
