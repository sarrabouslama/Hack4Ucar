from app.modules.documents_ingestion.models import OCRDocumentRequest
from app.modules.documents_ingestion.services import document_ingestion_service


def test_ocr_extraction_returns_structured_energy_fields():
    payload = OCRDocumentRequest(
        institution_id="ucar-fst",
        filename="facture-electricite-janvier.pdf",
        document_type="electricity_bill",
        period_label="2026-01",
        ocr_text="STEG Facture electricite janvier 2026 consommation 12500 kWh montant 4800 DT",
    )

    result = document_ingestion_service.extract_document_data(payload)

    assert result.status == "processed"
    assert result.structured_payload["consumption_value"] == 12500
    assert result.structured_payload["consumption_unit"] == "kwh"
    assert result.structured_payload["invoice_amount"] == 4800


def test_ocr_extraction_detects_rse_action():
    payload = OCRDocumentRequest(
        institution_id="ucar-ipei",
        filename="preuve-rse.pdf",
        document_type="rse_proof",
        ocr_text="Certificat d'installation de panneaux solaires et audit de mise en service",
    )

    result = document_ingestion_service.extract_document_data(payload)

    assert result.status == "processed"
    assert result.structured_payload["rse_action"] == "solar_panels"
