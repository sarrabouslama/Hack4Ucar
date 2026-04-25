"""
Database seeding with fake data
"""

import random
from datetime import datetime, timedelta
from typing import List

from faker import Faker
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, db
from app.modules.documents_ingestion.db_models import Document, DocumentStatus
from app.modules.education_research.db_models import Student, Course, Enrollment, Exam, ResearchIndicator
from app.modules.finance_partnerships_hr.db_models import (
    Budget, Partnership, FinancialReport, Ranking, Employee, Contract, Absenteeism, EmploymentOutcome
)
from app.modules.environment_infrastructure.db_models import (
    ESGMetric, CarbonFootprint, EnergyConsumption, RecyclingStatistic, InventoryItem, Equipment, FacilityHealth
)
from app.modules.chatbot_automation.db_models import (
    ChatSession, ChatMessage, AutomationAction, Workflow, WorkflowExecution, Orchestration
)

fake = Faker()


def seed_documents(db_session: Session, count: int = 10) -> None:
    """Seed documents"""


def seed_education(db_session: Session, count: int = 20) -> None:
    """Seed education data"""

def seed_finance_hr(db_session: Session, count: int = 15) -> None:
    """Seed finance and HR data"""
    
def seed_environment(db_session: Session) -> None:
    """Seed environment data"""

def seed_chatbot(db_session: Session, count: int = 5) -> None:
    """Seed chatbot and automation data"""

def seed_all() -> None:
    """Seed all tables with fake data"""
    print("\n" + "="*50)
    print("HACK4UCAR DATABASE SEEDING")
    print("="*50 + "\n")
    
    db_session = SessionLocal()
    
    try:
        # Create all tables
        db.create_tables()
        print("✓ Database tables created\n")
        
        # Seed each domain
        seed_documents(db_session, count=10)
        seed_education(db_session, count=20)
        seed_finance_hr(db_session, count=15)
        seed_environment(db_session)
        seed_chatbot(db_session, count=5)
        
        print("\n" + "="*50)
        print("✓ DATABASE SEEDING COMPLETED")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error seeding database: {e}")
        db_session.rollback()
        raise
    finally:
        db_session.close()


if __name__ == "__main__":
    seed_all()
