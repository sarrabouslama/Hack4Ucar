"""
SMART objective generation from KPI summaries.
"""

import json
import os
from datetime import date
from typing import Any, Dict, List

import anthropic

from app.config import settings
from app.modules.finance_partnerships_hr.db_models import KpiTarget


def _anthropic_client() -> anthropic.Anthropic:
    api_key = settings.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured")
    return anthropic.Anthropic(api_key=api_key)


def _extract_text(response: Any) -> str:
    chunks: List[str] = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


def _parse_json_array(payload: str) -> List[Dict[str, Any]]:
    text = payload.strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        pass

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        parsed = json.loads(text[start : end + 1])
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _normalize_priority(value: Any) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = 3
    return max(1, min(5, parsed))


def _safe_date(value: Any):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except Exception:
        return None


def generate_smart_objectives(db_session, report_id: str, kpi_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    prompt = (
        "A partir du JSON KPI ci-dessous, retourne exactement 5 objectifs SMART.\n"
        "Tu dois repondre en JSON brut uniquement.\n"
        "Aucun markdown, aucune explication, aucun texte hors JSON.\n"
        "Format attendu: un tableau JSON de 5 objets avec les champs exacts:\n"
        "title, metric, target_value, deadline, responsible_role, priority.\n"
        "La priorite doit etre un entier de 1 a 5.\n"
        "La date deadline doit etre au format ISO YYYY-MM-DD.\n"
        f"KPI JSON:\n{json.dumps(kpi_summary, ensure_ascii=False, indent=2)}"
    )

    raw_text = ""
    try:
        response = _anthropic_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = _extract_text(response)
    except Exception as exc:
        print(f"[ERROR] Claude SMART objectives call failed: {exc}")
        return []

    items = _parse_json_array(raw_text)
    if not items:
        print("[ERROR] Failed to parse SMART objectives JSON")
        return []

    objectives: List[Dict[str, Any]] = []
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        metric = str(item.get("metric", "")).strip()
        target_value = str(item.get("target_value", "")).strip()
        deadline = _safe_date(item.get("deadline"))
        responsible_role = str(item.get("responsible_role", "")).strip()
        priority = _normalize_priority(item.get("priority"))

        target = KpiTarget(
            report_id=str(report_id),
            domain="finance_hr_research",
            objective=title or metric or "Objectif SMART",
            title=title or None,
            metric=metric or None,
            target_value=target_value or None,
            deadline=deadline,
            responsible_role=responsible_role or None,
            priority=priority,
            status="pending",
            ai_generated=True,
        )
        db_session.add(target)
        objectives.append(
            {
                "title": title,
                "metric": metric,
                "target_value": target_value,
                "deadline": deadline.isoformat() if deadline else None,
                "responsible_role": responsible_role,
                "priority": priority,
            }
        )

    return objectives
