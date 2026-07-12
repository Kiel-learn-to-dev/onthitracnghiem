"""Import question occurrences from PDFs that have selectable text."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path

from pypdf import PdfReader

from scripts.storage import record_source, record_source_question


QUESTION_HEADING = re.compile(r"(C\w*\s*(\d+)\s*[:.])", re.IGNORECASE)


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_text_pdf(db_path: Path, pdf_path: Path) -> int:
    """Extract each heading-delimited question occurrence from a text PDF."""
    reader = PdfReader(str(pdf_path))
    extracted: list[tuple[int, str, str]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        headings = list(QUESTION_HEADING.finditer(text))
        for index, heading in enumerate(headings):
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            question = text[heading.start() : end].strip()
            if question:
                extracted.append((page_number, heading.group(2), question))

    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            source_id = record_source(connection, pdf_path.name, "pdf", _checksum(pdf_path))
            for ordinal, (page_number, label, question) in enumerate(extracted, start=1):
                record_source_question(
                    connection,
                    source_id,
                    ordinal,
                    question,
                    json.dumps([], ensure_ascii=False),
                    None,
                    source_label=f"Câu {label}",
                    page=page_number,
                )
    finally:
        connection.close()
    return len(extracted)
