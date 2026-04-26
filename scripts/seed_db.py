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
    content_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "image/png",
        "text/csv",
    ]
    parser_names = ["pdf_text", "excel_parser", "image_ocr", "csv_parser"]

    for index in range(count):
        content_type = random.choice(content_types)
        parser_name = parser_names[content_types.index(content_type)]
        extension = {
            "application/pdf": "pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
            "image/png": "png",
            "text/csv": "csv",
        }[content_type]

        document = Document(
            filename=f"demo-document-{index + 1}.{extension}",
            content_type=content_type,
            size=random.randint(25_000, 2_000_000),
            status=random.choice(
                [
                    DocumentStatus.PENDING.value,
                    DocumentStatus.PROCESSED.value,
                    DocumentStatus.FAILED.value,
                ]
            ),
            extracted_text=fake.paragraph(nb_sentences=6),
            extracted_data='{"structured_data": {"preview": "demo"}, "metadata": {"parser": "demo"}}',
            parser_name=parser_name,
            error_message=None,
            file_path=f"storage/documents/demo-document-{index + 1}.{extension}",
        )
        db_session.add(document)

    db_session.commit()
    print(f"[OK] Documents seeded ({count})")


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
        print("[OK] Database tables created\n")
        
        # Seed each domain
        seed_documents(db_session, count=10)
        seed_education(db_session, count=20)
        seed_finance_hr(db_session, count=15)
        seed_environment(db_session)
        seed_chatbot(db_session, count=5)
        
        print("\n" + "="*50)
        print("[OK] DATABASE SEEDING COMPLETED")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"\n[ERROR] Error seeding database: {e}")
        db_session.rollback()
        raise
    finally:
        db_session.close()


if __name__ == "__main__":
    seed_all()
