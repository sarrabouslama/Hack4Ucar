"""API routes for documents ingestion."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.documents_ingestion.models import (
    DocumentListResponse,
    DocumentResponse,
    OCRDocumentRequest,
    OCRExtractionResponse,
    UploadDocumentResponse,
)
from app.modules.documents_ingestion.services import documents_service

router = APIRouter()


def _serialize(document) -> DocumentResponse:
    payload = documents_service.deserialize_payload(document)
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        size=document.size,
        status=document.status,
        extracted_text=document.extracted_text,
        extracted_data=payload,
        parser_name=document.parser_name,
        error_message=document.error_message,
        file_path=document.file_path,
        module_classification=document.module_classification,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.post("/ocr-extract", response_model=OCRExtractionResponse)
async def extract_document(payload: OCRDocumentRequest, db: Session = Depends(get_db)) -> OCRExtractionResponse:
    """Normalize scanned-document OCR output into structured ESG data."""

    return await documents_service.extract_document_data(db, payload)


@router.post("/upload", response_model=UploadDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    institution_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload and process a document."""

    document = await documents_service.upload_and_process(db, file, institution_id)
    payload = documents_service.deserialize_payload(document)
    return UploadDocumentResponse(
        document=_serialize(document),
        extraction_preview={
            "text_preview": (document.extracted_text or "")[:500],
            "metadata": payload.get("metadata", {}),
        },
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(db: Session = Depends(get_db)):
    """List processed documents."""

    items = [_serialize(document) for document in documents_service.list_documents(db)]
    return DocumentListResponse(items=items)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: UUID, db: Session = Depends(get_db)):
    """Fetch one document by id."""

    return _serialize(documents_service.get_document(db, document_id))
    
@router.post("/documents/{document_id}/route")
async def route_document(document_id: UUID, institution_id: str, db: Session = Depends(get_db)):
    """Route an existing document's data to other modules."""
    return await documents_service.route_existing_document(db, document_id, institution_id)

@router.get("/search", response_model=DocumentListResponse)
async def search_documents(
    query: str, 
    limit: int = 5, 
    doc_type: str = None, 
    db: Session = Depends(get_db)
):
    """
    Search documents using hybrid semantic + full-text search.
    """
    results = await documents_service.hybrid_search(db, query, limit=limit, doc_type=doc_type)
    items = [_serialize(document) for document in results]
    return DocumentListResponse(items=items)
