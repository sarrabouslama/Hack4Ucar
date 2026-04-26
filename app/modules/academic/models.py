"""
Academic Module — Pydantic Schemas
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Saisie de données (côté Institution) ───────────────────────────────────

class AcademicKPISubmit(BaseModel):
    """Formulaire guidé saisie académique institution"""
    success_rate: Optional[float] = Field(None, ge=0, le=100, description="Taux de réussite (%)")
    dropout_rate: Optional[float] = Field(None, ge=0, le=100, description="Taux d'abandon (%)")
    attendance_rate: Optional[float] = Field(None, ge=0, le=100, description="Taux de présence (%)")
    grade_repetition_rate: Optional[float] = Field(None, ge=0, le=100, description="Taux de redoublement (%)")
    exam_pass_rate: Optional[float] = Field(None, ge=0, le=100, description="Taux de passage examens (%)")
    reporting_date: datetime = Field(..., description="Mois/Année de la période")
    notes: Optional[str] = None


class AcademicKPIResponse(BaseModel):
    """Réponse après saisie"""
    success: bool
    message: str
    kpis_created: int
    alerts_generated: int
    preview: Dict[str, Optional[float]]


# ── KPI View ────────────────────────────────────────────────────────────────

class KPIPoint(BaseModel):
    date: str
    value: float
    unit: str = "%"


class IndicatorSummary(BaseModel):
    indicator: str
    current_value: float
    unit: str = "%"
    trend: str          # "up" | "down" | "stable"
    change_pct: float
    status: str         # "excellent" | "good" | "warning" | "critical"


class InstitutionAcademicView(BaseModel):
    institution_id: str
    institution_name: str
    period: str
    indicators: List[IndicatorSummary]
    overall_score: float
    rank: Optional[int] = None


# ── Dashboard UCAR ──────────────────────────────────────────────────────────

class ConsolidatedKPI(BaseModel):
    indicator: str
    avg_value: float
    min_value: float
    max_value: float
    std_dev: float
    total_institutions: int
    unit: str = "%"


class InstitutionRankRow(BaseModel):
    rank: int
    institution_name: str
    institution_code: str
    success_rate: float
    dropout_rate: float
    attendance_rate: float
    overall_score: float
    trend: str
    badges: List[str] = []
    # anonymized_name: str  — utilisé côté institution


class UCARDashboard(BaseModel):
    total_institutions: int
    consolidated_kpis: List[ConsolidatedKPI]
    rankings: List[InstitutionRankRow]
    active_alerts_count: int
    at_risk_count: int
    top_performer: str
    generated_at: str


# ── Alertes ─────────────────────────────────────────────────────────────────

class AlertDetail(BaseModel):
    id: str
    institution_name: str
    institution_code: str
    severity: str           # "critical" | "warning" | "info"
    indicator: str
    actual_value: float
    threshold_value: float
    message: str
    xai_explanation: Optional[str] = None
    xai_factors: Optional[Dict[str, float]] = None
    created_at: str


# ── Prédictions Prophet ──────────────────────────────────────────────────────

class ForecastPoint(BaseModel):
    date: str
    predicted: float
    lower: float
    upper: float


class PredictionResult(BaseModel):
    institution_name: str
    indicator: str
    horizon_days: int
    current_value: float
    predicted_value: float
    change_pct: float
    risk_level: str         # "low" | "medium" | "high" | "critical"
    forecast: List[ForecastPoint]


# ── XAI "Pourquoi ?" ─────────────────────────────────────────────────────────

class WhyRequest(BaseModel):
    institution_id: UUID
    indicator: str          # "dropout_rate" | "success_rate" | etc.


class WhyResponse(BaseModel):
    institution_name: str
    indicator: str
    current_value: float
    explanation: str
    factors: Dict[str, float]
    trend: Dict[str, Any]
    recommendation: str
    generated_at: str
