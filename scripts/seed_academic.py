"""
Seed Script — Academic KPIs pour UniSmart AI
Crée 30 institutions tunisiennes + 18 mois de KPIs académiques réalistes.
Inclut des anomalies volontaires pour la démo.

Usage: python scripts/seed_academic.py
"""

import sys
import os
import uuid
import random
from datetime import datetime, timedelta

# Ajouter la racine du projet au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import SessionLocal, engine, Base
from app.modules.kpis.db_models import (
    Institution, KPIMetric, KPIAggregate, Alert, Ranking
)

# ─────────────────────────────────────────────────────────────────────────────
# DONNÉES RÉALISTES — 30 institutions UCAR
# ─────────────────────────────────────────────────────────────────────────────

# 5 institutions — une par catégorie de performance
INSTITUTIONS = [
    {"name": "FST Tunis",    "code": "FST_TUN",  "region": "Tunis"},       # 🏆 Élite
    {"name": "ISET Sfax",    "code": "ISET_SFX", "region": "Sfax"},        # ✅ Bon
    {"name": "ISET Nabeul",  "code": "ISET_NBL", "region": "Nabeul"},      # 🔵 Moyen
    {"name": "IPEIEM",       "code": "IPEIEM",   "region": "Tunis"},        # ⚠️ Difficulté
    {"name": "ISET Ariana",  "code": "ISET_ARN", "region": "Ariana"},      # 🚨 Critique
]

# Profils de performance — 5 catégories très distinctes
INSTITUTION_PROFILES = {
    # 🏆 ÉLITE — Tout au vert, tendance croissante
    "FST_TUN":   {"base_success": 91, "base_dropout": 4,  "base_attendance": 94, "trend": "improving"},

    # ✅ BON — Au-dessus de la moyenne, stable
    "ISET_SFX":  {"base_success": 78, "base_dropout": 9,  "base_attendance": 84, "trend": "stable"},

    # 🔵 MOYEN — Dans la moyenne nationale
    "ISET_NBL":  {"base_success": 65, "base_dropout": 15, "base_attendance": 74, "trend": "stable"},

    # ⚠️ DIFFICULTÉ — Sous la moyenne, tendance dégradée
    "IPEIEM":    {"base_success": 52, "base_dropout": 21, "base_attendance": 63, "trend": "deteriorating"},

    # 🚨 CRITIQUE — Crise active, alertes déclenchées
    "ISET_ARN":  {"base_success": 41, "base_dropout": 27, "base_attendance": 55, "trend": "crisis"},
}

ACADEMIC_INDICATORS = [
    {"name": "success_rate",        "unit": "%",  "min": 45, "max": 92, "higher_is_better": True},
    {"name": "dropout_rate",        "unit": "%",  "min": 5,  "max": 28, "higher_is_better": False},
    {"name": "attendance_rate",     "unit": "%",  "min": 60, "max": 95, "higher_is_better": True},
    {"name": "grade_repetition_rate","unit": "%", "min": 3,  "max": 18, "higher_is_better": False},
    {"name": "exam_pass_rate",      "unit": "%",  "min": 55, "max": 90, "higher_is_better": True},
]


# ─────────────────────────────────────────────────────────────────────────────
# GÉNÉRATEUR DE VALEURS RÉALISTES
# ─────────────────────────────────────────────────────────────────────────────

