"""
Database models for KPIs module
"""

from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey, Text, Enum as SQLEnum, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class KPIMetric(Base):
    """Centralized KPI Metric Model"""
    __tablename__ = "kpi_metrics"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False)
    
    # KPI Definition
    domain = Column(String(50), nullable=False)
    indicator = Column(String(100), nullable=False)
    period = Column(String(20), nullable=False)
    
    # Value
    value = Column(Float, nullable=False)
    unit = Column(String(50))
    
    # Metadata
    reporting_date = Column(DateTime, nullable=False)
    data_source = Column(String(100), default="manual")
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.utcnow())
    updated_at = Column(DateTime, default=lambda: __import__('datetime').datetime.utcnow(), 
                        onupdate=lambda: __import__('datetime').datetime.utcnow())

    # Relationships
    institution = relationship("Institution", back_populates="kpis")
    predictions = relationship("KPIPrediction", back_populates="kpi_metric")
    alerts = relationship("Alert", back_populates="kpi_metric")


class Institution(Base):
    """Institution/Affiliated University Model"""
    __tablename__ = "institutions"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    type = Column(String(50), default="institution")
    region = Column(String(100))
    address = Column(Text)
    contact_email = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.utcnow())
    updated_at = Column(DateTime, default=lambda: __import__('datetime').datetime.utcnow(),
                        onupdate=lambda: __import__('datetime').datetime.utcnow())

    # Relationships
    kpis = relationship("KPIMetric", back_populates="institution")
    alerts = relationship("Alert", back_populates="institution")


class KPIPrediction(Base):
    """KPI Predictions from Prophet/ML"""
    __tablename__ = "kpi_predictions"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    kpi_metric_id = Column(UUID(as_uuid=True), ForeignKey("kpi_metrics.id"), nullable=False)
    
    prediction_date = Column(DateTime, nullable=False)
    predicted_value = Column(Float, nullable=False)
    confidence_lower = Column(Float)
    confidence_upper = Column(Float)
    model_type = Column(String(50), default="prophet")
    horizon_days = Column(Integer, nullable=False)
    
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.utcnow())

    kpi_metric = relationship("KPIMetric", back_populates="predictions")


class Alert(Base):
    """Intelligent Alert Model with XAI"""
    __tablename__ = "alerts"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False)
    kpi_metric_id = Column(UUID(as_uuid=True), ForeignKey("kpi_metrics.id"))
    
    severity = Column(String(20), nullable=False)
    status = Column(String(20), default="active")
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    xai_factors = Column(JSONB)
    xai_explanation = Column(Text)
    threshold_value = Column(Float)
    actual_value = Column(Float)
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.utcnow())
    acknowledged_at = Column(DateTime)

    institution = relationship("Institution", back_populates="alerts")
    kpi_metric = relationship("KPIMetric", back_populates="alerts")


class KPIAggregate(Base):
    """Aggregated KPIs for UCAR Central"""
    __tablename__ = "kpi_aggregates"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    domain = Column(String(50), nullable=False)
    indicator = Column(String(100), nullable=False)
    period = Column(String(20), nullable=False)
    reporting_date = Column(DateTime, nullable=False)
    avg_value = Column(Float)
    min_value = Column(Float)
    max_value = Column(Float)
    std_dev = Column(Float)
    total_count = Column(Integer)
    breakdown = Column(JSONB)
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.utcnow())


class Ranking(Base):
    """Gamification Ranking"""
    __tablename__ = "rankings"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True)
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False)
    period = Column(String(20), nullable=False)
    reporting_date = Column(DateTime, nullable=False)
    overall_score = Column(Float, nullable=False)
    academic_score = Column(Float)
    finance_score = Column(Float)
    esg_score = Column(Float)
    rank = Column(Integer, nullable=False)
    badges = Column(JSONB)
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.utcnow())