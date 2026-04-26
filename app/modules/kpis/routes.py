"""
KPI Routes - API endpoints for KPI management
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.kpis.models import (
    KPIEntryForm, KPIEntryBatch, KPIResponse, KPIAggregateResponse,
    PredictionRequest, PredictionResponse, AlertResponse, AlertAcknowledge, AlertResolve,
    WhyButtonRequest, WhyButtonResponse, DashboardSummary, KPITrendResponse,
    InstitutionCreate, InstitutionResponse, RankingResponse, APIResponse
)
from app.modules.kpis.services import KPIService, AlertService, RankingService
from app.modules.kpis.db_models import Institution, KPIMetric, KPIAggregate, Alert, Ranking

router = APIRouter(prefix="/api/v1/kpis", tags=["KPIs"])


# ==================== Institution Endpoints ====================

@router.post("/institutions", response_model=InstitutionResponse)
def create_institution(
    data: InstitutionCreate,
    db: Session = Depends(get_db)
):
    """Create a new institution"""
    import uuid
    institution = Institution(
        id=uuid.uuid4(),
        name=data.name,
        code=data.code,
        type=data.type,
        region=data.region,
        address=data.address,
        contact_email=data.contact_email,
        is_active="true"
    )
    db.add(institution)
    db.commit()
    db.refresh(institution)
    return institution


@router.get("/institutions", response_model=List[InstitutionResponse])
def list_institutions(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all institutions"""
    query = db.query(Institution)
    if active_only:
        query = query.filter(Institution.is_active == "true")
    return query.all()


@router.get("/institutions/{institution_id}", response_model=InstitutionResponse)
def get_institution(
    institution_id: UUID,
    db: Session = Depends(get_db)
):
    """Get institution by ID"""
    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution


# ==================== KPI Entry (Institution Side) ====================

@router.post("/submit", response_model=APIResponse)
def submit_kpi(
    data: KPIEntryForm,
    institution_id: UUID = Query(..., description="Institution ID"),
    db: Session = Depends(get_db)
):
    """Submit KPI data from an institution"""
    # Verify institution exists
    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    
    service = KPIService(db)
    kpi = service.create_kpi(
        institution_id=institution_id,
        domain=data.domain,
        indicator=data.indicator,
        period=data.period,
        value=data.value,
        unit=data.unit,
        reporting_date=data.reporting_date,
        data_source="manual",
        notes=data.notes
    )
    
    # Check for alerts
    alert_service = AlertService(db)
    alerts = alert_service.check_and_create_alerts(institution_id, data.domain, data.indicator)
    
    return APIResponse(
        success=True,
        message=f"KPI submitted successfully. {len(alerts)} alert(s) generated.",
        data={"kpi_id": str(kpi.id), "alerts_created": len(alerts)}
    )


@router.post("/submit-batch", response_model=APIResponse)
def submit_kpi_batch(
    data: KPIEntryBatch,
    institution_id: UUID = Query(..., description="Institution ID"),
    db: Session = Depends(get_db)
):
    """Submit multiple KPIs at once (batch)"""
    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    
    service = KPIService(db)
    alert_service = AlertService(db)
    
    created_kpis = []
    total_alerts = 0
    
    for kpi_data in data.kpis:
        kpi = service.create_kpi(
            institution_id=institution_id,
            domain=kpi_data.domain,
            indicator=kpi_data.indicator,
            period=kpi_data.period,
            value=kpi_data.value,
            unit=kpi_data.unit,
            reporting_date=kpi_data.reporting_date,
            data_source="manual",
            notes=kpi_data.notes
        )
        created_kpis.append(str(kpi.id))
        
        # Check for alerts
        alerts = alert_service.check_and_create_alerts(institution_id, kpi_data.domain, kpi_data.indicator)
        total_alerts += len(alerts)
    
    return APIResponse(
        success=True,
        message=f"Submitted {len(created_kpis)} KPIs. {total_alerts} alert(s) generated.",
        data={"kpis_created": len(created_kpis), "alerts_created": total_alerts}
    )


# ==================== Institution KPI View ====================

@router.get("/own", response_model=List[KPIResponse])
def get_own_kpis(
    institution_id: UUID = Query(...),
    domain: Optional[str] = None,
    period: Optional[str] = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """Get KPIs for the requesting institution only"""
    service = KPIService(db)
    kpis = service.get_institution_kpis(institution_id, domain, period, limit)
    return kpis


@router.get("/trend", response_model=KPITrendResponse)
def get_kpi_trend(
    institution_id: UUID = Query(...),
    domain: str = Query(...),
    indicator: str = Query(...),
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db)
):
    """Get KPI trend over time"""
    service = KPIService(db)
    trend = service.get_kpi_trend(institution_id, domain, indicator, months)
    return KPITrendResponse(
        institution_id=institution_id,
        domain=domain,
        indicator=indicator,
        trend=trend
    )


