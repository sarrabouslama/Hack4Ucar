"""
Academic Module — Routes API
Endpoints: dashboard UCAR, saisie institution, alertes, prédictions, XAI
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import numpy as np

from app.core.database import get_db
from app.modules.kpis.db_models import Institution, KPIMetric, KPIAggregate, Alert, Ranking
from app.services.kpi_calculator import KPICalculator
from app.modules.academic.models import (
    AcademicKPISubmit, AcademicKPIResponse,
    UCARDashboard, ConsolidatedKPI, InstitutionRankRow,
    AlertDetail, PredictionResult, ForecastPoint,
    WhyRequest, WhyResponse,
)

router = APIRouter(prefix="/api/v1/academic", tags=["Academic AI"])

@router.post("/process-scan")
def process_document_scan(
    data: Dict[str, Any], 
    institution_id: Optional[UUID] = Query(None), 
    db: Session = Depends(get_db)
):
    """
    Traite un JSON brut issu du scanner et calcule les indicateurs.
    If institution_id is provided, it persists them using the document_router.
    """
    from app.shared.document_router import route_scan_json
    
    if institution_id:
        return route_scan_json(db, institution_id, data)
    
    calculator = KPICalculator()
    return calculator.calculate_all(data)

ACADEMIC_INDICATORS = [
    "success_rate", "dropout_rate", "attendance_rate",
    "grade_repetition_rate", "exam_pass_rate"
]

THRESHOLDS = {
    "success_rate":         {"warning": 60,  "critical": 50,  "higher_is_better": True},
    "dropout_rate":         {"warning": 15,  "critical": 20,  "higher_is_better": False},
    "attendance_rate":      {"warning": 70,  "critical": 60,  "higher_is_better": True},
    "grade_repetition_rate":{"warning": 15,  "critical": 20,  "higher_is_better": False},
    "exam_pass_rate":       {"warning": 60,  "critical": 50,  "higher_is_better": True},
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_kpi_status(indicator: str, value: float) -> str:
    cfg = THRESHOLDS.get(indicator, {})
    hib = cfg.get("higher_is_better", True)
    warn, crit = cfg.get("warning", 60), cfg.get("critical", 50)
    if hib:
        if value >= warn: return "good"
        if value >= crit: return "warning"
        return "critical"
    else:
        if value <= warn: return "good"
        if value <= crit: return "warning"
        return "critical"


def _get_trend(values: list) -> tuple:
    """Retourne (direction, change_pct)"""
    if len(values) < 2:
        return "stable", 0.0
    first, last = values[0], values[-1]
    if last == 0:
        return "stable", 0.0
    change = ((first - last) / last) * 100
    if change > 1:   return "up",   round(change, 1)
    if change < -1:  return "down", round(change, 1)
    return "stable", 0.0


def _get_inst_or_404(institution_id: UUID, db: Session) -> Institution:
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution non trouvée")
    return inst


# ─── 1. Saisie KPIs — côté Institution ───────────────────────────────────────

@router.post("/submit", response_model=AcademicKPIResponse)
def submit_academic_kpis(
    data: AcademicKPISubmit,
    institution_id: UUID = Query(..., description="ID de l'institution"),
    db: Session = Depends(get_db),
):
    """Formulaire guidé : soumission des KPIs académiques d'une institution."""
    try:
        inst = _get_inst_or_404(institution_id, db)

        kpi_map = {
            "success_rate":         data.success_rate,
            "dropout_rate":         data.dropout_rate,
            "attendance_rate":      data.attendance_rate,
            "grade_repetition_rate":data.grade_repetition_rate,
            "exam_pass_rate":       data.exam_pass_rate,
        }

        created = []
        alerts_gen = 0
        for indicator, value in kpi_map.items():
            if value is not None:
                kpi = KPIMetric(
                    id=uuid.uuid4(),
                    institution_id=institution_id,
                    domain="academic",
                    indicator=indicator,
                    period="monthly",
                    value=value,
                    unit="%",
                    reporting_date=data.reporting_date,
                    data_source="form",
                    notes=data.notes,
                )
                db.add(kpi)
                created.append(kpi)

        db.commit()

        # Vérifier les seuils et créer des alertes
        inst = db.query(Institution).filter(Institution.id == institution_id).first()
        for kpi in created:
            status = _get_kpi_status(kpi.indicator, kpi.value)
            if status in ("warning", "critical"):
                cfg = THRESHOLDS[kpi.indicator]
                threshold = cfg["critical"] if status == "critical" else cfg["warning"]
                
                alert = Alert(
                    id=uuid.uuid4(),
                    institution_id=institution_id,
                    kpi_metric_id=kpi.id,
                    severity=status,
                    status="active",
                    title=f"Alerte : {kpi.indicator} — {inst.name}",
                    message=f"{kpi.indicator} à {kpi.value}% (seuil : {threshold}%)",
                    xai_factors={"threshold_violation": 1.0},
                    xai_explanation=f"Valeur {kpi.value}% dépasse le seuil {status} ({threshold}%)",
                    threshold_value=threshold,
                    actual_value=kpi.value,
                )
                db.add(alert)
                alerts_gen += 1
        
        db.commit()

        return AcademicKPIResponse(
            success=True,
            message=f"KPIs soumis pour {inst.name}",
            kpis_created=len(created),
            alerts_generated=alerts_gen,
            preview=kpi_map,
        )
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur Submit: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── 2. KPIs propres — côté Institution ──────────────────────────────────────

