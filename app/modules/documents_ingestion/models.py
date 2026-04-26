"""Pydantic models for documents ingestion."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OCRDocumentRequest(BaseModel):
    """Input payload representing a scanned university document."""

    institution_id: str = Field(..., description="Institution identifier")
    filename: str = Field(..., description="Uploaded filename")
    document_type: Literal["electricity_bill", "gas_bill", "water_bill", "rse_proof", "generic"]
    period_label: Optional[str] = Field(
        default=None,
        description="Human-readable reporting period such as 2026-S1 or 2026-01",
    )
    ocr_text: str = Field(..., description="Raw OCR text extracted from the scanned document")


class OCRExtractionField(BaseModel):
    """A normalized OCR field."""

    name: str
    value: str | float | int
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_fragment: Optional[str] = None


class OCRExtractionResponse(BaseModel):
    """Parsed OCR result usable by downstream environmental models."""

    filename: str
    document_type: str
    status: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    extracted_text_preview: str
    normalized_fields: List[OCRExtractionField]
    structured_payload: Dict[str, str | float | int | bool]
    recommendations: List[str]


class ExtractionMetadata(BaseModel):
    """Metadata about how a document was parsed."""

    parser: str
    document_kind: str
    page_count: Optional[int] = None
    sheet_names: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Structured extraction output returned by the service."""

    text: str = ""
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: ExtractionMetadata


class DocumentResponse(BaseModel):
    """Serialized document row with parsed payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str
    size: int
    status: str
    extracted_text: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    parser_name: Optional[str] = None
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Document listing response."""

    items: List[DocumentResponse]


class UploadDocumentResponse(BaseModel):
    """Upload response with extraction summary."""

    document: DocumentResponse
    extraction_preview: Dict[str, Any] = Field(default_factory=dict)
