"""Image OCR helpers."""

from pathlib import Path
from typing import List

from app.modules.documents_ingestion.models import ExtractionMetadata, ExtractionResult

try:
    import pytesseract
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    pytesseract = None
    Image = None


def parse_image(file_path: Path) -> ExtractionResult:
    """OCR image files using Tesseract."""

    if pytesseract is None or Image is None:
        raise RuntimeError("Image OCR requires pytesseract and Pillow.")

    image = Image.open(file_path)
    text = pytesseract.image_to_string(image, lang="eng+fra+ara", config="--oem 3 --psm 6").strip()
    warnings: List[str] = []
    if not text:
        warnings.append("OCR completed but returned no text.")

    return ExtractionResult(
        text=text,
        structured_data={"preview": text[:2000]},
        metadata=ExtractionMetadata(
            parser="image_ocr",
            document_kind="image",
            warnings=warnings,
        ),
    )
