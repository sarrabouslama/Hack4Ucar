"""
Business logic for documents ingestion
"""

import re
from typing import Dict, List, Optional

from app.modules.documents_ingestion.models import (
    OCRDocumentRequest,
    OCRExtractionField,
    OCRExtractionResponse,
)


class DocumentIngestionService:
    """OCR normalization service for university documents."""

    _DOCUMENT_HINTS = {
        "electricity_bill": ["kwh", "electricite", "electricity", "energie"],
        "gas_bill": ["gaz", "gas", "m3", "kwh pci"],
        "water_bill": ["eau", "water", "m3", "sonede"],
        "rse_proof": ["installation", "panneau", "solar", "led", "compost", "certificat"],
    }

    def extract_document_data(self, payload: OCRDocumentRequest) -> OCRExtractionResponse:
        """Convert OCR text into normalized fields used by the ESG scoring engine."""

        lowered_text = payload.ocr_text.lower()
        normalized_fields: List[OCRExtractionField] = []
        structured_payload: Dict[str, str | float | int | bool] = {
            "institution_id": payload.institution_id,
            "document_type": payload.document_type,
        }

        amount = self._find_number_before_unit(lowered_text, ["dt", "tnd", "eur", "$"])
        consumption = self._extract_consumption(payload.document_type, lowered_text)
        if amount is not None:
            normalized_fields.append(
                OCRExtractionField(
                    name="invoice_amount",
                    value=amount,
                    confidence=0.91,
                    source_fragment="currency amount",
                )
            )
            structured_payload["invoice_amount"] = amount
        if consumption is not None:
            normalized_fields.append(
                OCRExtractionField(
                    name="consumption",
                    value=consumption["value"],
                    confidence=consumption["confidence"],
                    source_fragment=consumption["unit"],
                )
            )
            structured_payload["consumption_value"] = consumption["value"]
            structured_payload["consumption_unit"] = consumption["unit"]

        action = self._extract_rse_action(lowered_text)
        if action:
            normalized_fields.append(
                OCRExtractionField(
                    name="rse_action",
                    value=action,
                    confidence=0.85,
                    source_fragment=action,
                )
            )
            structured_payload["rse_action"] = action

        document_matches = sum(
            1 for hint in self._DOCUMENT_HINTS.get(payload.document_type, []) if hint in lowered_text
        )
        confidence = min(0.55 + 0.1 * len(normalized_fields) + 0.05 * document_matches, 0.99)
        status = "processed" if normalized_fields else "needs_review"
        recommendations = self._build_recommendations(payload.document_type, normalized_fields)
        preview = payload.ocr_text[:220]
        if len(payload.ocr_text) > 220:
            preview += "..."

        return OCRExtractionResponse(
            filename=payload.filename,
            document_type=payload.document_type,
            status=status,
            confidence=round(confidence, 2),
            extracted_text_preview=preview,
            normalized_fields=normalized_fields,
            structured_payload=structured_payload,
            recommendations=recommendations,
        )

    def _extract_consumption(self, document_type: str, text: str) -> Optional[Dict[str, str | float]]:
        patterns = {
            "electricity_bill": [("kwh", ["kwh", "kw/h"])],
            "gas_bill": [("m3", ["m3"]), ("kwh", ["kwh"])],
            "water_bill": [("m3", ["m3"])],
        }
        for normalized_unit, aliases in patterns.get(document_type, []):
            value = self._find_number_before_unit(text, aliases)
            if value is not None:
                return {
                    "value": value,
                    "unit": normalized_unit,
                    "confidence": 0.93 if normalized_unit in text else 0.88,
                }
        return None

    def _extract_rse_action(self, text: str) -> Optional[str]:
        actions = {
            "solar_panels": ["panneau solaire", "panneaux solaires", "solar panel"],
            "led_retrofit": ["led", "ampoule led", "eclairage led"],
            "composting": ["compost", "compostage"],
            "water_reuse": ["reutilisation eau", "recycled water", "reuse water"],
        }
        for action, keywords in actions.items():
            if any(keyword in text for keyword in keywords):
                return action
        return None

    def _build_recommendations(
        self,
        document_type: str,
        fields: List[OCRExtractionField],
    ) -> List[str]:
        field_names = {field.name for field in fields}
        recommendations: List[str] = []
        if "consumption" not in field_names and document_type in {"electricity_bill", "gas_bill", "water_bill"}:
            recommendations.append("Verifier la lisibilite du document: consommation non detectee.")
        if "invoice_amount" not in field_names:
            recommendations.append("Ajouter un scan plus net pour extraire le montant de la facture.")
        if document_type == "rse_proof" and "rse_action" not in field_names:
            recommendations.append("Completer la description de l'acte RSE pour faciliter la verification.")
        if not recommendations:
            recommendations.append("Document exploitable pour le calcul ESG et le controle de fiabilite.")
        return recommendations

    def _find_number_before_unit(self, text: str, units: List[str]) -> Optional[float]:
        for unit in units:
            pattern = rf"(\d+(?:[.,]\d+)?)\s*{re.escape(unit)}"
            match = re.search(pattern, text)
            if match:
                return float(match.group(1).replace(",", "."))
        return None


document_ingestion_service = DocumentIngestionService()
