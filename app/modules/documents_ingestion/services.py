"""Business logic for documents ingestion."""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.documents_ingestion.db_models import Document, DocumentStatus
from app.modules.documents_ingestion.models import (
    ExtractionResult,
    OCRDocumentRequest,
    OCRExtractionField,
    OCRExtractionResponse,
)
from app.modules.documents_ingestion.parsers import CONTENT_TYPE_TO_EXTENSION, PARSERS_BY_EXTENSION, SUPPORTED_EXTENSIONS
from app.modules.documents_ingestion.gemini_extractor import get_extractor
from app.shared.document_router import route_gemini_modules

ParserFunction = Callable[[Path], ExtractionResult]

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """Service responsible for OCR normalization, Gemini classification, and automated routing."""

    SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS

    def __init__(self, storage_dir: str = "storage/documents") -> None:
        self.storage_root = Path(storage_dir)
        self.storage_root.mkdir(parents=True, exist_ok=True)

    async def extract_document_data(self, db: Session, payload: OCRDocumentRequest) -> OCRExtractionResponse:
        """
        Convert OCR text into normalized fields and route them to other modules using Gemini.
        This is the core intelligence layer that maps unstructured text to structured KPIs.
        """
        
        # 1. Gemini Extraction & Classification
        extractor = get_extractor()
        gemini_result = extractor.extract_and_classify(payload.ocr_text[:5000])
        
        modules = gemini_result.get("modules", [])
        
        # 2. Automated Routing (Persistence to KPI/Finance tables)
        routing_summary = {}
        if payload.institution_id and db:
            try:
                institution_uuid = UUID(payload.institution_id)
                routing_summary = route_gemini_modules(
                    db=db,
                    institution_id=institution_uuid,
                    modules=modules,
                    period_label=payload.period_label or "monthly"
                )
                logger.info(f"Routing successful for {len(routing_summary)} modules")
            except Exception as e:
                logger.error(f"Routing failed: {e}")
                routing_summary = {"error": str(e)}

        # 3. Build UI-friendly normalized fields
        normalized_fields: List[OCRExtractionField] = []
        for mod_entry in modules:
            module_name = mod_entry.get("module")
            fields = mod_entry.get("fields", {}) or {}
            for key, val in fields.items():
                normalized_fields.append(
                    OCRExtractionField(
                        name=f"{module_name}_{key}",
                        value=val if isinstance(val, (int, float)) else 0,
                        confidence=mod_entry.get("confidence", 0.9),
                        source_fragment="gemini_extraction"
                    )
                )
        
        # 4. Prepare Response
        status = "processed" if not gemini_result.get("error") else "needs_review"
        confidence = 0.95 if status == "processed" else 0.5
        
        preview = payload.ocr_text[:220] + ("..." if len(payload.ocr_text) > 220 else "")

        return OCRExtractionResponse(
            filename=payload.filename,
            document_type=payload.document_type,
            status=status,
            confidence=confidence,
            extracted_text_preview=preview,
            normalized_fields=normalized_fields,
            structured_payload={
                "modules": modules,
                "routing_summary": routing_summary
            },
            recommendations=["Données extraites et intégrées via DocumentRouter."] if status == "processed" else ["Extraction incomplète."],
        )

    async def upload_and_process(self, db: Session, file: UploadFile, institution_id: Optional[str] = None) -> Document:
        """Main entry point for document uploads: saves, parses, extracts, and routes."""

        suffix, parser = self._resolve_parser(file.filename, file.content_type)
        saved_path, size = await self._save_upload(file, suffix)
        
        # Initial save to get the record in the DB
        document = Document(
            filename=file.filename or saved_path.name,
            content_type=file.content_type or "application/octet-stream",
            size=size,
            status=DocumentStatus.PENDING.value,
            file_path=str(saved_path),
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        try:
            # 1. OCR / Parser Step
            extraction = self.parse_document(saved_path, parser)
            document.extracted_text = extraction.text
            document.parser_name = extraction.metadata.parser
            
            # 2. Gemini & Routing Step
            if extraction.text:
                payload = OCRDocumentRequest(
                    institution_id=institution_id,
                    filename=document.filename,
                    document_type="unknown",
                    ocr_text=extraction.text[:5000]
                )
                extraction_response = await self.extract_document_data(db, payload)
                
                # Update document with AI metadata
                modules = extraction_response.structured_payload.get("modules", [])
                module_names = ", ".join([m.get("module") for m in modules if m.get("module")])
                document.module_classification = module_names or "documents_ingestion"
                
                document.extracted_data = json.dumps({
                    "parser": self._serialize_extraction(extraction),
                    "gemini": extraction_response.structured_payload
                })
                document.status = DocumentStatus.PROCESSED.value
            else:
                document.status = DocumentStatus.FAILED.value
                document.error_message = "No text extracted from document"
                
        except Exception as exc:
            logger.exception("Upload process failed")
            document.status = DocumentStatus.FAILED.value
            document.error_message = str(exc)
            document.extracted_data = json.dumps(self._build_failure_payload(suffix, exc))

        # Ensure persistence
        if document not in db:
            document = db.merge(document)
        db.commit()
        db.refresh(document)
        return document

    def list_documents(self, db: Session) -> List[Document]:
        return db.query(Document).order_by(Document.created_at.desc()).all()

    def get_document(self, db: Session, document_id: UUID) -> Document:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document

    def deserialize_payload(self, document: Document) -> Dict[str, Any]:
        """Return structured JSON payload from the DB row."""
        if not document.extracted_data:
            return {}
        try:
            return json.loads(document.extracted_data)
        except json.JSONDecodeError:
            return {"raw": document.extracted_data}

    async def route_existing_document(self, db: Session, document_id: UUID, institution_id: str) -> Dict[str, Any]:
        """Re-run the routing logic for a document that was already uploaded."""
        document = self.get_document(db, document_id)
        if not document.extracted_text:
            raise HTTPException(status_code=400, detail="Document has no extracted text")
            
        payload = OCRDocumentRequest(
            institution_id=institution_id,
            filename=document.filename,
            document_type="unknown",
            ocr_text=document.extracted_text[:5000]
        )
        
        extraction_response = await self.extract_document_data(db, payload)
        
        # Update classification
        modules = extraction_response.structured_payload.get("modules", [])
        document.module_classification = ", ".join([m.get("module") for m in modules if m.get("module")]) or "unknown"
        
        # Update data
        current_data = json.loads(document.extracted_data) if document.extracted_data else {}
        current_data["gemini"] = extraction_response.structured_payload
        document.extracted_data = json.dumps(current_data)
        
        if document not in db:
            document = db.merge(document)
        db.commit()
        
        return {
            "status": "success",
            "modules": [m.get("module") for m in modules]
        }

    def parse_document(self, file_path: Path, parser: ParserFunction) -> ExtractionResult:
        return parser(file_path)

    def _resolve_parser(self, filename: str | None, content_type: str | None) -> Tuple[str, ParserFunction]:
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

    def _serialize_extraction(self, extraction: ExtractionResult) -> Dict[str, Any]:
        return {
            "structured_data": self._make_json_safe(extraction.structured_data),
            "metadata": extraction.metadata.model_dump(),
        }

    def _build_failure_payload(self, suffix: str, exc: Exception) -> Dict[str, Any]:
        return {
            "structured_data": {},
            "metadata": {"parser": "failed", "warnings": [str(exc)]},
        }

    @classmethod
    def _make_json_safe(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): cls._make_json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._make_json_safe(item) for item in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, (Decimal, float)):
            return float(value)
        return value


documents_service = DocumentIngestionService()
document_ingestion_service = documents_service
