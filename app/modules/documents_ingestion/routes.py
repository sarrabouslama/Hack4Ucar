"""
API routes for documents ingestion
"""

from fastapi import APIRouter

from app.modules.documents_ingestion.models import OCRDocumentRequest, OCRExtractionResponse
from app.modules.documents_ingestion.services import document_ingestion_service

router = APIRouter()


@router.post("/ocr-extract", response_model=OCRExtractionResponse)
async def extract_document(payload: OCRDocumentRequest) -> OCRExtractionResponse:
    """Normalize scanned-document OCR output into structured ESG data."""

    return document_ingestion_service.extract_document_data(payload)
