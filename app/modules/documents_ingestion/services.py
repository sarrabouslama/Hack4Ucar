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
from app.modules.documents_ingestion.gemini_extractor import get_extractor

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

    async def extract_document_data(self, db: Session, payload: OCRDocumentRequest) -> OCRExtractionResponse:
        """Convert OCR text into normalized fields and route them to other modules using Gemini."""
        
        # Call the new gemini extractor
        extractor = get_extractor()
        gemini_result = extractor.extract_and_classify(payload.ocr_text[:5000])
        
        normalized_fields: List[OCRExtractionField] = []
        structured_payload: Dict[str, Any] = {
            "institution_id": payload.institution_id,
            "document_type": payload.document_type,
            "modules": gemini_result.get("modules", [])
        }
        
        if payload.institution_id and db:
            try:
                institution_uuid = UUID(payload.institution_id)
                from app.modules.kpis.services import KPIService
                kpi_service = KPIService(db)
                
                for mod_entry in gemini_result.get("modules", []):
                    module = mod_entry.get("module")
                    data = mod_entry.get("fields", {})
                    
                    if module in ["education_research", "academic"]:
                        for indicator, value in data.items():
                            if isinstance(value, (int, float)):
                                kpi_service.create_kpi(
                                    institution_id=institution_uuid,
                                    domain="academic",
                                    indicator=indicator,
                                    period="monthly",
                                    value=float(value),
                                    unit="count" if "count" in indicator else "%",
                                    data_source="document_ingestion"
                                )
                    elif module == "environment":
                        if "consumption_value" in data:
                            utility = data.get("energy_source", "unknown")
                            kpi_service.create_kpi(
                                institution_id=institution_uuid,
                                domain="environment",
                                indicator=f"consumption_{utility}",
                                period="monthly",
                                value=float(data["consumption_value"]),
                                unit=data.get("consumption_unit", ""),
                                data_source="document_ingestion"
                            )
                        if "carbon_footprint_kg" in data:
                            kpi_service.create_kpi(
                                institution_id=institution_uuid,
                                domain="environment",
                                indicator="carbon_footprint",
                                period="monthly",
                                value=float(data["carbon_footprint_kg"]),
                                unit="kg",
                                data_source="document_ingestion",
                                notes=data.get("emission_type", "")
                            )
                    elif module == "finance":
                        from app.modules.finance_partnerships_hr.services import FormService
                        from app.modules.finance_partnerships_hr.models import BudgetReportInput
                        form_service = FormService(db)
                        budget_input = BudgetReportInput(
                            department=str(data.get("department", "general")),
                            fiscal_year=int(data.get("fiscal_year", datetime.utcnow().year)),
                            allocated_amount=float(data.get("allocated_amount") or data.get("total_revenue") or 0.0),
                            spent_amount=float(data.get("spent_amount") or data.get("total_expenses") or 0.0),
                            category=str(data.get("category", "general"))
                        )
                        await form_service.submit_budget_report(budget_input)
                    elif module == "hr":
                        if "salary" in data:
                            kpi_service.create_kpi(
                                institution_id=institution_uuid,
                                domain="hr",
                                indicator="average_salary",
                                period="monthly",
                                value=float(data["salary"]),
                                unit="DT",
                                data_source="document_ingestion",
                                notes=f"Position: {data.get('position', 'unknown')}"
                            )
                    elif module == "partnerships":
                        if "contract_value" in data:
                            kpi_service.create_kpi(
                                institution_id=institution_uuid,
                                domain="partnerships",
                                indicator="contract_value",
                                period="yearly",
                                value=float(data["contract_value"]),
                                unit="DT",
                                data_source="document_ingestion",
                                notes=f"Partner: {data.get('partner_name', 'unknown')}"
                            )
                    elif module == "infrastructure":
                        if "budget" in data:
                            kpi_service.create_kpi(
                                institution_id=institution_uuid,
                                domain="infrastructure",
                                indicator="infrastructure_budget",
                                period="yearly",
                                value=float(data["budget"]),
                                unit="DT",
                                data_source="document_ingestion",
                                notes=f"Project: {data.get('project_name', 'unknown')}, Status: {data.get('status', 'unknown')}"
                            )
            except ValueError as e:
                print(f"Failed routing document due to value error: {e}")

        for mod_entry in gemini_result.get("modules", []):
            for key, val in mod_entry.get("fields", {}).items():
                normalized_fields.append(
                    OCRExtractionField(
                        name=f"{mod_entry.get('module')}_{key}",
                        value=val if isinstance(val, (int, float)) else 0,
                        confidence=mod_entry.get("confidence", 0.9),
                        source_fragment="ai_extraction"
                    )
                )
                
        status = "processed"
        confidence = 0.95
        recommendations = ["Données extraites et intégrées avec succès via l'IA."]
        
        if "error" in gemini_result:
            status = "needs_review"
            confidence = 0.5
            recommendations = ["Échec de l'extraction IA. Vérifiez la lisibilité du document."]

        preview = payload.ocr_text[:220]
        if len(payload.ocr_text) > 220:
            preview += "..."

        return OCRExtractionResponse(
            filename=payload.filename,
            document_type=payload.document_type,
            status=status,
            confidence=confidence,
            extracted_text_preview=preview,
            normalized_fields=normalized_fields,
            structured_payload=structured_payload,
            recommendations=recommendations,
        )

    async def upload_and_process(self, db: Session, file: UploadFile, institution_id: Optional[str] = None) -> Document:
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
        db.commit()
        db.refresh(document)

        try:
            extraction = self.parse_document(saved_path, parser)
            document.status = DocumentStatus.PROCESSED.value
            document.extracted_text = extraction.text
            document.parser_name = extraction.metadata.parser
            document.error_message = None
            
            parser_data = self._serialize_extraction(extraction)
            
            # Always run Gemini extraction and classification (even without institution_id)
            if extraction.text:
                payload = OCRDocumentRequest(
                    institution_id=institution_id,
                    filename=document.filename,
                    document_type="unknown",
                    ocr_text=extraction.text[:5000]
                )
                # extract_document_data handles the automated routing if institution_id is set
                extraction_response = await self.extract_document_data(db, payload)
                
                # Set module classification from the detected modules
                modules = extraction_response.structured_payload.get("modules", [])
                module_names = ", ".join([m.get("module") for m in modules if m.get("module")])
                document.module_classification = module_names or "documents_ingestion"
                
                # Combine parser results and Gemini intelligence
                combined_data = {
                    "parser": parser_data,
                    "gemini_extraction": extraction_response.structured_payload
                }
                document.extracted_data = json.dumps(combined_data)
            else:
                document.extracted_data = json.dumps({"parser": parser_data})
                
        except Exception as exc:
            document.status = DocumentStatus.FAILED.value
            document.parser_name = "failed"
            document.error_message = str(exc)
            document.extracted_text = None
            document.extracted_data = json.dumps(self._build_failure_payload(suffix, exc))

        if document not in db:
            document = db.merge(document)
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

    async def route_existing_document(self, db: Session, document_id: UUID, institution_id: str) -> Dict[str, Any]:
        """Route an existing document's extracted data to other modules."""
        document = self.get_document(db, document_id)
        
        if not document.extracted_text:
            raise HTTPException(status_code=400, detail="Document has no extracted text to route")
            
        payload = OCRDocumentRequest(
            institution_id=institution_id,
            filename=document.filename,
            document_type="unknown",
            ocr_text=document.extracted_text[:5000]
        )
        
        # This will trigger all kpi_service and form_service calls
        extraction_response = await self.extract_document_data(db, payload)
        
        # Update module classification
        modules = extraction_response.structured_payload.get("modules", [])
        module_names = ", ".join([m.get("module") for m in modules if m.get("module")])
        document.module_classification = module_names or "documents_ingestion"
        
        # Update document data with the new routing results
        combined_data = {
            "parser": self._serialize_extraction(self.parse_document(Path(document.file_path), self._resolve_parser(document.filename, document.content_type)[1])),
            "gemini_extraction": extraction_response.structured_payload
        }
        document.extracted_data = json.dumps(combined_data)
        if document not in db:
            document = db.merge(document)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Document {document_id} routed to institution {institution_id}",
            "modules_routed": [m.get("module") for m in extraction_response.structured_payload.get("modules", [])]
        }

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
