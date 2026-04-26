"""
KPI Pydantic schemas for request/response validation
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# KPI Schemas
class KPIBase(BaseModel):
    domain: str
    indicator: str
    period: str
    value: float
    unit: Optional[str] = None
    reporting_date: Optional[datetime] = None
    data_source: Optional[str] = "manual"
    notes: Optional[str] = None


class KPICreate(KPIBase):
    institution_id: UUID


class KPIResponse(KPIBase):
    id: UUID
    institution_id: UUID
    reporting_date: datetime

    class Config:
        from_attributes = True


class KPIAggregateResponse(BaseModel):
    id: UUID
    domain: str
    indicator: str
    period: str
    reporting_date: datetime
    avg_value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    std_dev: Optional[float] = None
    total_count: Optional[int] = None

    class Config:
        from_attributes = True


# Prediction Schemas
class PredictionRequest(BaseModel):
    institution_id: UUID
    domain: str
    indicator: str
    horizon_days: int = Field(default=30, ge=7, le=90)


class PredictionResponse(BaseModel):
    institution_id: str
    domain: str
    indicator: str
    horizon_days: int
    last_prediction: Dict[str, Any]
    forecast: List[Dict[str, Any]]
    model_info: Dict[str, Any]


# Alert Schemas
class AlertResponse(BaseModel):
    id: UUID
    institution_id: UUID
    kpi_metric_id: Optional[UUID] = None
    severity: str
    status: str
    title: str
    message: str
    xai_factors: Optional[Dict[str, float]] = None
    xai_explanation: Optional[str] = None
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertAcknowledge(BaseModel):
    alert_id: UUID


class AlertResolve(BaseModel):
    alert_id: UUID
    resolution_notes: Optional[str] = None


# XAI/Why Button Schemas
class WhyButtonRequest(BaseModel):
    institution_id: UUID
    domain: str
    indicator: str


class WhyButtonResponse(BaseModel):
    kpi: Dict[str, Any]
    analysis: Dict[str, Any]
    explanation: str
    generated_at: str


# Dashboard Schemas
class DashboardSummary(BaseModel):
    total_institutions: int
    kpis_by_domain: Dict[str, int]
    latest_aggregates: List[Dict[str, Any]]


class KPITrendResponse(BaseModel):
    institution_id: UUID
    domain: str
    indicator: str
    trend: List[Dict[str, Any]]


# Institution Schemas
class InstitutionBase(BaseModel):
    name: str
    code: str
    type: str = "institution"
    region: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[str] = None


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionResponse(InstitutionBase):
    id: UUID
    is_active: str
    created_at: datetime

    class Config:
        from_attributes = True


# Ranking Schemas
class RankingResponse(BaseModel):
    id: UUID
    institution_id: UUID
    period: str
    reporting_date: datetime
    overall_score: float
    academic_score: Optional[float] = None
    finance_score: Optional[float] = None
    esg_score: Optional[float] = None
    rank: int
    badges: Optional[List[str]] = None

    class Config:
        from_attributes = True


# KPI Entry Form Schemas (for Institutions)
class KPIEntryForm(BaseModel):
    """Schema for institution KPI data entry"""
    domain: str = Field(..., description="Domain: academic, finance, hr, research, esg, infrastructure, partnerships, employment")
    indicator: str = Field(..., description="Specific indicator name")
    period: str = Field(..., description="monthly, semestrial, or annual")
    value: float = Field(..., description="KPI value")
    unit: Optional[str] = Field(None, description="Unit: %, number, currency, etc.")
    reporting_date: datetime = Field(..., description="Date of the reporting period")
    notes: Optional[str] = Field(None, description="Additional notes")


class KPIEntryBatch(BaseModel):
    """Batch KPI entry for institutions"""
    kpis: List[KPIEntryForm]


# Generic API Response
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Any] = None