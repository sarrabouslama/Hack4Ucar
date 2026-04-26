"""Business logic for documents ingestion."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.modules.documents_ingestion.db_models import Document, DocumentStatus
from app.modules.documents_ingestion.models import (
    ExtractionResult,
    OCRDocumentRequest,
    OCRExtractionField,
    OCRExtractionResponse,
)
from app.modules.documents_ingestion.parsers import CONTENT_TYPE_TO_EXTENSION, PARSERS_BY_EXTENSION, SUPPORTED_EXTENSIONS
from app.core.ai_service import ai_service

ParserFunction = Callable[[Path], ExtractionResult]


class DocumentIngestionService:
    """Service responsible for OCR normalization and document parsing."""

    SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS

    _DOCUMENT_HINTS = {
        "electricity_bill": ["kwh", "electricite", "electricity", "energie"],
        "gas_bill": ["gaz", "gas", "m3", "kwh pci"],
        "water_bill": ["eau", "water", "m3", "sonede"],
        "rse_proof": ["installation", "panneau", "solar", "led", "compost", "certificat"],
    }

    def __init__(self, storage_dir: str = "storage/documents") -> None:
        self.storage_root = Path(storage_dir)
        self.storage_root.mkdir(parents=True, exist_ok=True)

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

    async def upload_and_process(self, db: Session, file: UploadFile) -> Document:
        """Store an uploaded file, parse it, and persist the extraction result."""

        suffix, parser = self._resolve_parser(file.filename, file.content_type)
        saved_path, size = await self._save_upload(file, suffix)
        document = Document(
            filename=file.filename or saved_path.name,
            content_type=file.content_type or "application/octet-stream",
            size=size,
            status=DocumentStatus.PENDING.value,
            file_path=str(saved_path),
        )
        db.add(document)
        db.flush()

        try:
            extraction = self.parse_document(saved_path, parser)
            document.status = DocumentStatus.PROCESSED.value
            document.extracted_text = extraction.text
            document.extracted_data = json.dumps(self._serialize_extraction(extraction))
            document.parser_name = extraction.metadata.parser
            document.error_message = None
            
            # Generate embeddings for semantic search
            if document.extracted_text:
                try:
                    document.embedding = await ai_service.get_embeddings(document.extracted_text[:3000])
                except Exception as e:
                    print(f"Warning: Could not generate embedding: {e}")
        except Exception as exc:
            document.status = DocumentStatus.FAILED.value
            document.parser_name = "failed"
            document.error_message = str(exc)
            document.extracted_text = None
            document.extracted_data = json.dumps(self._build_failure_payload(suffix, exc))

        db.commit()
        db.refresh(document)
        return document

    def list_documents(self, db: Session) -> List[Document]:
        """Return all uploaded documents."""

        return db.query(Document).order_by(Document.created_at.desc()).all()

    def get_document(self, db: Session, document_id: UUID) -> Document:
        """Return one uploaded document."""

        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document

    async def hybrid_search(
        self, 
        db: Session, 
        query: str, 
        limit: int = 5,
        doc_type: str = None
    ) -> List[Document]:
        """
        Perform search using full-text search and metadata filters.
        (Vector similarity is currently stored as JSON for compatibility).
        """
        if not query:
            return []

        # Full-text search part
        ts_query = func.plainto_tsquery("french", query)
        text_rank = func.ts_rank(Document.search_vector, ts_query).label("text_rank")

        results_query = db.query(Document).filter(
            (Document.status == DocumentStatus.PROCESSED.value)
        )

        if doc_type:
            results_query = results_query.filter(Document.content_type.ilike(f"%{doc_type}%"))

        # In this compatibility version, we mainly use text rank
        results = (
            results_query
            .filter(Document.search_vector.op("@@")(ts_query))
            .order_by(text_rank.desc())
            .limit(limit)
            .all()
        )
        
        return results

    async def process_upload_preview(self, file: UploadFile) -> Dict[str, Any]:
        """Parse an uploaded file without persisting it to the database."""

        suffix, parser = self._resolve_parser(file.filename, file.content_type)
        saved_path, size = await self._save_upload(file, suffix)
        timestamp = datetime.utcnow()

        try:
            extraction = self.parse_document(saved_path, parser)
            payload = self._serialize_extraction(extraction)
            return {
                "id": uuid4(),
                "filename": file.filename or saved_path.name,
                "content_type": file.content_type or "application/octet-stream",
                "size": size,
                "status": DocumentStatus.PROCESSED.value,
                "extracted_text": extraction.text,
                "extracted_data": payload,
                "parser_name": extraction.metadata.parser,
                "error_message": None,
                "file_path": str(saved_path),
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        except Exception as exc:
            return {
                "id": uuid4(),
                "filename": file.filename or saved_path.name,
                "content_type": file.content_type or "application/octet-stream",
                "size": size,
                "status": DocumentStatus.FAILED.value,
                "extracted_text": None,
                "extracted_data": self._build_failure_payload(suffix, exc),
                "parser_name": "failed",
                "error_message": str(exc),
                "file_path": str(saved_path),
                "created_at": timestamp,
                "updated_at": timestamp,
            }

    def parse_document(self, file_path: Path, parser: ParserFunction) -> ExtractionResult:
        """Run the parser selected for an uploaded file."""

        return parser(file_path)

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

    def _build_recommendations(self, document_type: str, fields: List[OCRExtractionField]) -> List[str]:
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

    @staticmethod
    def _find_number_before_unit(text: str, units: List[str]) -> Optional[float]:
        for unit in units:
            pattern = rf"(\d+(?:[.,]\d+)?)\s*{re.escape(unit)}"
            match = re.search(pattern, text)
            if match:
                return float(match.group(1).replace(",", "."))
        return None

    def _resolve_parser(self, filename: str | None, content_type: str | None) -> Tuple[str, ParserFunction]:
        """Resolve which parser to use from content type or filename."""

        normalized_content_type = (content_type or "").split(";", 1)[0].strip().lower()
        inferred_suffix = CONTENT_TYPE_TO_EXTENSION.get(normalized_content_type)
        if inferred_suffix in self.SUPPORTED_EXTENSIONS:
            return inferred_suffix, PARSERS_BY_EXTENSION[inferred_suffix]

        suffix = Path(filename or "").suffix.lower()
        if suffix in self.SUPPORTED_EXTENSIONS:
            return suffix, PARSERS_BY_EXTENSION[suffix]

        detected = suffix or inferred_suffix or normalized_content_type or "unknown"
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {detected}")

    async def _save_upload(self, file: UploadFile, preferred_suffix: str) -> Tuple[Path, int]:
        """Persist the uploaded file to local storage."""

        filename = Path(file.filename or f"upload{preferred_suffix}").name
        if not Path(filename).suffix and preferred_suffix:
            filename = f"{filename}{preferred_suffix}"

        destination = self.storage_root / filename
        counter = 1
        while destination.exists():
            destination = self.storage_root / f"{destination.stem}-{counter}{destination.suffix}"
            counter += 1

        content = await file.read()
        destination.write_bytes(content)
        await file.seek(0)
        return destination, len(content)

    @staticmethod
    def deserialize_payload(document: Document) -> Dict[str, Any]:
        """Return structured JSON payload from the DB row."""

        if not document.extracted_data:
            return {}
        try:
            return json.loads(document.extracted_data)
        except json.JSONDecodeError:
            return {"raw": document.extracted_data}

    @classmethod
    def _make_json_safe(cls, value: Any) -> Any:
        """Convert parsed values into JSON-safe primitives."""

        if isinstance(value, dict):
            return {str(key): cls._make_json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._make_json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [cls._make_json_safe(item) for item in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, Path):
            return str(value)
        return value

    def _serialize_extraction(self, extraction: ExtractionResult) -> Dict[str, Any]:
        """Convert parser output into a JSON-safe payload."""

        return {
            "structured_data": self._make_json_safe(extraction.structured_data),
            "metadata": self._make_json_safe(extraction.metadata.model_dump()),
        }

    def _build_failure_payload(self, suffix: str, exc: Exception) -> Dict[str, Any]:
        """Build a consistent failure response payload."""

        return {
            "structured_data": {},
            "metadata": {
                "parser": "failed",
                "document_kind": suffix.lstrip(".") or "unknown",
                "warnings": [str(exc)],
            },
        }


documents_service = DocumentIngestionService()
document_ingestion_service = documents_service
