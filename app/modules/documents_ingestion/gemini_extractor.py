"""Gemini-based document extraction and classification service."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.shared.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)


class DocumentExtractionPrompt:
    """Build prompts for multi-module classification and field extraction."""

    MODULE_SCHEMAS: Dict[str, Dict[str, Any]] = {
        "finance": {
            "fields": [
                "report_type",
                "fiscal_year",
                "fiscal_period",
                "department",
                "allocated_amount",
                "spent_amount",
                "total_revenue",
                "total_expenses",
                "net_result",
                "category",
                "currency",
            ],
            "description": "Financial budgets, invoices, expense reports, and financial statements",
        },
        "partnerships": {
            "fields": [
                "partner_name",
                "partner_type",
                "status",
                "start_date",
                "end_date",
                "contact_email",
                "contract_value",
                "collaboration_type",
            ],
            "description": "Partnership agreements, contracts, MoUs, and collaboration documents",
        },
        "hr": {
            "fields": [
                "employee_name",
                "department",
                "position",
                "contract_type",
                "start_date",
                "end_date",
                "salary",
                "performance_rating",
            ],
            "description": "HR records, employment contracts, payroll, and personnel evaluations",
        },
        "education_research": {
            "fields": [
                "institution_name",
                "degree_type",
                "field_of_study",
                "duration_years",
                "accreditation_status",
                "research_focus",
                "funding_source",
                "publication_count",
                "collaboration_institutions",
            ],
            "description": "Educational institutions, research papers, degrees, and academic programs",
        },
        "environment": {
            "fields": [
                "emission_type",
                "consumption_value",
                "consumption_unit",
                "carbon_footprint_kg",
                "energy_source",
                "sustainability_measures",
                "environmental_impact",
                "reporting_period",
            ],
            "description": "Environmental data, carbon footprint, energy/water consumption, and sustainability reports",
        },
        "infrastructure": {
            "fields": [
                "project_name",
                "location",
                "infrastructure_type",
                "budget",
                "completion_date",
                "stakeholders",
                "status",
            ],
            "description": "Infrastructure projects, construction, and facility management",
        },
        "documents_ingestion": {
            "fields": [
                "document_type",
                "title",
                "author",
                "publication_date",
                "pages",
                "language",
                "summary",
            ],
            "description": "General documents, reports, and publications that do not fit other modules",
        },
    }

    VALID_MODULES = set(MODULE_SCHEMAS.keys())

    @classmethod
    def build(cls, extracted_text: str) -> str:
        modules_desc = "\n".join(
            [f"- {name}: {schema['description']}" for name, schema in cls.MODULE_SCHEMAS.items()]
        )
        module_names = "|".join(cls.VALID_MODULES)

        return f"""You are a document classification and data extraction expert.

A single document can belong to MULTIPLE modules at the same time.
Example: an electricity bill belongs to both "finance" (it is an invoice) and "environment" (it contains consumption data for carbon footprint calculation).

Task:
1) Identify ALL modules this document is relevant to (can be one or more) from:
{modules_desc}

2) For each matched module, extract the relevant structured fields defined for that module.

3) Return ONLY strict JSON in this format (no prose, no markdown):
{{
  "modules": [
    {{
      "module": "{module_names}",
      "confidence": 0.0,
      "fields": {{"key": "value"}},
      "reasoning": "short reason why this module applies"
    }}
  ]
}}

Rules:
- Include a module entry only if the document genuinely relates to it.
- Confidence must be a float between 0.0 and 1.0.
- Extract only fields that are present in the document; omit fields with no data.
- If no specific module applies, include only "documents_ingestion".

Document text:
---
{extracted_text}
---
"""


class GeminiDocumentExtractor:
    """Extract structured data from parsed text using Gemini."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name

    def extract_and_classify(self, extracted_text: str) -> Dict[str, Any]:
        """Return a dict with a 'modules' list, each entry being a module classification."""
        try:
            prompt = DocumentExtractionPrompt.build((extracted_text or "")[:4000])
            client = get_gemini_client(self.model_name)
            raw = client.generate_text(prompt, temperature=0.1)
            parsed = self._parse_response_json(raw)
            parsed["modules"] = self._validate_modules(parsed.get("modules", []))
            return parsed
        except RuntimeError as exc:
            logger.error("Gemini extraction unavailable: %s", exc)
            return {
                "modules": [
                    {
                        "module": "documents_ingestion",
                        "confidence": 0,
                        "fields": {"raw_text_preview": (extracted_text or "")[:500]},
                        "reasoning": "Gemini extraction unavailable",
                    }
                ],
                "error": str(exc),
            }
        except Exception as exc:
            logger.error("Gemini extraction failed: %s", exc)
            return {
                "modules": [
                    {
                        "module": "documents_ingestion",
                        "confidence": 0,
                        "fields": {},
                        "reasoning": "Extraction service error",
                    }
                ],
                "error": str(exc),
            }

    @staticmethod
    def _parse_response_json(raw: str) -> Dict[str, Any]:
        text = (raw or "").strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3:
                text = "\n".join(lines[1:-1]).strip()
                if text.lower().startswith("json"):
                    text = text[4:].strip()

        result = json.loads(text)
        if not isinstance(result, dict):
            raise ValueError("Model response is not a JSON object")

        modules = result.get("modules", [])
        if not isinstance(modules, list):
            raise ValueError("'modules' field must be a list")

        return {"modules": modules}

    @staticmethod
    def _validate_modules(modules: List[Any]) -> List[Dict[str, Any]]:
        """Sanitise each module entry; drop unknown module names."""
        valid = DocumentExtractionPrompt.VALID_MODULES
        sanitised: List[Dict[str, Any]] = []

        for entry in modules:
            if not isinstance(entry, dict):
                continue
            module_name = entry.get("module", "")
            if module_name not in valid:
                logger.warning("Gemini returned unknown module '%s', skipping.", module_name)
                continue
            sanitised.append(
                {
                    "module": module_name,
                    "confidence": max(0.0, min(1.0, float(entry.get("confidence") or 0))),
                    "fields": entry.get("fields", {}) or {},
                    "reasoning": entry.get("reasoning", ""),
                }
            )

        # Fallback: always return at least one module
        if not sanitised:
            sanitised.append(
                {
                    "module": "documents_ingestion",
                    "confidence": 0.0,
                    "fields": {},
                    "reasoning": "No valid module returned by model",
                }
            )

        return sanitised


_extractor_instance: Optional[GeminiDocumentExtractor] = None


def get_extractor() -> GeminiDocumentExtractor:
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = GeminiDocumentExtractor()
    return _extractor_instance