# ==================== UCAR Central - Consolidated KPIs ====================

@router.get("/consolidated", response_model=List[KPIAggregateResponse])
def get_consolidated_kpis(
    domain: Optional[str] = None,
    indicator: Optional[str] = None,
    period: str = Query("monthly"),
    db: Session = Depends(get_db)
):
    """Get consolidated KPIs across all institutions (UCAR Central only)"""
    service = KPIService(db)
    aggregates = service.get_consolidated_kpis(domain, indicator, period)
    return aggregates


@router.get("/dashboard-summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get summary for UCAR Central dashboard"""
    service = KPIService(db)
    return service.get_dashboard_summary()


@router.post("/aggregate", response_model=APIResponse)
def calculate_aggregate(
    domain: str = Query(...),
    indicator: str = Query(...),
    period: str = Query("monthly"),
    db: Session = Depends(get_db)
):
    """Calculate aggregate KPIs for a specific domain/indicator"""
    service = KPIService(db)
    aggregate = service.calculate_aggregate(domain, indicator, period)
    
    if not aggregate:
        return APIResponse(success=False, message="No data found for aggregation")
    
    return APIResponse(
        success=True,
        message="Aggregate calculated successfully",
        data={"aggregate_id": str(aggregate.id), "avg_value": aggregate.avg_value}
    )


# ==================== Alerts ====================

@router.get("/alerts", response_model=List[AlertResponse])
def get_alerts(
    institution_id: Optional[UUID] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """Get active alerts"""
    service = AlertService(db)
    alerts = service.get_active_alerts(institution_id, severity, limit)
    return alerts


@router.post("/alerts/acknowledge", response_model=APIResponse)
def acknowledge_alert(
    data: AlertAcknowledge,
    db: Session = Depends(get_db)
):
    """Acknowledge an alert"""
    service = AlertService(db)
    alert = service.acknowledge_alert(data.alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return APIResponse(success=True, message="Alert acknowledged")


@router.post("/alerts/resolve", response_model=APIResponse)
def resolve_alert(
    data: AlertResolve,
    db: Session = Depends(get_db)
):
    """Resolve an alert"""
    service = AlertService(db)
    alert = service.resolve_alert(data.alert_id, data.resolution_notes)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return APIResponse(success=True, message="Alert resolved")


# ==================== Rankings ====================

@router.get("/rankings", response_model=List[dict])
def get_rankings(
    period: str = Query("monthly"),
    anonymized: bool = Query(False, description="True for institution view, False for UCAR"),
    db: Session = Depends(get_db)
):
    """Get rankings (anonymized for institutions, full for UCAR)"""
    service = RankingService(db)
    return service.get_rankings(period, anonymized)


@router.post("/rankings/calculate", response_model=APIResponse)
def calculate_rankings(
    period: str = Query("monthly"),
    db: Session = Depends(get_db)
):
    """Calculate rankings for all institutions (UCAR only)"""
    service = RankingService(db)
    rankings = service.calculate_rankings(period)
    
    return APIResponse(
        success=True,
        message=f"Rankings calculated for {len(rankings)} institutions",
        data={"rankings_count": len(rankings)}
    )


# ==================== XAI - "Pourquoi ?" Button ====================

@router.post("/why", response_model=dict)
def explain_kpi_why(
    data: WhyButtonRequest,
    db: Session = Depends(get_db)
):
    """Explain why a KPI has its current value (XAI)"""
    from app.services.xai_service import XAIService
    
    xai_service = XAIService(db)
    result = xai_service.explain_kpi(
        data.institution_id,
        data.domain,
        data.indicator
    )
    return result


# ==================== Predictions ====================

@router.post("/predict", response_model=dict)
def predict_kpi(
    data: PredictionRequest,
    db: Session = Depends(get_db)
):
    """Generate predictions for a KPI using Prophet"""
    from app.services.prediction_service import PredictionService
    
    service = PredictionService(db)
    result = service.predict_kpi(
        data.institution_id,
        data.domain,
        data.indicator,
        data.horizon_days
    )
    return result


@router.post("/predict/all-domains", response_model=dict)
def predict_all_domains(
    institution_id: UUID = Query(...),
    horizon_days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db)
):
    """Generate predictions for all KPIs of an institution"""
    from app.services.prediction_service import PredictionService
    
    service = PredictionService(db)
    result = service.predict_all_domains(institution_id, horizon_days)
    return result