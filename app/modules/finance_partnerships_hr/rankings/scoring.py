"""
Composite scoring and gamification logic for institution rankings.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from app.core.database import SessionLocal
from app.modules.kpis.db_models import KPIMetric
from app.modules.environment_infrastructure.db_models import ESGMetric
from app.modules.finance_partnerships_hr.db_models import Absenteeism, Budget, Employee, Ranking

DOMAIN_WEIGHTS = {
    "academic": 0.30,
    "finance": 0.20,
    "hr": 0.20,
    "esg": 0.15,
    "research": 0.15,
}


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 2)))


def _compute_academic_score(db_session, institution_id: Optional[str] = None) -> float:
    avg_score = _safe_float(db_session.query(func.avg(KPIMetric.value)).filter(func.lower(KPIMetric.indicator).like("%exam%")).scalar())
    return _clamp_score(avg_score)


def _compute_finance_score(db_session, institution_id: Optional[str] = None) -> float:
    allocated = _safe_float(db_session.query(func.sum(Budget.allocated_amount)).scalar())
    spent = _safe_float(db_session.query(func.sum(Budget.spent_amount)).scalar())
    if allocated <= 0:
        return 0.0
    execution_pct = (spent / allocated) * 100.0
    return _clamp_score(execution_pct)


def _compute_hr_score(db_session, institution_id: Optional[str] = None) -> float:
    total_employees = int(db_session.query(func.count(Employee.id)).scalar() or 0)
    total_hours_missed = _safe_float(db_session.query(func.sum(Absenteeism.hours_missed)).scalar())
    if total_employees <= 0:
        return 0.0
    absenteeism_pct = (total_hours_missed / max(total_employees * 160.0, 1.0)) * 100.0
    return _clamp_score(100.0 - absenteeism_pct)


def _compute_esg_score(db_session, institution_id: Optional[str] = None) -> float:
    avg_esg = _safe_float(db_session.query(func.avg(ESGMetric.metric_value)).scalar())
    return _clamp_score(avg_esg)


def _compute_research_score(db_session, institution_id: Optional[str] = None) -> float:
    avg_research = _safe_float(db_session.query(func.avg(KPIMetric.value)).filter(func.lower(KPIMetric.domain) == "research").scalar())
    return _clamp_score(avg_research)


def _assign_badges(domain_scores: Dict[str, float]) -> List[str]:
    badges: List[str] = []
    if domain_scores.get("academic", 0.0) > 85:
        badges.append("Excellence Acad\u00e9mique")
    if domain_scores.get("esg", 0.0) > 80:
        badges.append("Green Campus")
    if domain_scores.get("finance", 0.0) > 80:
        badges.append("Gestion Exemplaire")
    if domain_scores.get("research", 0.0) > 75:
        badges.append("Recherche Active")
    return badges


def compute_composite_score(institution_id: str) -> Dict[str, Any]:
    db_session = SessionLocal()
    try:
        domain_scores = {
            "academic": _compute_academic_score(db_session, institution_id),
            "finance": _compute_finance_score(db_session, institution_id),
            "hr": _compute_hr_score(db_session, institution_id),
            "esg": _compute_esg_score(db_session, institution_id),
            "research": _compute_research_score(db_session, institution_id),
        }
        composite = 0.0
        for domain, weight in DOMAIN_WEIGHTS.items():
            composite += domain_scores.get(domain, 0.0) * weight
        composite = _clamp_score(composite)

        badges = _assign_badges(domain_scores)
        now = datetime.utcnow()
        ranking = Ranking(
            ranking_organization="UniSmart AI",
            rank_year=now.year,
            overall_rank=0,
            category="composite",
            score=composite,
            institution_id=institution_id,
            institution_name=institution_id,
            composite_score=composite,
            academic_score=domain_scores["academic"],
            finance_score=domain_scores["finance"],
            hr_score=domain_scores["hr"],
            esg_score=domain_scores["esg"],
            research_score=domain_scores["research"],
            domain_breakdown=domain_scores,
            badges=badges,
            scored_at=now,
        )
        db_session.add(ranking)
        db_session.commit()

        return {
            "institution_id": institution_id,
            "composite_score": composite,
            "domain_breakdown": domain_scores,
            "badges": badges,
            "timestamp": now.isoformat(),
        }
    except Exception as exc:
        db_session.rollback()
        print(f"[ERROR] Composite score computation failed: {exc}")
        return {
            "institution_id": institution_id,
            "composite_score": 0.0,
            "domain_breakdown": {},
            "badges": [],
            "timestamp": datetime.utcnow().isoformat(),
        }
    finally:
        db_session.close()


def _latest_rankings(db_session) -> List[Ranking]:
    rows = db_session.query(Ranking).order_by(Ranking.scored_at.desc(), Ranking.created_at.desc()).all()
    latest_by_institution: Dict[str, Ranking] = {}
    for row in rows:
        key = row.institution_id or row.institution_name or row.ranking_organization
        if not key:
            continue
        if key not in latest_by_institution:
            latest_by_institution[key] = row
    return list(latest_by_institution.values())


def get_full_rankings() -> List[Dict[str, Any]]:
    db_session = SessionLocal()
    try:
        latest = _latest_rankings(db_session)
        if not latest:
            db_session.close()
            compute_composite_score("UCAR")
            db_session = SessionLocal()
            latest = _latest_rankings(db_session)
        ordered = sorted(latest, key=lambda row: _safe_float(row.composite_score or row.score), reverse=True)
        response: List[Dict[str, Any]] = []
        for idx, row in enumerate(ordered, start=1):
            response.append(
                {
                    "rank": idx,
                    "institution_id": row.institution_id,
                    "institution_name": row.institution_name or row.ranking_organization,
                    "composite_score": _safe_float(row.composite_score or row.score),
                    "domain_breakdown": row.domain_breakdown or {},
                    "badges": row.badges or [],
                    "scored_at": (row.scored_at or row.created_at).isoformat(),
                }
            )
        return response
    except Exception as exc:
        print(f"[ERROR] Failed to build full rankings: {exc}")
        return []
    finally:
        db_session.close()


def get_anonymous_rankings(current_institution_id: Optional[str] = None) -> List[Dict[str, Any]]:
    full = get_full_rankings()
    code_by_institution: Dict[str, str] = {}
    response: List[Dict[str, Any]] = []

    for idx, item in enumerate(full, start=1):
        institution_id = item.get("institution_id") or item.get("institution_name") or f"institution_{idx}"
        if institution_id not in code_by_institution:
            code_by_institution[institution_id] = f"INST-{len(code_by_institution) + 1:03d}"
        response.append(
            {
                "rank": item["rank"],
                "anon_code": code_by_institution[institution_id],
                "composite_score": item["composite_score"],
                "domain_breakdown": item["domain_breakdown"],
                "badges": item["badges"],
                "is_current_institution": bool(current_institution_id and current_institution_id == institution_id),
                "scored_at": item["scored_at"],
            }
        )
    return response
