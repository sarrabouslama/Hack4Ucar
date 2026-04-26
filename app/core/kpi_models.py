"""
KPI Models for UniSmart AI
Centralized KPI tracking across all institutions
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey, Text, Enum as SQLEnum, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class KPI_DOMAIN(str, Enum):
    """KPI Domains as per CDC"""
    ACADEMIC = "academic"
    FINANCE = "finance"
    HR = "hr"
    RESEARCH = "research"
    ESG = "esg"
    INFRASTRUCTURE = "infrastructure"
    PARTNERSHIPS = "partnerships"
    EMPLOYMENT = "employment"


class KPI_PERIOD(str, Enum):
    """Reporting periods"""
    MONTHLY = "monthly"
    SEMESTRIAL = "semestrial"
    ANNUAL = "annual"


class ALERT_SEVERITY(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ALERT_STATUS(str, Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class Institution(Base):
    """Institution/Affiliated University Model"""
    __tablename__ = "institutions"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)  # e.g., "ISET_Nabeul"
    type = Column(String(50), default="institution")  # "institution" or "ucar_central"
    region = Column(String(100))
    address = Column(Text)
    contact_email = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    kpis = relationship("KPIMetric", back_populates="institution")
    alerts = relationship("Alert", back_populates="institution")
    documents = relationship("Document", back_populates="institution")


class KPIMetric(Base):
    """Centralized KPI Metric Model"""
    __tablename__ = "kpi_metrics"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False)
    
    # KPI Definition
    domain = Column(SQLEnum(KPI_DOMAIN), nullable=False)  # academic, finance, hr, etc.
    indicator = Column(String(100), nullable=False)  # e.g., "success_rate", "budget_consumed"
    period = Column(SQLEnum(KPI_PERIOD), nullable=False)  # monthly, semestrial, annual
    
    # Value
    value = Column(Float, nullable=False)
    unit = Column(String(50))  # %, number, currency, etc.
    
    # Metadata
    reporting_date = Column(DateTime, nullable=False)
    data_source = Column(String(100))  # manual, ocr, api
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    institution = relationship("Institution", back_populates="kpis")
    predictions = relationship("KPIPrediction", back_populates="kpi_metric")
    alerts = relationship("Alert", back_populates="kpi_metric")

    def to_dict(self):
        return {
            "id": str(self.id),
            "institution_id": str(self.institution_id),
            "domain": self.domain.value if self.domain else None,
            "indicator": self.indicator,
            "period": self.period.value if self.period else None,
            "value": self.value,
            "unit": self.unit,
            "reporting_date": self.reporting_date.isoformat() if self.reporting_date else None,
            "data_source": self.data_source,
            "notes": self.notes
        }


class KPITarget(Base):
    """KPI Target/Objective Model"""
    __tablename__ = "kpi_targets"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False)
    
    domain = Column(SQLEnum(KPI_DOMAIN), nullable=False)
    indicator = Column(String(100), nullable=False)
    period = Column(SQLEnum(KPI_PERIOD), nullable=False)
    
    target_value = Column(Float, nullable=False)
    ai_generated = Column(String(10), default="false")  # true/false
    
    # SMART objectives
    milestone = Column(Text)  # Description of the objective
    priority = Column(Integer, default=1)  # 1 = high, 5 = low
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KPIPrediction(Base):
    """KPI Predictions from Prophet/ML"""
    __tablename__ = "kpi_predictions"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    kpi_metric_id = Column(UUID(as_uuid=True), ForeignKey("kpi_metrics.id"), nullable=False)
    
    # Prediction details
    prediction_date = Column(DateTime, nullable=False)  # When the prediction is for
    predicted_value = Column(Float, nullable=False)
    confidence_lower = Column(Float)
    confidence_upper = Column(Float)
    
    # Model info
    model_type = Column(String(50), default="prophet")  # prophet, sklearn, etc.
    horizon_days = Column(Integer, nullable=False)  # J+7, J+30, J+90
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    kpi_metric = relationship("KPIMetric", back_populates="predictions")


class Alert(Base):
    """Intelligent Alert Model with XAI"""
    __tablename__ = "alerts"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False)
    kpi_metric_id = Column(UUID(as_uuid=True), ForeignKey("kpi_metrics.id"))
    
    # Alert details
    severity = Column(SQLEnum(ALERT_SEVERITY), nullable=False)
    status = Column(SQLEnum(ALERT_STATUS), default=ALERT_STATUS.ACTIVE)
    
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # XAI - Explainable AI factors
    xai_factors = Column(JSONB)  # { "factor1": 0.45, "factor2": 0.30, ... }
    xai_explanation = Column(Text)  # Natural language explanation
    
    # Threshold info
    threshold_value = Column(Float)
    actual_value = Column(Float)
    
    # Resolution
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime)

    # Relationships
    institution = relationship("Institution", back_populates="alerts")
    kpi_metric = relationship("KPIMetric", back_populates="alerts")


class KPIAggregate(Base):
    """Aggregated KPIs for UCAR Central (cross-institution)"""
    __tablename__ = "kpi_aggregates"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    
    # Aggregate definition
    domain = Column(SQLEnum(KPI_DOMAIN), nullable=False)
    indicator = Column(String(100), nullable=False)
    period = Column(SQLEnum(KPI_PERIOD), nullable=False)
    reporting_date = Column(DateTime, nullable=False)
    
    # Aggregated values
    avg_value = Column(Float)  # Average across institutions
    min_value = Column(Float)
    max_value = Column(Float)
    std_dev = Column(Float)
    total_count = Column(Integer)  # Number of institutions
    
    # JSON breakdown
    breakdown = Column(JSONB)  # { "institution_id": value, ... }
    
    created_at = Column(DateTime, default=datetime.utcnow)


class Ranking(Base):
    """Gamification Ranking"""
    __tablename__ = "rankings"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False)
    
    period = Column(SQLEnum(KPI_PERIOD), nullable=False)
    reporting_date = Column(DateTime, nullable=False)
    
    # Scores
    overall_score = Column(Float, nullable=False)
    academic_score = Column(Float)
    finance_score = Column(Float)
    esg_score = Column(Float)
    
    # Rank
    rank = Column(Integer, nullable=False)
    
    # Badges/Trophies
    badges = Column(JSONB)  # ["top_performer", "most_improved", ...]
    
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    """User/Admin Model"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id"))
    
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), nullable=False)  # super_admin, president, director, admin, staff
    space = Column(String(50), nullable=False)  # ucar_central, institution
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)