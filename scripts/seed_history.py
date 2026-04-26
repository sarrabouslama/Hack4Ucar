import uuid
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys
import os

DATABASE_URL = "postgresql://postgres:eyazayeni1742@localhost:5432/unismart"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_history():
    with engine.connect() as conn:
        institutions = [
            {"code": "FST_TUN", "trend": "positive"},
            {"code": "ISET_SFX", "trend": "negative"}
        ]
        
        for inst_info in institutions:
            result = conn.execute(text(f"SELECT id, name FROM institutions WHERE code = '{inst_info['code']}'")).fetchone()
            if not result:
                print(f"Erreur: {inst_info['code']} non trouvée.")
                continue
            
            fst_id = result[0]
            fst_name = result[1]
            print(f"Génération d'historique pour {fst_name} (Tendance: {inst_info['trend']})...")

            # Supprimer les alertes et KPIs liés
            conn.execute(text(f"DELETE FROM alerts WHERE institution_id = '{fst_id}'"))
            conn.execute(text(f"DELETE FROM kpi_metrics WHERE institution_id = '{fst_id}'"))

            now = datetime.utcnow()
            indicators = ["success_rate", "dropout_rate", "attendance_rate", "exam_pass_rate", "grade_repetition_rate"]
            
            # Générer 12 mois de données
            for month_back in range(12, -1, -1):
                date = now - timedelta(days=30 * month_back)
                date_str = date.strftime('%Y-%m-%d %H:%M:%S')
                
                for ind in indicators:
                    if inst_info['trend'] == "positive":
                        if ind == "success_rate": val = 65 + (12 - month_back) * 1.5 + random.uniform(-3, 3)
                        elif ind == "dropout_rate": val = 20 - (12 - month_back) * 0.8 + random.uniform(-2, 2)
                        else: val = random.uniform(70, 85)
                    else: # negative trend for ENIT
                        if ind == "success_rate": val = 85 - (12 - month_back) * 2.0 + random.uniform(-4, 4)
                        elif ind == "dropout_rate": val = 5 + (12 - month_back) * 1.2 + random.uniform(-1, 3)
                        else: val = random.uniform(50, 75)
                    
                    val = round(min(100, max(0, val)), 2)
                    kpi_id = str(uuid.uuid4())
                    
                    query = text("""
                        INSERT INTO kpi_metrics (id, institution_id, domain, indicator, period, value, unit, reporting_date, data_source, created_at, updated_at)
                        VALUES (:id, :inst_id, 'academic', :ind, 'monthly', :val, '%', :date, 'manual', NOW(), NOW())
                    """)
                    conn.execute(query, {"id": kpi_id, "inst_id": fst_id, "ind": ind, "val": val, "date": date_str})
        
        conn.commit()
        print("✅ Historique généré pour FST et ENIT !")

if __name__ == "__main__":
    seed_history()
