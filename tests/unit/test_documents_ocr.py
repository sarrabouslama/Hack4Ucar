import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from app.modules.documents_ingestion.models import OCRDocumentRequest
from app.modules.documents_ingestion.services import document_ingestion_service
from app.core.ai_service import ai_service


@pytest.mark.asyncio
async def test_ocr_extraction_returns_structured_energy_fields():
    payload = OCRDocumentRequest(
        institution_id="00000000-0000-0000-0000-000000000000",
        filename="facture-electricite-janvier.pdf",
        document_type="electricity_bill",
        period_label="2026-01",
        ocr_text="STEG Facture electricite janvier 2026 consommation 12500 kWh montant 4800 DT",
    )

    mock_db = MagicMock()
    mock_response = {
        "module": "environment",
        "data": {
            "utility_type": "electricity",
            "consumption_value": 12500,
            "consumption_unit": "kwh",
            "invoice_amount": 4800,
            "period_label": "2026-01"
        }
    }
    ai_service.generate_json = AsyncMock(return_value=json.dumps(mock_response))

    result = await document_ingestion_service.extract_document_data(mock_db, payload)

    assert result.status == "processed"
    assert result.structured_payload["consumption_value"] == 12500
    assert result.structured_payload["consumption_unit"] == "kwh"
    assert result.structured_payload["invoice_amount"] == 4800


@pytest.mark.asyncio
async def test_ocr_extraction_detects_rse_action():
    payload = OCRDocumentRequest(
        institution_id="00000000-0000-0000-0000-000000000000",
        filename="preuve-rse.pdf",
        document_type="rse_proof",
        ocr_text="Certificat d'installation de panneaux solaires et audit de mise en service",
    )

    mock_db = MagicMock()
    mock_response = {
        "module": "environment_rse",
        "data": {
            "title": "Installation de panneaux solaires",
            "category": "solar",
            "description": "Certificat d'installation de panneaux solaires",
            "estimated_co2_reduction_kg": 500.0
        }
    }
    ai_service.generate_json = AsyncMock(return_value=json.dumps(mock_response))

    result = await document_ingestion_service.extract_document_data(mock_db, payload)

    assert result.status == "processed"
    assert result.structured_payload["category"] == "solar"
