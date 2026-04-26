"""
Anomaly Detection Service - ML-based anomaly detection
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from uuid import UUID

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.core.kpi_models import (
    KPIMetric, Alert, Institution,
    KPI_DOMAIN, KPI_PERIOD, ALERT_SEVERITY, ALERT_STATUS
)


class AnomalyDetectionService:
    """Service for detecting anomalies in KPIs using ML"""
    
    def __init__(self, db: Session):
        self.db = db
        self.scaler = StandardScaler()
    
    def _calculate_z_score(self, value: float, mean: float, std: float) -> float:
        """Calculate Z-score for a value"""
        if std == 0:
            return 0
        return (value - mean) / std
    
    def _get_threshold_config(
        self, 
        domain: str, 
        indicator: str
    ) -> Dict[str, float]:
        """Get threshold configuration for a KPI"""
        # Default thresholds (can be moved to config)
        default_thresholds = {
            # Academic
            ("academic", "success_rate"): {"warning": 60, "critical": 50},
            ("academic", "dropout_rate"): {"warning": 15, "critical": 20},
            ("academic", "attendance_rate"): {"warning": 75, "critical": 65},
            # Finance
            ("finance", "budget_consumed"): {"warning": 90, "critical": 100},
            ("finance", "revenue_growth"): {"warning": -5, "critical": -10},
            # HR
            ("hr", "absenteeism_rate"): {"warning": 10, "critical": 15},
            ("hr", "retention_rate"): {"warning": 80, "critical": 70},
            # ESG
            ("esg", "co2_per_student"): {"warning": 200, "critical": 350},
            ("esg", "energy_efficiency"): {"warning": -10, "critical": -20},
        }
        
        key = (domain, indicator)
        return default_thresholds.get(key, {"warning": 20, "critical": 30})
    
    def detect_z_score_anomalies(
        self,
        institution_id: UUID,
        domain: str,
        indicator: str,
        threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Detect anomalies using Z-score method"""
        # Get historical data
        kpis = self.db.query(KPIMetric).filter(
            and_(
                KPIMetric.institution_id == institution_id,
                KPIMetric.domain == KPI_DOMAIN(domain),
                KPIMetric.indicator == indicator
            )
        ).order_by(KPIMetric.reporting_date.asc()).all()
        
        if len(kpis) < 5:
            return []
        
        values = np.array([k.value for k in kpis])
        mean = np.mean(values)
        std = np.std(values)
        
        anomalies = []
        for kpi in kpis[-10:]:  # Check last 10 values
            z_score = self._calculate_z_score(kpi.value, mean, std)
            
            if abs(z_score) > threshold:
                anomalies.append({
                    "kpi_id": str(kpi.id),
                    "date": kpi.reporting_date.isoformat(),
                    "value": kpi.value,
                    "z_score": round(z_score, 2),
                    "mean": round(mean, 2),
                    "std": round(std, 2)
                })
        
        return anomalies
    
    def detect_isolation_forest(
        self,
        institution_id: UUID,
        domain: str,
        indicator: str
    ) -> List[Dict[str, Any]]:
        """Detect anomalies using Isolation Forest"""
        # Get historical data
        kpis = self.db.query(KPIMetric).filter(
            and_(
                KPIMetric.institution_id == institution_id,
                KPIMetric.domain == KPI_DOMAIN(domain),
                KPIMetric.indicator == indicator
            )
        ).order_by(KPIMetric.reporting_date.asc()).all()
        
        if len(kpis) < 10:
            return []
        
        # Prepare data
        values = np.array([[k.value] for k in kpis])
        
        # Fit Isolation Forest
        model = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=100
        )
        model.fit(values)
        
        # Predict anomalies
        predictions = model.predict(values)
        scores = model.decision_function(values)
        
        anomalies = []
        for kpi, pred, score in zip(kpis, predictions, scores):
            if pred == -1:  # Anomaly
                anomalies.append({
                    "kpi_id": str(kpi.id),
                    "date": kpi.reporting_date.isoformat(),
                    "value": kpi.value,
                    "anomaly_score": round(score, 4),
                    "is_anomaly": True
                })
        
        return anomalies
    
    def check_threshold_violations(
        self,
        institution_id: UUID,
        domain: str,
        indicator: str
    ) -> List[Dict[str, Any]]:
        """Check if KPI violates configured thresholds"""
        # Get latest KPI
        kpi = self.db.query(KPIMetric).filter(
            and_(
                KPIMetric.institution_id == institution_id,
                KPIMetric.domain == KPI_DOMAIN(domain),
                KPIMetric.indicator == indicator
            )
        ).order_by(KPIMetric.reporting_date.desc()).first()
        
        if not kpi:
            return []
        
        thresholds = self._get_threshold_config(domain, indicator)
        
        violations = []
        
        # Check warning threshold
        if "warning" in thresholds:
            # For rates where lower is worse
            if indicator in ["dropout_rate", "absenteeism_rate", "co2_per_student"]:
                if kpi.value > thresholds["warning"]:
                    violations.append({
                        "level": "warning",
                        "threshold": thresholds["warning"],
                        "actual_value": kpi.value,
                        "message": f"{indicator} is above warning threshold"
                    })
            else:
                if kpi.value < thresholds["warning"]:
                    violations.append({
                        "level": "warning",
                        "threshold": thresholds["warning"],
                        "actual_value": kpi.value,
                        "message": f"{indicator} is below warning threshold"
                    })
        
        # Check critical threshold
        if "critical" in thresholds:
            if indicator in ["dropout_rate", "absenteeism_rate", "co2_per_student"]:
                if kpi.value > thresholds["critical"]:
                    violations.append({
                        "level": "critical",
                        "threshold": thresholds["critical"],
                        "actual_value": kpi.value,
                        "message": f"{indicator} exceeds critical threshold!"
                    })
            else:
                if kpi.value < thresholds["critical"]:
                    violations.append({
                        "level": "critical",
                        "threshold": thresholds["critical"],
                        "actual_value": kpi.value,
                        "message": f"{indicator} below critical threshold!"
                    })
        
        return violations
    
    def create_alert_from_anomaly(
        self,
        institution_id: UUID,
        kpi_metric_id: UUID,
        severity: str,
        title: str,
        message: str,
        xai_factors: Dict[str, float] = None,
        xai_explanation: str = None,
        threshold_value: float = None,
        actual_value: float = None
    ) -> Alert:
        """Create an alert from detected anomaly"""
        alert = Alert(
            institution_id=institution_id,
            kpi_metric_id=kpi_metric_id,
            severity=ALERT_SEVERITY(severity),
            status=ALERT_STATUS.ACTIVE,
            title=title,
            message=message,
            xai_factors=xai_factors,
            xai_explanation=xai_explanation,
            threshold_value=threshold_value,
            actual_value=actual_value
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def analyze_and_alert(
        self,
        institution_id: UUID,
        domain: str,
        indicator: str
    ) -> Dict[str, Any]:
        """Run full anomaly detection and create alerts if needed"""
        results = {
            "institution_id": str(institution_id),
            "domain": domain,
            "indicator": indicator,
            "alerts_created": []
        }
        
        # 1. Check threshold violations
        violations = self.check_threshold_violations(
            institution_id, domain, indicator
        )
        
        for violation in violations:
            # Get latest KPI
            kpi = self.db.query(KPIMetric).filter(
                and_(
                    KPIMetric.institution_id == institution_id,
                    KPIMetric.domain == KPI_DOMAIN(domain),
                    KPIMetric.indicator == indicator
                )
            ).order_by(KPIMetric.reporting_date.desc()).first()
            
            if kpi:
                # Check if alert already exists
                existing = self.db.query(Alert).filter(
                    and_(
                        Alert.institution_id == institution_id,
                        Alert.kpi_metric_id == kpi.id,
                        Alert.status == ALERT_STATUS.ACTIVE
                    )
                ).first()
                
                if not existing:
                    alert = self.create_alert_from_anomaly(
                        institution_id=institution_id,
                        kpi_metric_id=kpi.id,
                        severity=violation["level"],
                        title=f"Alert: {indicator}",
                        message=violation["message"],
                        xai_factors={"threshold_violation": 1.0},
                        xai_explanation=f"Value {kpi.value} {violation['message']}. Threshold: {violation['threshold']}",
                        threshold_value=violation["threshold"],
                        actual_value=kpi.value
                    )
                    results["alerts_created"].append({
                        "alert_id": str(alert.id),
                        "severity": alert.severity.value,
                        "title": alert.title
                    })
        
        # 2. Run Z-score detection
        z_score_anomalies = self.detect_z_score_anomalies(
            institution_id, domain, indicator
        )
        results["z_score_anomalies"] = z_score_anomalies
        
        # 3. Run Isolation Forest detection
        if_anomalies = self.detect_isolation_forest(
            institution_id, domain, indicator
        )
        results["isolation_forest_anomalies"] = if_anomalies
        
        return results
    
    def get_active_alerts(
        self,
        institution_id: UUID = None,
        severity: str = None,
        limit: int = 50
    ) -> List[Alert]:
        """Get active alerts"""
        query = self.db.query(Alert).filter(
            Alert.status == ALERT_STATUS.ACTIVE
        )
        
        if institution_id:
            query = query.filter(Alert.institution_id == institution_id)
        
        if severity:
            query = query.filter(Alert.severity == ALERT_SEVERITY(severity))
        
        return query.order_by(Alert.created_at.desc()).limit(limit).all()
    
    def acknowledge_alert(self, alert_id: UUID) -> Alert:
        """Acknowledge an alert"""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.status = ALERT_STATUS.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(alert)
        return alert
    
    def resolve_alert(
        self, 
        alert_id: UUID, 
        resolution_notes: str = None
    ) -> Alert:
        """Resolve an alert"""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.status = ALERT_STATUS.RESOLVED
            alert.resolved_at = datetime.utcnow()
            alert.resolution_notes = resolution_notes
            self.db.commit()
            self.db.refresh(alert)
        return alert