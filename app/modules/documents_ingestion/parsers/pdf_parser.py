"""PDF parsing helpers."""

from pathlib import Path
from typing import List, Tuple

from app.modules.documents_ingestion.models import ExtractionMetadata, ExtractionResult

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency
    PdfReader = None

try:
    import pytesseract
except Exception:  # pragma: no cover - optional dependency
    pytesseract = None

try:
    from pdf2image import convert_from_path
except Exception:  # pragma: no cover - optional dependency
    convert_from_path = None


def parse_pdf(file_path: Path) -> ExtractionResult:
    """Extract text from PDF and fall back to OCR when needed."""

    if PdfReader is None:
        raise RuntimeError("PDF parsing dependency missing. Install pypdf.")

    reader = PdfReader(str(file_path))
    page_texts: List[str] = []
    warnings: List[str] = []

    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            page_texts.append(text.strip())
        else:
            warnings.append(f"Page {index} contained no machine-readable text.")

    extracted_text = "\n\n".join(page_texts).strip()
    parser_name = "pdf_text"

    if not extracted_text:
        ocr_text, ocr_warnings = _run_pdf_ocr(file_path)
        extracted_text = ocr_text
        warnings.extend(ocr_warnings)
        parser_name = "pdf_ocr"

    structured_data = {
        "preview": extracted_text[:2000],
        "page_summaries": [
            {"page_number": index + 1, "characters": len(text)}
            for index, text in enumerate(page_texts)
        ],
    }

    return ExtractionResult(
        text=extracted_text,
        structured_data=structured_data,
        metadata=ExtractionMetadata(
            parser=parser_name,
            document_kind="pdf",
            page_count=len(reader.pages),
            warnings=warnings,
        ),
    )


def _run_pdf_ocr(file_path: Path) -> Tuple[str, List[str]]:
    """OCR scanned PDFs by converting them to images first."""

    if convert_from_path is None:
        raise RuntimeError("Scanned PDF OCR requires pdf2image and a Poppler installation.")
    if pytesseract is None:
        raise RuntimeError("OCR requires pytesseract and a Tesseract installation.")

    warnings: List[str] = []
    pages = convert_from_path(str(file_path))
    chunks: List[str] = []
    for index, image in enumerate(pages, start=1):
        text = pytesseract.image_to_string(image, lang="eng+fra+ara", config="--oem 3 --psm 6")
        if text.strip():
            chunks.append(text.strip())
        else:
            warnings.append(f"OCR produced no text for page {index}.")
    return "\n\n".join(chunks).strip(), warnings
