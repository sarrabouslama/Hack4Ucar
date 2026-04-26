"""
KPI Services - Business logic for KPI management
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from uuid import UUID
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.modules.kpis.db_models import KPIMetric, KPIAggregate, Institution, Alert, KPIPrediction, Ranking


class KPIService:
    """Service for KPI calculations and management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_kpi(
        self,
        institution_id: UUID,
        domain: str,
        indicator: str,
        period: str,
        value: float,
        unit: str = None,
        reporting_date: datetime = None,
        data_source: str = "manual",
        notes: str = None
    ) -> KPIMetric:
        """Create a new KPI metric"""
        kpi = KPIMetric(
            id=uuid.uuid4(),
            institution_id=institution_id,
            domain=domain,
            indicator=indicator,
            period=period,
            value=value,
            unit=unit,
            reporting_date=reporting_date or datetime.utcnow(),
            data_source=data_source,
            notes=notes
        )
        self.db.add(kpi)
        self.db.commit()
        self.db.refresh(kpi)
        return kpi
    
    def get_institution_kpis(
        self,
        institution_id: UUID,
        domain: str = None,
        period: str = None,
        limit: int = 100
    ) -> List[KPIMetric]:
        """Get KPIs for a specific institution"""
        query = self.db.query(KPIMetric).filter(
            KPIMetric.institution_id == institution_id
        )
        
        if domain:
            query = query.filter(KPIMetric.domain == domain)
        if period:
            query = query.filter(KPIMetric.period == period)
        
        return query.order_by(KPIMetric.reporting_date.desc()).limit(limit).all()
    
    def get_consolidated_kpis(
        self,
        domain: str = None,
        indicator: str = None,
        period: str = "monthly",
        reporting_date: datetime = None
    ) -> List[KPIAggregate]:
        """Get consolidated KPIs across all institutions (UCAR Central view)"""
        query = self.db.query(KPIAggregate)
        
        if domain:
            query = query.filter(KPIAggregate.domain == domain)
        if indicator:
            query = query.filter(KPIAggregate.indicator == indicator)
        if period:
            query = query.filter(KPIAggregate.period == period)
        if reporting_date:
            query = query.filter(
                func.date(KPIAggregate.reporting_date) == reporting_date.date()
            )
        
        return query.order_by(KPIAggregate.domain, KPIAggregate.indicator).all()
    
    def calculate_aggregate(
        self,
        domain: str,
        indicator: str,
        period: str,
        reporting_date: datetime = None
    ) -> KPIAggregate:
        """Calculate aggregate KPIs across all institutions"""
        reporting_date = reporting_date or datetime.utcnow()
        
        # Get all KPIs for this domain/indicator/period
        kpis = self.db.query(KPIMetric).filter(
            and_(
                KPIMetric.domain == domain,
                KPIMetric.indicator == indicator,
                KPIMetric.period == period,
                func.date(KPIMetric.reporting_date) == reporting_date.date()
            )
        ).all()
        
        if not kpis:
            return None
        
        values = [k.value for k in kpis]
        
        # Calculate statistics
        avg_value = sum(values) / len(values)
        min_value = min(values)
        max_value = max(values)
        
        # Standard deviation
        variance = sum((x - avg_value) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        # Breakdown by institution
        breakdown = {str(k.institution_id): k.value for k in kpis}
        
        # Create or update aggregate
        aggregate = self.db.query(KPIAggregate).filter(
            and_(
                KPIAggregate.domain == domain,
                KPIAggregate.indicator == indicator,
                KPIAggregate.period == period,
                func.date(KPIAggregate.reporting_date) == reporting_date.date()
            )
        ).first()
        
        if aggregate:
            aggregate.avg_value = avg_value
            aggregate.min_value = min_value
            aggregate.max_value = max_value
            aggregate.std_dev = std_dev
            aggregate.total_count = len(values)
            aggregate.breakdown = breakdown
        else:
            aggregate = KPIAggregate(
                id=uuid.uuid4(),
                domain=domain,
                indicator=indicator,
                period=period,
                reporting_date=reporting_date,
                avg_value=avg_value,
                min_value=min_value,
                max_value=max_value,
                std_dev=std_dev,
                total_count=len(values),
                breakdown=breakdown
            )
            self.db.add(aggregate)
        
        self.db.commit()
        self.db.refresh(aggregate)
        return aggregate
    
    def get_kpi_trend(
        self,
        institution_id: UUID,
        domain: str,
        indicator: str,
        months: int = 6
    ) -> List[Dict[str, Any]]:
        """Get KPI trend over time for an institution"""
        start_date = datetime.utcnow() - timedelta(days=30 * months)
        
        kpis = self.db.query(KPIMetric).filter(
            and_(
                KPIMetric.institution_id == institution_id,
                KPIMetric.domain == domain,
                KPIMetric.indicator == indicator,
                KPIMetric.reporting_date >= start_date
            )
        ).order_by(KPIMetric.reporting_date.asc()).all()
        
        return [
            {
                "date": k.reporting_date.isoformat(),
                "value": k.value,
                "unit": k.unit
            }
            for k in kpis
        ]
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get summary for UCAR Central dashboard"""
        # Total institutions
        total_institutions = self.db.query(Institution).filter(
            Institution.is_active == "true"
        ).count()
        
        # KPIs by domain
        domains = {}
        result = self.db.query(KPIMetric.domain, func.count(KPIMetric.id)).group_by(KPIMetric.domain).all()
        for domain, count in result:
            domains[domain] = count
        
        # Latest aggregates
        latest_aggregates = self.db.query(KPIAggregate).order_by(
            KPIAggregate.reporting_date.desc()
        ).limit(10).all()
        
        return {
            "total_institutions": total_institutions,
            "kpis_by_domain": domains,
            "latest_aggregates": [
                {
                    "domain": a.domain,
                    "indicator": a.indicator,
                    "avg_value": a.avg_value,
                    "period": a.period,
                    "reporting_date": a.reporting_date.isoformat()
                }
                for a in latest_aggregates
            ]
        }


class AlertService:
    """Service for intelligent alerts"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _get_threshold_config(self, domain: str, indicator: str) -> Dict[str, float]:
        """Get threshold configuration for a KPI"""
        default_thresholds = {
            ("academic", "success_rate"): {"warning": 60, "critical": 50},
            ("academic", "dropout_rate"): {"warning": 15, "critical": 20},
            ("finance", "budget_consumed"): {"warning": 90, "critical": 100},
            ("hr", "absenteeism_rate"): {"warning": 10, "critical": 15},
            ("esg", "co2_per_student"): {"warning": 200, "critical": 350},
        }
        key = (domain, indicator)
        return default_thresholds.get(key, {"warning": 20, "critical": 30})
    
    def check_and_create_alerts(
        self,
        institution_id: UUID,
        domain: str,
        indicator: str
    ) -> List[Alert]:
        """Check thresholds and create alerts if needed"""
        # Get latest KPI
        kpi = self.db.query(KPIMetric).filter(
            and_(
                KPIMetric.institution_id == institution_id,
                KPIMetric.domain == domain,
                KPIMetric.indicator == indicator
            )
        ).order_by(KPIMetric.reporting_date.desc()).first()
        
        if not kpi:
            return []
        
        thresholds = self._get_threshold_config(domain, indicator)
        alerts_created = []
        
        # Check warning threshold
        for level in ["warning", "critical"]:
            if level not in thresholds:
                continue
            
            is_violation = False
            if indicator in ["dropout_rate", "absenteeism_rate", "co2_per_student"]:
                is_violation = kpi.value > thresholds[level]
            else:
                is_violation = kpi.value < thresholds[level]
            
            if is_violation:
                # Check if alert already exists
                existing = self.db.query(Alert).filter(
                    and_(
                        Alert.institution_id == institution_id,
                        Alert.kpi_metric_id == kpi.id,
                        Alert.status == "active",
                        Alert.severity == level
                    )
                ).first()
                
                if not existing:
                    alert = Alert(
                        id=uuid.uuid4(),
                        institution_id=institution_id,
                        kpi_metric_id=kpi.id,
                        severity=level,
                        status="active",
                        title=f"Alert: {indicator}",
                        message=f"{indicator} is at {kpi.value}, threshold: {thresholds[level]}",
                        xai_factors={"threshold_violation": 1.0},
                        xai_explanation=f"Value {kpi.value} triggers {level} threshold ({thresholds[level]})",
                        threshold_value=thresholds[level],
                        actual_value=kpi.value
                    )
                    self.db.add(alert)
                    alerts_created.append(alert)
        
        if alerts_created:
            self.db.commit()
        
        return alerts_created
    
    def get_active_alerts(
        self,
        institution_id: UUID = None,
        severity: str = None,
        limit: int = 50
    ) -> List[Alert]:
        """Get active alerts"""
        query = self.db.query(Alert).filter(Alert.status == "active")
        
        if institution_id:
            query = query.filter(Alert.institution_id == institution_id)
        
        if severity:
            query = query.filter(Alert.severity == severity)
        
        return query.order_by(Alert.created_at.desc()).limit(limit).all()
    
    def acknowledge_alert(self, alert_id: UUID) -> Optional[Alert]:
        """Acknowledge an alert"""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.status = "acknowledged"
            alert.acknowledged_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(alert)
        return alert
    
    def resolve_alert(self, alert_id: UUID, resolution_notes: str = None) -> Optional[Alert]:
        """Resolve an alert"""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.status = "resolved"
            alert.resolved_at = datetime.utcnow()
            alert.resolution_notes = resolution_notes
            self.db.commit()
            self.db.refresh(alert)
        return alert


class RankingService:
    """Service for gamification rankings"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_rankings(
        self,
        period: str = "monthly",
        reporting_date: datetime = None
    ) -> List[Ranking]:
        """Calculate rankings for all institutions"""
        reporting_date = reporting_date or datetime.utcnow()
        
        # Get all institutions
        institutions = self.db.query(Institution).filter(
            Institution.is_active == "true"
        ).all()
        
        rankings = []
        
        for institution in institutions:
            # Calculate overall score from KPIs
            kpis = self.db.query(KPIMetric).filter(
                and_(
                    KPIMetric.institution_id == institution.id,
                    KPIMetric.period == period
                )
            ).all()
            
            if not kpis:
                continue
            
            # Group by domain and calculate average
            domain_scores = {}
            for kpi in kpis:
                if kpi.domain not in domain_scores:
                    domain_scores[kpi.domain] = []
                domain_scores[kpi.domain].append(kpi.value)
            
            # Calculate domain averages
            academic = sum(domain_scores.get("academic", [0])) / max(len(domain_scores.get("academic", [1])), 1)
            finance = sum(domain_scores.get("finance", [0])) / max(len(domain_scores.get("finance", [1])), 1)
            esg = sum(domain_scores.get("esg", [0])) / max(len(domain_scores.get("esg", [1])), 1)
            
            # Overall score (weighted)
            overall = (academic * 0.4 + finance * 0.3 + esg * 0.3)
            
            # Check if ranking exists
            existing = self.db.query(Ranking).filter(
                and_(
                    Ranking.institution_id == institution.id,
                    Ranking.period == period,
                    func.date(Ranking.reporting_date) == reporting_date.date()
                )
            ).first()
            
            if existing:
                existing.overall_score = overall
                existing.academic_score = academic
                existing.finance_score = finance
                existing.esg_score = esg
                rankings.append(existing)
            else:
                ranking = Ranking(
                    id=uuid.uuid4(),
                    institution_id=institution.id,
                    period=period,
                    reporting_date=reporting_date,
                    overall_score=overall,
                    academic_score=academic,
                    finance_score=finance,
                    esg_score=esg,
                    rank=0,  # Will be updated after all rankings are calculated
                    badges=[]
                )
                self.db.add(ranking)
                rankings.append(ranking)
        
        self.db.commit()
        
        # Update ranks
        rankings_sorted = sorted(rankings, key=lambda x: x.overall_score, reverse=True)
        for idx, r in enumerate(rankings_sorted, 1):
            r.rank = idx
            
            # Assign badges
            badges = []
            if idx == 1:
                badges.append("top_performer")
            if r.overall_score > 80:
                badges.append("excellence")
            if r.esg_score > 75:
                badges.append("green_champion")
            r.badges = badges
        
        self.db.commit()
        
        return rankings_sorted
    
    def get_rankings(
        self,
        period: str = "monthly",
        anonymized: bool = False
    ) -> List[Dict[str, Any]]:
        """Get rankings, optionally anonymized for institutions"""
        rankings = self.db.query(Ranking).filter(
            Ranking.period == period
        ).order_by(Ranking.rank.asc()).all()
        
        result = []
        for r in rankings:
            institution = self.db.query(Institution).filter(
                Institution.id == r.institution_id
            ).first()
            
            if anonymized:
                # Hide actual institution names
                result.append({
                    "rank": r.rank,
                    "anon_code": f"Institution_{r.rank}",
                    "overall_score": r.overall_score,
                    "academic_score": r.academic_score,
                    "finance_score": r.finance_score,
                    "esg_score": r.esg_score,
                    "badges": r.badges
                })
            else:
                result.append({
                    "rank": r.rank,
                    "institution_name": institution.name if institution else "Unknown",
                    "institution_code": institution.code if institution else "N/A",
                    "overall_score": r.overall_score,
                    "academic_score": r.academic_score,
                    "finance_score": r.finance_score,
                    "esg_score": r.esg_score,
                    "badges": r.badges
                })
        
        return result