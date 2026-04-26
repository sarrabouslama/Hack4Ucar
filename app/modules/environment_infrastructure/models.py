"""
Pydantic models for environment and infrastructure
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class UtilityBillInput(BaseModel):
    """Utility bill consumed by the environmental scoring engine."""

    utility_type: Literal["electricity", "gas", "water"]
    period_label: str = Field(..., description="Reporting period such as 2026-S1 or 2026-Q1")
    consumption_value: float = Field(..., ge=0)
    consumption_unit: Literal["kwh", "m3"]
    invoice_amount: Optional[float] = Field(default=None, ge=0)


class EmailMetricInput(BaseModel):
    """Email activity metrics collected without reading content."""

    period_label: str = Field(..., description="Reporting period such as 2026-S1 or 2026-04")
    emails_sent: int = Field(..., ge=0)
    average_email_size_kb: float = Field(..., ge=0)
    attachments_count: int = Field(default=0, ge=0)
    average_attachment_size_kb: float = Field(default=0.0, ge=0)
    average_recipients: float = Field(default=1.0, ge=1.0)
    stored_days: int = Field(default=30, ge=0)


class RSEInitiativeInput(BaseModel):
    """Declared and optionally documented CSR initiative."""

    title: str
    category: Literal["solar", "lighting", "waste", "water", "mobility", "other"]
    description: str
    estimated_co2_reduction_kg: float = Field(..., ge=0)
    proof_document_present: bool = False
    proof_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class InstitutionScorecardRequest(BaseModel):
    """Institutional payload used for energy and ESG assessment."""

    institution_id: str
    institution_name: str
    surface_m2: float = Field(..., gt=0)
    students_count: int = Field(..., ge=0)
    employees_count: int = Field(..., ge=0)
    utility_bills: List[UtilityBillInput]
    email_metrics: List[EmailMetricInput] = Field(default_factory=list)
    rse_initiatives: List[RSEInitiativeInput] = Field(default_factory=list)


class ConsumptionBreakdown(BaseModel):
    utility_type: str
    total_consumption: float
    normalized_unit: str
    co2_kg: float
    share_percent: float
    intensity_per_person_kg: float
    intensity_per_m2_kg: float


class RSEInitiativeAssessment(BaseModel):
    title: str
    category: str
    reliability_status: Literal["fiable", "a_verifier"]
    estimated_reduction_kg: float
    confidence: float


class TimeSeriesPoint(BaseModel):
    period_label: str
    gross_co2_kg: float
    optimized_co2_kg: float
    verdict: str


class EnvironmentalScorecardResponse(BaseModel):
    institution_id: str
    institution_name: str
    total_people: int
    gross_co2_kg: float
    optimized_co2_kg: float
    co2_per_person_kg: float
    annualized_co2_per_person_kg: float
    benchmark_per_person_kg: float
    verdict: Literal["consommation optimale", "dans la norme", "surconsommation detectee"]
    environmental_score: float = Field(..., ge=0, le=100)
    subdimension_scores: dict[str, float]
    total_rse_reduction_kg: float
    breakdown: List[ConsumptionBreakdown]
    rse_assessments: List[RSEInitiativeAssessment]
    timeline: List[TimeSeriesPoint]
    insights: List[str]


class EmailPeriodEstimate(BaseModel):
    period_label: str
    emails_sent: int
    estimated_energy_kwh: float
    estimated_co2_kg: float
    average_recipients: float
    attachment_ratio: float


class EmailFootprintRequest(BaseModel):
    institution_id: str
    institution_name: str
    students_count: int = Field(..., ge=0)
    employees_count: int = Field(..., ge=0)
    email_metrics: List[EmailMetricInput]


class EmailFootprintResponse(BaseModel):
    institution_id: str
    institution_name: str
    total_people: int
    total_emails_sent: int
    total_estimated_energy_kwh: float
    total_estimated_co2_kg: float
    annualized_co2_per_person_kg: float
    digital_responsibility_score: float = Field(..., ge=0, le=100)
    verdict: Literal["usage numerique sobre", "usage numerique modere", "surconsommation numerique"]
    methodology: List[str]
    period_breakdown: List[EmailPeriodEstimate]
