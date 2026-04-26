"""
Initialize database tables for all modules.
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.core.database import engine, Base

# Import all models to ensure they are registered with Base.metadata
from app.modules.documents_ingestion.db_models import Document
from app.modules.kpis.db_models import KPIMetric, Institution, KPIAggregate, Alert, Ranking
from app.modules.finance_partnerships_hr.db_models import Budget, Partnership, FinancialReport, Employee, Contract
# Environment module models if any
try:
    from app.modules.environment_infrastructure.db_models import ESGMetric
except ImportError:
    pass

def init_db():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Done!")

if __name__ == "__main__":
    init_db()
