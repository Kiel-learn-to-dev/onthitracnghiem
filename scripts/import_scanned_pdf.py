"""OCR the scanned question bank and store source-level question occurrences."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

from scripts.storage import record_source


ROOT = Path(__file__).resolve().parent.parent
OCR_DEPENDENCIES = ROOT / ".tools" / "ocr"
QUESTION_START = re.compile(r"\bcau(?:\s*hoi)?\s*([0-9oOIl]+)\s*[.:]", re.IGNORECASE)
OCR_DIGITS = str.maketrans({"o": "0", "O": "0", "i": "1", "I": "1", "l": "1"})


def _ascii(text: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    ).replace("đ", "d").replace("Đ", "D")


def split_ocr_questions(lines: list[str]) -> list[tuple[int, str]]:
    """Split OCR lines at detected question headings while preserving raw evidence."""
    results: list[tuple[int, str]] = []
    current_number: int | None = None
    current_lines: list[str] = []
    for line in lines:
        match = QUESTION_START.search(_ascii(line))
        if match:
            if current_number is not None:
                results.append((current_number, "\n".join(current_lines).strip()))
            current_number = int(match.group(1).translate(OCR_DIGITS))
            current_lines = [line]
        elif current_number is not None:
            current_lines.append(line)
    if current_number is not None:
        results.append((current_number, "\n".join(current_lines).strip()))
    return results


def extract_ocr_answer(raw_question: str) -> str | None:
    """Read the separate A-D answer cell emitted by the scanned-table OCR."""
    for line in raw_question.splitlines()[1:4]:
        marker = line.strip().upper()
        if marker in {"A", "B", "C", "D"}:
            return marker
    return None


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _page_number(image_path: Path) -> int:
    match = re.search(r"_p(\d+)\.png$", image_path.name)
    if not match:
        raise ValueError(f"Không đọc được số trang từ {image_path.name}")
    return int(match.group(1))


def _ocr_lines(image_path: Path) -> list[str]:
    sys.path.insert(0, str(OCR_DEPENDENCIES))
    import cv2
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR

    image = cv2.imdecode(np.frombuffer(image_path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Không mở được ảnh {image_path}")
    rotated = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    result, _ = RapidOCR()(rotated)
    return [item[1] for item in result or []]


def import_scanned_pdf(db_path: Path, start_page: int = 1, end_page: int = 40) -> int:
    """OCR a page range; each extracted row is retained as needs_review evidence."""
    image_paths = sorted(
        (path for path in (ROOT / "pdf_images").glob("C*.png") if start_page <= _page_number(path) <= end_page),
        key=_page_number,
    )
    pdf_path = ROOT / "Câu hỏi ôn tập-e.pdf"
    connection = sqlite3.connect(db_path)
    inserted = 0
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        source_row = connection.execute(
            "SELECT id FROM sources WHERE filename = ?", (pdf_path.name,)
        ).fetchone()
        source_id = int(source_row[0]) if source_row else record_source(
            connection, pdf_path.name, "pdf", _checksum(pdf_path)
        )
        with connection:
            for image_path in image_paths:
                page = _page_number(image_path)
                for number, raw_question in split_ocr_questions(_ocr_lines(image_path)):
                    cursor = connection.execute(
                        """
                        INSERT OR IGNORE INTO source_questions
                        (source_id, source_label, page, ordinal, raw_question, raw_choices_json, extraction_status)
                        VALUES (?, ?, ?, ?, ?, ?, 'needs_review')
                        """,
                        (
                            source_id,
                            f"Câu hỏi {number}",
                            page,
                            number,
                            raw_question,
                            json.dumps([], ensure_ascii=False),
                        ),
                    )
                    inserted += cursor.rowcount
    finally:
        connection.close()
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--end-page", type=int, default=40)
    args = parser.parse_args()
    count = import_scanned_pdf(ROOT / "data" / "review.db", args.start_page, args.end_page)
    print(f"Đã thêm {count} câu OCR.")


if __name__ == "__main__":
    main()
