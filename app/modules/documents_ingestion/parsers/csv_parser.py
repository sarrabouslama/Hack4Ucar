"""CSV parsing helpers."""

import csv
from pathlib import Path

from app.modules.documents_ingestion.models import ExtractionMetadata, ExtractionResult


def parse_csv(file_path: Path) -> ExtractionResult:
    """Parse CSV files into structured rows."""

    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    text_lines = []
    if reader.fieldnames:
        text_lines.append(f"Headers: {', '.join(reader.fieldnames)}")
    text_lines.append(f"Rows: {len(rows)}")

    return ExtractionResult(
        text="\n".join(text_lines),
        structured_data={"rows": rows[:200], "headers": reader.fieldnames or []},
        metadata=ExtractionMetadata(
            parser="csv_parser",
            document_kind="csv",
        ),
    )
