"""
Comprehensive database re-initialization and seeding script.
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine, Base, db
from app.modules.documents_ingestion.db_models import Document, DocumentStatus
import uuid

def reinit_and_seed():
    print("Starting database re-initialization...")
    
    with engine.connect() as conn:
        print("Dropping existing tables...")
        # Order matters for foreign keys
        tables = [
            "mail_logs", "chat_messages", "chat_sessions", 
            "automation_actions", "workflows", "workflow_executions", "orchestrations",
            "enrollments", "exams", "students", "courses", "research_indicators",
            "budgets", "partnerships", "financial_reports", "rankings",
            "employees", "contracts", "absenteeism", "employment_outcomes",
            "esg_metrics", "carbon_footprint", "energy_consumption", "recycling_statistics",
            "inventory_items", "equipment", "facility_health", "documents"
        ]
        for table in tables:
            conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        conn.commit()
    
    print("Recreating tables with latest schema...")
    db.create_tables()
    
    print("Seeding searchable documents...")
    from app.core.database import SessionLocal
    db_session = SessionLocal()
    
    test_docs = [
        {
            "filename": "Rapport_Abandon_FST_2024.pdf",
            "content_type": "application/pdf",
            "text": "Ce rapport analyse le taux d'abandon à la Faculté des Sciences de Tunis (FST). On observe une hausse de 15% en première année de licence. Les causes principales incluent des difficultés d'adaptation et des problèmes financiers. Des mesures de tutorat sont recommandées.",
            "institution": "FST"
        },
        {
            "filename": "Budget_UCAR_Central_2025.xlsx",
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text": "Plan budgétaire pour l'Université de Carthage. Allocation de 5 millions de dinars pour la recherche et l'innovation. Augmentation des fonds pour la durabilité environnementale et la rénovation des infrastructures solaires.",
            "institution": "UCAR Central"
        },
        {
            "filename": "Strategie_Accreditation_IHEC.docx",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text": "L'IHEC Carthage lance son plan stratégique pour l'accréditation EQUIS. Ce document détaille les standards de qualité académique, l'internationalisation des programmes et les partenariats avec le secteur privé.",
            "institution": "IHEC"
        },
        {
            "filename": "Etude_Impact_Environnemental_ENIT.pdf",
            "content_type": "application/pdf",
            "text": "Étude sur l'empreinte carbone de l'ENIT. Proposition d'installation de panneaux photovoltaïques sur les toits des bâtiments de génie civil. Réduction prévue de 20% de la consommation énergétique d'ici 2026.",
            "institution": "ENIT"
        },
        {
            "filename": "Projet_Recherche_Intelligence_Artificielle.pdf",
            "content_type": "application/pdf",
            "text": "Collaboration entre l'EPT et l'ENIT sur un projet de recherche en Intelligence Artificielle appliquée à la santé. Utilisation de modèles de deep learning pour le diagnostic précoce des maladies chroniques.",
            "institution": "EPT/ENIT"
        }
    ]
    
    for doc_data in test_docs:
        doc = Document(
            id=uuid.uuid4(),
            filename=doc_data["filename"],
            content_type=doc_data["content_type"],
            size=len(doc_data["text"]) * 10,
            status=DocumentStatus.PROCESSED.value,
            extracted_text=doc_data["text"],
            extracted_data='{"institution": "' + doc_data["institution"] + '", "type": "manual_seed"}',
            parser_name="manual_injection",
            file_path=f"storage/documents/{doc_data['filename']}"
        )
        db_session.add(doc)
    
    try:
        db_session.commit()
        print("[OK] Database re-initialized and seeded successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to seed: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    reinit_and_seed()