def generate_kpi_value(indicator: dict, institution_code: str, month_offset: int) -> float:
    """
    Génère une valeur réaliste selon le profil de l'institution.
    Chaque catégorie produit des valeurs clairement distinctes.
    """
    profile = INSTITUTION_PROFILES.get(institution_code, {})
    trend = profile.get("trend", "stable")
    ind_name = indicator["name"]

    # ── Valeur de base selon le profil ──────────────────────────────────────
    if ind_name == "success_rate":
        base = profile.get("base_success", 65)
    elif ind_name == "dropout_rate":
        base = profile.get("base_dropout", 15)
    elif ind_name == "attendance_rate":
        base = profile.get("base_attendance", 75)
    elif ind_name == "exam_pass_rate":
        # Corrélé au taux de réussite ± décalage
        base = profile.get("base_success", 65) * 0.95 + random.uniform(-3, 3)
    elif ind_name == "grade_repetition_rate":
        # Inversement corrélé au taux de réussite
        success = profile.get("base_success", 65)
        base = max(2, 25 - success * 0.22)
    else:
        base = (indicator["min"] + indicator["max"]) / 2

    # ── Appliquer la tendance sur les 6 derniers mois (offset 12 → 17) ─────
    if month_offset >= 12:
        recent = month_offset - 11  # 1 à 6

        if trend == "crisis":
            # Dégradation rapide : +2-3% d'abandon par mois, -2% de réussite
            if ind_name == "dropout_rate":
                base += recent * random.uniform(1.8, 3.0)
            elif ind_name in ["success_rate", "attendance_rate", "exam_pass_rate"]:
                base -= recent * random.uniform(1.5, 2.5)

        elif trend == "deteriorating":
            if ind_name == "dropout_rate":
                base += recent * random.uniform(0.8, 1.5)
            elif ind_name in ["success_rate", "attendance_rate"]:
                base -= recent * random.uniform(0.5, 1.0)

        elif trend == "improving":
            if ind_name in ["success_rate", "attendance_rate", "exam_pass_rate"]:
                base += recent * random.uniform(0.4, 0.9)
            elif ind_name == "dropout_rate":
                base -= recent * random.uniform(0.2, 0.6)

    # ── Bruit réaliste ±1.5% ────────────────────────────────────────────────
    noise = random.uniform(-1.5, 1.5)
    value = base + noise

    # ── Borner aux plages valides ────────────────────────────────────────────
    value = max(indicator["min"] * 0.75, min(indicator["max"] * 1.05, value))
    return round(value, 1)


# ─────────────────────────────────────────────────────────────────────────────
# FONCTIONS DE SEED
# ─────────────────────────────────────────────────────────────────────────────

def create_tables():
    """Crée toutes les tables."""
    print("  → Création des tables...")
    Base.metadata.create_all(bind=engine)
    print("  ✓ Tables créées")


def seed_institutions(session) -> dict:
    """Crée les 30 institutions. Retourne un dict code → institution_id."""
    print("\n  → Création des 30 institutions...")

    # Supprimer d'abord les données existantes (dans l'ordre FK)
    session.execute(text("DELETE FROM alerts"))
    session.execute(text("DELETE FROM kpi_predictions"))
    session.execute(text("DELETE FROM kpi_aggregates"))
    session.execute(text("DELETE FROM rankings"))
    session.execute(text("DELETE FROM kpi_metrics"))
    session.execute(text("DELETE FROM institutions"))
    session.commit()

    institution_map = {}
    for inst_data in INSTITUTIONS:
        inst = Institution(
            id=uuid.uuid4(),
            name=inst_data["name"],
            code=inst_data["code"],
            type="institution",
            region=inst_data["region"],
            contact_email=f"contact@{inst_data['code'].lower()}.tn",
            is_active=True,
        )
        session.add(inst)
        institution_map[inst_data["code"]] = inst

    session.commit()
    print(f"  ✓ {len(INSTITUTIONS)} institutions créées")
    return institution_map


def seed_academic_kpis(session, institution_map: dict) -> list:
    """Crée 18 mois de KPIs académiques pour chaque institution."""
    print("\n  → Génération des KPIs académiques (18 mois × 30 inst × 5 indicateurs)...")

    all_kpis = []
    now = datetime.utcnow()

    for code, institution in institution_map.items():
        for month_offset in range(18):  # 18 mois en arrière
            reporting_date = now - timedelta(days=30 * (17 - month_offset))
            reporting_date = reporting_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            for indicator in ACADEMIC_INDICATORS:
                value = generate_kpi_value(indicator, code, month_offset)

                kpi = KPIMetric(
                    id=uuid.uuid4(),
                    institution_id=institution.id,
                    domain="academic",
                    indicator=indicator["name"],
                    period="monthly",
                    value=value,
                    unit=indicator["unit"],
                    reporting_date=reporting_date,
                    data_source="seed",
                )
                session.add(kpi)
                all_kpis.append(kpi)

    session.commit()
    total = len(INSTITUTIONS) * 18 * len(ACADEMIC_INDICATORS)
    print(f"  ✓ {total} KPIs académiques créés")
    return all_kpis


