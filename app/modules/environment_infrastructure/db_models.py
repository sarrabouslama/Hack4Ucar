"""
Database models for environment and infrastructure
"""

from sqlalchemy import Column, String, Float, DateTime, Integer, Text
from datetime import datetime

from app.core.models import BaseModel


class ESGMetric(BaseModel):
    """ESG metrics model"""

    __tablename__ = "esg_metrics"

    metric_name = Column(String(255), nullable=False)
    metric_value = Column(Float, nullable=False)
    unit = Column(String(100), nullable=True)
    measurement_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    category = Column(String(100), nullable=False)  # environmental, social, governance


class CarbonFootprint(BaseModel):
    """Carbon footprint model"""

    __tablename__ = "carbon_footprint"

    reporting_period = Column(String(50), nullable=False)
    co2_emissions = Column(Float, nullable=False)  # in tons
    reduction_target = Column(Float, nullable=True)
    scope = Column(String(50), nullable=False)  # scope1, scope2, scope3
    measurement_date = Column(DateTime, default=datetime.utcnow, nullable=False)


class EnergyConsumption(BaseModel):
    """Energy consumption model"""

    __tablename__ = "energy_consumption"

    facility_id = Column(String(100), nullable=False)
    consumption_kwh = Column(Float, nullable=False)
    energy_type = Column(String(50), nullable=False)  # electricity, gas, etc.
    reporting_month = Column(String(50), nullable=False)
    cost = Column(Float, nullable=True)
    measurement_date = Column(DateTime, default=datetime.utcnow, nullable=False)


class RecyclingStatistic(BaseModel):
    """Recycling statistics model"""

    __tablename__ = "recycling_statistics"

    reporting_month = Column(String(50), nullable=False)
    material_type = Column(String(100), nullable=False)
    quantity_kg = Column(Float, nullable=False)
    recycled_amount = Column(Float, nullable=False)
    recycling_rate = Column(Float, nullable=False)


class InventoryItem(BaseModel):
    """Inventory item model"""

    __tablename__ = "inventory_items"

    item_code = Column(String(100), unique=True, nullable=False)
    item_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    location = Column(String(200), nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Equipment(BaseModel):
    """Equipment model"""

    __tablename__ = "equipment"

    equipment_code = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    facility_location = Column(String(200), nullable=False)
    status = Column(String(50), default="operational", nullable=False)
    last_maintenance = Column(DateTime, nullable=True)
    next_maintenance = Column(DateTime, nullable=True)


class FacilityHealth(BaseModel):
    """Facility health model"""

    __tablename__ = "facility_health"

    facility_name = Column(String(255), nullable=False)
    health_score = Column(Float, nullable=False)  # 0-100
    condition = Column(String(50), nullable=False)  # excellent, good, fair, poor
    last_inspection = Column(DateTime, nullable=True)
    next_inspection = Column(DateTime, nullable=True)
    maintenance_needs = Column(Text, nullable=True)
