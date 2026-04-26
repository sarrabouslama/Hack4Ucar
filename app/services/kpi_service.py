"""
KPI Service - Centralized KPI calculations and aggregations
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.kpi_models import (
    KPIMetric, KPIAggregate, Institution, 
    KPI_DOMAIN, KPI_PERIOD
)


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
            institution_id=institution_id,
            domain=KPI_DOMAIN(domain),
            indicator=indicator,
            period=KPI_PERIOD(period),
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
            query = query.filter(KPIMetric.domain == KPI_DOMAIN(domain))
        if period:
            query = query.filter(KPIMetric.period == KPI_PERIOD(period))
        
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
            query = query.filter(KPIAggregate.domain == KPI_DOMAIN(domain))
        if indicator:
            query = query.filter(KPIAggregate.indicator == indicator)
        if period:
            query = query.filter(KPIAggregate.period == KPI_PERIOD(period))
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
                KPIMetric.domain == KPI_DOMAIN(domain),
                KPIMetric.indicator == indicator,
                KPIMetric.period == KPI_PERIOD(period),
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
                KPIAggregate.domain == KPI_DOMAIN(domain),
                KPIAggregate.indicator == indicator,
                KPIAggregate.period == KPI_PERIOD(period),
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
                domain=KPI_DOMAIN(domain),
                indicator=indicator,
                period=KPI_PERIOD(period),
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
                KPIMetric.domain == KPI_DOMAIN(domain),
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
        for domain in KPI_DOMAIN:
            count = self.db.query(KPIMetric).filter(
                KPIMetric.domain == domain
            ).count()
            domains[domain.value] = count
        
        # Latest aggregates
        latest_aggregates = self.db.query(KPIAggregate).order_by(
            KPIAggregate.reporting_date.desc()
        ).limit(10).all()
        
        return {
            "total_institutions": total_institutions,
            "kpis_by_domain": domains,
            "latest_aggregates": [
                {
                    "domain": a.domain.value,
                    "indicator": a.indicator,
                    "avg_value": a.avg_value,
                    "period": a.period.value,
                    "reporting_date": a.reporting_date.isoformat()
                }
                for a in latest_aggregates
            ]
        }