def seed_aggregates(session, institution_map: dict):
    """Calcule et stocke les agrégats UCAR pour chaque indicateur."""
    print("\n  → Calcul des agrégats consolidés UCAR...")

    now = datetime.utcnow()

    # Agrégats sur les 6 derniers mois
    for month_offset in range(6):
        reporting_date = now - timedelta(days=30 * month_offset)
        reporting_date = reporting_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        for indicator in ACADEMIC_INDICATORS:
            # Récupérer toutes les valeurs du mois pour cet indicateur
            kpis = session.query(KPIMetric).filter(
                KPIMetric.domain == "academic",
                KPIMetric.indicator == indicator["name"],
                KPIMetric.period == "monthly",
            ).all()

            if not kpis:
                continue

            values = [k.value for k in kpis]
            avg_val = sum(values) / len(values)
            min_val = min(values)
            max_val = max(values)
            variance = sum((x - avg_val) ** 2 for x in values) / len(values)
            std_dev = variance ** 0.5
            breakdown = {str(k.institution_id): k.value for k in kpis}

            agg = KPIAggregate(
                id=uuid.uuid4(),
                domain="academic",
                indicator=indicator["name"],
                period="monthly",
                reporting_date=reporting_date,
                avg_value=round(avg_val, 2),
                min_value=round(min_val, 2),
                max_value=round(max_val, 2),
                std_dev=round(std_dev, 2),
                total_count=len(values),
                breakdown=breakdown,
            )
            session.add(agg)

    session.commit()
    print(f"  ✓ Agrégats créés pour 6 mois × {len(ACADEMIC_INDICATORS)} indicateurs")


def seed_alerts(session, institution_map: dict):
    """Crée des alertes pour les institutions en difficulté (données de démo)."""
    print("\n  → Création des alertes de démo...")

    # Institutions en difficulté connues
    problem_institutions = {
        "ISET_ARN": {"dropout_rate": 27.2, "threshold": 20.0, "severity": "critical"},
        "IPEIEM":   {"dropout_rate": 21.4, "threshold": 15.0, "severity": "warning"},
    }

    alerts_created = 0
    for code, alert_data in problem_institutions.items():
        institution = institution_map.get(code)
        if not institution:
            continue

        # Récupérer le dernier KPI dropout_rate
        kpi = session.query(KPIMetric).filter(
            KPIMetric.institution_id == institution.id,
            KPIMetric.indicator == "dropout_rate",
        ).order_by(KPIMetric.reporting_date.desc()).first()

        if kpi:
            alert = Alert(
                id=uuid.uuid4(),
                institution_id=institution.id,
                kpi_metric_id=kpi.id,
                severity=alert_data["severity"],
                status="active",
                title=f"Taux d'abandon critique — {institution.name}",
                message=(
                    f"Le taux d'abandon de {institution.name} est à "
                    f"{alert_data['dropout_rate']}%, dépassant le seuil de "
                    f"{alert_data['threshold']}%."
                ),
                xai_factors={
                    "surcharge_cours_S2": 0.84,
                    "baisse_tutorat": 0.62,
                    "problemes_transport": 0.31,
                    "difficultes_financieres": 0.28,
                },
                xai_explanation=(
                    f"Analyse IA : Le taux d'abandon de {institution.name} a augmenté de "
                    f"+{round(alert_data['dropout_rate'] - alert_data['threshold'], 1)} points "
                    f"sur les 3 derniers mois. "
                    "Cause principale identifiée : surcharge des cours S2 (corrélation 0.84). "
                    "Facteur aggravant : baisse du tutorat (-40% séances). "
                    "Recommandation : plan d'action en 3 axes urgents."
                ),
                threshold_value=alert_data["threshold"],
                actual_value=alert_data["dropout_rate"],
            )
            session.add(alert)
            alerts_created += 1

    session.commit()
    print(f"  ✓ {alerts_created} alertes créées (données démo)")


