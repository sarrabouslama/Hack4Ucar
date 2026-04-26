"""
Pydantic models for documents ingestion
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


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