@router.get("/own")
def get_own_academic_kpis(
    institution_id: UUID = Query(...),
    months: int = Query(6, ge=1, le=18),
    db: Session = Depends(get_db),
):
    """KPIs académiques de l'institution (vue institution — ses données seulement)."""
    inst = _get_inst_or_404(institution_id, db)

    result = {}
    for indicator in ACADEMIC_INDICATORS:
        kpis = db.query(KPIMetric).filter(
            KPIMetric.institution_id == institution_id,
            KPIMetric.domain == "academic",
            KPIMetric.indicator == indicator,
        ).order_by(KPIMetric.reporting_date.desc()).limit(months).all()

        values = [k.value for k in kpis]
        direction, change = _get_trend(values)
        result[indicator] = {
            "current": values[0] if values else None,
            "trend": direction,
            "change_pct": change,
            "status": _get_kpi_status(indicator, values[0]) if values else "unknown",
            "history": [{"date": k.reporting_date.strftime("%Y-%m"), "value": k.value} for k in reversed(kpis)],
        }

    return {"institution_name": inst.name, "kpis": result}


# ─── 3. Dashboard UCAR Consolidé ─────────────────────────────────────────────

@router.get("/dashboard")
def get_ucar_dashboard(db: Session = Depends(get_db)):
    """Dashboard consolidé UCAR — agrégats toutes institutions + classement."""

    institutions = db.query(Institution).filter(Institution.is_active == True).all()
    total = len(institutions)

    # Agrégats par indicateur
    consolidated = []
    for indicator in ACADEMIC_INDICATORS:
        kpis = db.query(KPIMetric).filter(
            KPIMetric.domain == "academic",
            KPIMetric.indicator == indicator,
        ).order_by(KPIMetric.reporting_date.desc()).limit(total * 2).all()

        if not kpis:
            continue
        values = [k.value for k in kpis]
        consolidated.append({
            "indicator": indicator,
            "avg_value": round(np.mean(values), 1),
            "min_value": round(np.min(values), 1),
            "max_value": round(np.max(values), 1),
            "std_dev":   round(np.std(values), 1),
            "total_institutions": total,
            "unit": "%",
        })

    # Classement avec détails
    rankings = db.query(Ranking).filter(
        Ranking.period == "monthly"
    ).order_by(Ranking.rank.asc()).all()

    rank_rows = []
    for r in rankings:
        inst = db.query(Institution).filter(Institution.id == r.institution_id).first()
        if not inst:
            continue

        # Derniers KPIs
        def last_val(ind):
            k = db.query(KPIMetric).filter(
                KPIMetric.institution_id == inst.id,
                KPIMetric.domain == "academic",
                KPIMetric.indicator == ind,
            ).order_by(KPIMetric.reporting_date.desc()).first()
            return round(k.value, 1) if k else 0.0

        rank_rows.append({
            "rank": r.rank,
            "institution_name": inst.name,
            "institution_code": inst.code,
            "institution_id": str(inst.id),
            "success_rate": last_val("success_rate"),
            "dropout_rate": last_val("dropout_rate"),
            "attendance_rate": last_val("attendance_rate"),
            "overall_score": round(r.overall_score, 1),
            "badges": r.badges or [],
        })

    # Alertes actives
    active_alerts = db.query(Alert).filter(Alert.status == "active").count()
    critical_alerts = db.query(Alert).filter(
        Alert.status == "active", Alert.severity == "critical"
    ).count()

    top = rank_rows[0]["institution_name"] if rank_rows else "N/A"

    return {
        "total_institutions": total,
        "consolidated_kpis": consolidated,
        "rankings": rank_rows,
        "active_alerts_count": active_alerts,
        "critical_alerts_count": critical_alerts,
        "at_risk_count": critical_alerts,
        "top_performer": top,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ─── 4. Institutions à risque ─────────────────────────────────────────────────

@router.get("/at-risk")
def get_at_risk_institutions(
    threshold_dropout: float = Query(20.0, description="Seuil taux d'abandon (%)"),
    db: Session = Depends(get_db),
):
    """Liste des institutions avec taux d'abandon au-dessus du seuil."""
    institutions = db.query(Institution).filter(Institution.is_active == True).all()
    at_risk = []

    for inst in institutions:
        kpi = db.query(KPIMetric).filter(
            KPIMetric.institution_id == inst.id,
            KPIMetric.domain == "academic",
            KPIMetric.indicator == "dropout_rate",
        ).order_by(KPIMetric.reporting_date.desc()).first()

        if kpi and kpi.value >= threshold_dropout:
            at_risk.append({
                "institution_id": str(inst.id),
                "institution_name": inst.name,
                "institution_code": inst.code,
                "dropout_rate": round(kpi.value, 1),
                "threshold": threshold_dropout,
                "excess": round(kpi.value - threshold_dropout, 1),
                "severity": "critical" if kpi.value >= 20 else "warning",
            })

    at_risk.sort(key=lambda x: x["dropout_rate"], reverse=True)
    return {"count": len(at_risk), "institutions": at_risk}


# ─── 5. Top performers ────────────────────────────────────────────────────────

@router.get("/top-performers")
def get_top_performers(
    n: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """Top N institutions par taux de réussite."""
    rankings = db.query(Ranking).filter(
        Ranking.period == "monthly"
    ).order_by(Ranking.rank.asc()).limit(n).all()

    result = []
    for r in rankings:
        inst = db.query(Institution).filter(Institution.id == r.institution_id).first()
        if inst:
            result.append({
                "rank": r.rank,
                "institution_name": inst.name,
                "overall_score": round(r.overall_score, 1),
                "badges": r.badges or [],
            })
    return result


# ─── 6. Alertes académiques ───────────────────────────────────────────────────

@router.get("/alerts")
def get_academic_alerts(
    institution_id: Optional[UUID] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Alertes académiques actives avec explication XAI."""
    query = db.query(Alert).filter(Alert.status == "active")
    if institution_id:
        query = query.filter(Alert.institution_id == institution_id)
    if severity:
        query = query.filter(Alert.severity == severity)

    alerts = query.order_by(Alert.created_at.desc()).all()

    result = []
    for a in alerts:
        inst = db.query(Institution).filter(Institution.id == a.institution_id).first()
        kpi = db.query(KPIMetric).filter(KPIMetric.id == a.kpi_metric_id).first() if a.kpi_metric_id else None
        result.append({
            "id": str(a.id),
            "institution_id": str(a.institution_id),
            "institution_name": inst.name if inst else "Inconnue",
            "institution_code": inst.code if inst else "N/A",
            "severity": a.severity,
            "indicator": kpi.indicator if kpi else "N/A",
            "actual_value": a.actual_value,
            "threshold_value": a.threshold_value,
            "message": a.message,
            "xai_explanation": a.xai_explanation,
            "xai_factors": a.xai_factors,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })

    return {"count": len(result), "alerts": result}


# ─── 7. Prédictions Prophet ───────────────────────────────────────────────────

@router.get("/predictions/{institution_id}")
def get_academic_predictions(
    institution_id: UUID,
    indicator: str = Query("dropout_rate"),
    horizon_days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    """Prédictions Prophet J+30/J+90 pour un indicateur académique."""
    from app.services.prediction_service import PredictionService

    inst = _get_inst_or_404(institution_id, db)
    service = PredictionService(db)
    result = service.predict_kpi(institution_id, "academic", indicator, horizon_days)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Enrichir avec niveau de risque
    current_kpi = db.query(KPIMetric).filter(
        KPIMetric.institution_id == institution_id,
        KPIMetric.domain == "academic",
        KPIMetric.indicator == indicator,
    ).order_by(KPIMetric.reporting_date.desc()).first()

    current_val = current_kpi.value if current_kpi else 0
    predicted_val = result["last_prediction"]["predicted_value"]
    status = _get_kpi_status(indicator, predicted_val)

    return {
        "institution_name": inst.name,
        "indicator": indicator,
        "horizon_days": horizon_days,
        "current_value": round(current_val, 1),
        "predicted_value": predicted_val,
        "risk_level": status,
        "forecast": result["forecast"],
    }


# ─── 8. Bouton "Pourquoi ?" XAI ──────────────────────────────────────────────

@router.post("/why")
def explain_why(data: WhyRequest, db: Session = Depends(get_db)):
    """Explication XAI en français pour un KPI — bouton 'Pourquoi ?'."""
    from app.services.xai_service import XAIService
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Conversion explicite de l'ID en UUID
        inst_uuid = uuid.UUID(str(data.institution_id))
        inst = db.query(Institution).filter(Institution.id == inst_uuid).first()
        if not inst:
            raise HTTPException(status_code=404, detail="Institution non trouvée")

        service = XAIService(db)
        # On s'assure d'utiliser l'UUID converti
        result = service.explain_kpi(inst_uuid, "academic", data.indicator)

        if "error" in result:
            logger.error(f"Erreur XAI Service: {result['error']}")
            raise HTTPException(status_code=404, detail=result["error"])

        # Recommandation selon le statut
        kpi_val = result["kpi"]["value"]
        status = _get_kpi_status(data.indicator, kpi_val)
        
        recommendation = "✅ Indicateur dans les normes. Continuer le suivi régulier."
        if status == "critical":
            recommendation = "⚡ Action urgente : analyser les causes racines immédiatement et contacter le responsable."
        elif status == "warning":
            recommendation = "💡 Surveillance recommandée : suivre l'évolution sur les 4 prochaines semaines."

        return {
            "institution_name": inst.name,
            "indicator": data.indicator,
            "current_value": kpi_val,
            "explanation": result["explanation"],
            "recommendation": recommendation,
            "generated_at": result["generated_at"],
        }
    except Exception as e:
        logger.exception("Erreur fatale dans /why")
        raise HTTPException(status_code=500, detail=str(e))


# ─── 9. Historique d'un indicateur ────────────────────────────────────────────

@router.get("/history/{institution_id}")
def get_indicator_history(
    institution_id: UUID,
    indicator: str = Query("dropout_rate"),
    months: int = Query(12, ge=1, le=18),
    db: Session = Depends(get_db),
):
    """Historique mensuel d'un indicateur pour une institution."""
    inst = _get_inst_or_404(institution_id, db)
    kpis = db.query(KPIMetric).filter(
        KPIMetric.institution_id == institution_id,
        KPIMetric.domain == "academic",
        KPIMetric.indicator == indicator,
    ).order_by(KPIMetric.reporting_date.asc()).limit(months).all()

    return {
        "institution_name": inst.name,
        "indicator": indicator,
        "history": [
            {"date": k.reporting_date.strftime("%Y-%m"), "value": round(k.value, 1)}
            for k in kpis
        ],
    }


# ─── 10. Comparaison inter-institutions (UCAR) ────────────────────────────────

@router.get("/compare")
def compare_institutions(
    indicator: str = Query("dropout_rate"),
    db: Session = Depends(get_db),
):
    """Comparaison de toutes les institutions pour un indicateur (vue UCAR)."""
    institutions = db.query(Institution).filter(Institution.is_active == True).all()
    result = []

    for inst in institutions:
        kpi = db.query(KPIMetric).filter(
            KPIMetric.institution_id == inst.id,
            KPIMetric.domain == "academic",
            KPIMetric.indicator == indicator,
        ).order_by(KPIMetric.reporting_date.desc()).first()

        if kpi:
            result.append({
                "institution_name": inst.name,
                "institution_code": inst.code,
                "institution_id": str(inst.id),
                "value": round(kpi.value, 1),
                "status": _get_kpi_status(indicator, kpi.value),
                "date": kpi.reporting_date.strftime("%Y-%m"),
            })

    result.sort(key=lambda x: x["value"], reverse=(THRESHOLDS.get(indicator, {}).get("higher_is_better", True)))
    return {"indicator": indicator, "institutions": result}
