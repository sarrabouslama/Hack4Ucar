"""Parser registry for document ingestion."""

from app.modules.documents_ingestion.parsers.csv_parser import parse_csv
from app.modules.documents_ingestion.parsers.excel_parser import parse_excel_workbook
from app.modules.documents_ingestion.parsers.image_parser import parse_image
from app.modules.documents_ingestion.parsers.pdf_parser import parse_pdf

PARSERS_BY_EXTENSION = {
    ".pdf": parse_pdf,
    ".png": parse_image,
    ".jpg": parse_image,
    ".jpeg": parse_image,
    ".tif": parse_image,
    ".tiff": parse_image,
    ".bmp": parse_image,
    ".xlsx": parse_excel_workbook,
    ".xlsm": parse_excel_workbook,
    ".csv": parse_csv,
}

CONTENT_TYPE_TO_EXTENSION = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/tiff": ".tif",
    "image/bmp": ".bmp",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel.sheet.macroenabled.12": ".xlsm",
    "text/csv": ".csv",
    "application/csv": ".csv",
    "application/vnd.ms-excel": ".csv",
}

SUPPORTED_EXTENSIONS = set(PARSERS_BY_EXTENSION.keys())

__all__ = [
    "CONTENT_TYPE_TO_EXTENSION",
    "PARSERS_BY_EXTENSION",
    "SUPPORTED_EXTENSIONS",
]
