"""
Pydantic models for documents ingestion
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    module_classification: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Document listing response."""

    items: List[DocumentResponse]


class UploadDocumentResponse(BaseModel):
    """Upload response with extraction summary."""

    document: DocumentResponse
    extraction_preview: Dict[str, Any] = Field(default_factory=dict)
