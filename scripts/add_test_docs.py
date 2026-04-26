"""
Script to add specific searchable documents to the database for verification.
"""
import uuid
from datetime import datetime
from app.core.database import SessionLocal
from app.modules.documents_ingestion.db_models import Document, DocumentStatus

def add_test_documents():
    db = SessionLocal()
    
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
    
    print(f"Adding {len(test_docs)} searchable documents...")
    
    for doc_data in test_docs:
        # Check if already exists
        existing = db.query(Document).filter(Document.filename == doc_data["filename"]).first()
        if existing:
            print(f" Skipping {doc_data['filename']} (already exists)")
            continue
            
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
        db.add(doc)
        print(f" Added {doc_data['filename']}")
        
    try:
        db.commit()
        print("\n[OK] Test documents added successfully.")
    except Exception as e:
        print(f"\n[ERROR] Failed to add documents: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_test_documents()