def seed_rankings(session, institution_map: dict):
    """Calcule le classement initial de toutes les institutions."""
    print("\n  → Calcul du classement gamifié...")

    now = datetime.utcnow()
    scores = []

    for code, institution in institution_map.items():
        # Calculer le score académique moyen sur les 3 derniers mois
        kpis = session.query(KPIMetric).filter(
            KPIMetric.institution_id == institution.id,
            KPIMetric.domain == "academic",
        ).order_by(KPIMetric.reporting_date.desc()).limit(15).all()

        if not kpis:
            continue

        # Normaliser chaque indicateur sur 100
        indicator_scores = {}
        for kpi in kpis:
            ind_config = next((i for i in ACADEMIC_INDICATORS if i["name"] == kpi.indicator), None)
            if not ind_config:
                continue

            if ind_config["higher_is_better"]:
                normalized = (kpi.value - ind_config["min"]) / (ind_config["max"] - ind_config["min"]) * 100
            else:
                # Inverser : plus bas = meilleur
                normalized = (1 - (kpi.value - ind_config["min"]) / (ind_config["max"] - ind_config["min"])) * 100

            normalized = max(0, min(100, normalized))

            if kpi.indicator not in indicator_scores:
                indicator_scores[kpi.indicator] = []
            indicator_scores[kpi.indicator].append(normalized)

        # Moyenne par indicateur
        avg_scores = {k: sum(v) / len(v) for k, v in indicator_scores.items()}

        # Score global pondéré
        overall = (
            avg_scores.get("success_rate", 0) * 0.35 +
            avg_scores.get("dropout_rate", 0) * 0.30 +
            avg_scores.get("attendance_rate", 0) * 0.20 +
            avg_scores.get("exam_pass_rate", 0) * 0.15
        )

        scores.append({
            "institution": institution,
            "overall_score": round(overall, 1),
            "academic_score": round(sum(avg_scores.values()) / len(avg_scores), 1) if avg_scores else 0,
        })

    # Trier par score décroissant
    scores.sort(key=lambda x: x["overall_score"], reverse=True)

    for rank_idx, entry in enumerate(scores, 1):
        badges = []
        if rank_idx == 1:
            badges.append("🏆 top_performer")
        if rank_idx <= 3:
            badges.append("🥇 podium")
        if entry["overall_score"] > 75:
            badges.append("⭐ excellence")
        if entry["institution"].code in ["FST_TUN", "ESSAI_CTH"]:
            badges.append("🌱 green_champion")

        ranking = Ranking(
            id=uuid.uuid4(),
            institution_id=entry["institution"].id,
            period="monthly",
            reporting_date=now,
            overall_score=entry["overall_score"],
            academic_score=entry["academic_score"],
            finance_score=round(random.uniform(60, 90), 1),
            esg_score=round(random.uniform(55, 85), 1),
            rank=rank_idx,
            badges=badges,
        )
        session.add(ranking)

    session.commit()
    print(f"  ✓ Classement créé pour {len(scores)} institutions")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  UniSmart AI — Seed Academic Data")
    print("=" * 60)

    session = SessionLocal()
    try:
        # Étape 1 : Tables
        create_tables()

        # Étape 2 : Institutions
        institution_map = seed_institutions(session)

        # Étape 3 : KPIs académiques
        seed_academic_kpis(session, institution_map)

        # Étape 4 : Agrégats UCAR
        seed_aggregates(session, institution_map)

        # Étape 5 : Alertes démo
        seed_alerts(session, institution_map)

        # Étape 6 : Classement
        seed_rankings(session, institution_map)

        print("\n" + "=" * 60)
        print("  ✅ SEED TERMINÉ AVEC SUCCÈS")
        print("=" * 60)
        print(f"""
  Résumé :
  • {len(INSTITUTIONS)} institutions créées (FST Tunis, ISET Sfax, ISET Nabeul, IPEIEM, ISET Ariana)
  • {len(INSTITUTIONS) * 18 * len(ACADEMIC_INDICATORS)} KPIs académiques (18 mois)
  • Agrégats UCAR calculés
  • 2 alertes de démo (ISET Ariana 🚨 critique, IPEIEM ⚠️ warning)
  • Classement calculé
  
  Prochaine étape : uvicorn app.main:app --reload
  Puis ouvrir : http://localhost:8000/docs
""")

    except Exception as e:
        print(f"\n  ✗ Erreur : {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
