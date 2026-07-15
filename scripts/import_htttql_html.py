"""Import the HTTTQL inline HTML question bank into SQLite."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from scripts.storage import (
    create_database,
    get_or_create_subject,
    record_canonical_question,
    record_source,
    record_source_question,
)


DATASET_PATTERN = re.compile(r"const\s+SOURCE_QUESTIONS\s*=\s*(\[[\s\S]*?\]);")
SUBJECT_SLUG = "htttql"
SUBJECT_TITLE = "Hệ thống thông tin quản lý"


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _content_hash(question: str, choices: list[str]) -> str:
    payload = json.dumps([question, choices], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _compatible_source_kind(connection: sqlite3.Connection) -> str:
    """Use the HTML kind on new databases while tolerating older CHECK constraints."""
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'sources'"
    ).fetchone()
    return "html" if row and "'html'" in row[0] else "pdf"


def _source_questions(html: str) -> list[dict[str, Any]]:
    match = DATASET_PATTERN.search(html)
    if match is None:
        raise ValueError("Không tìm thấy biến SOURCE_QUESTIONS trong HTML.")
    payload = json.loads(match.group(1))
    if not isinstance(payload, list):
        raise ValueError("SOURCE_QUESTIONS không phải là danh sách câu hỏi.")
    return payload


def _validated_question(row: dict[str, Any]) -> dict[str, Any]:
    required = ("sourceId", "chapter", "difficulty", "type", "question", "options", "correctAnswer", "explanation")
    missing = [field for field in required if row.get(field) in (None, "")]
    if missing:
        raise ValueError(f"Câu {row.get('sourceId', '?')}: thiếu {', '.join(missing)}")
    options = row["options"]
    if not isinstance(options, list) or len(options) != 4:
        raise ValueError(f"Câu {row['sourceId']}: không có đúng 4 lựa chọn.")
    by_key = {str(option.get("key", "")).strip().upper(): str(option.get("text", "")).strip() for option in options}
    if set(by_key) != {"A", "B", "C", "D"} or any(not text for text in by_key.values()):
        raise ValueError(f"Câu {row['sourceId']}: lựa chọn A-D không hợp lệ.")
    answer = str(row["correctAnswer"]).strip().upper()
    if answer not in by_key:
        raise ValueError(f"Câu {row['sourceId']}: đáp án đúng không thuộc A-D.")
    return {
        "source_id": str(row["sourceId"]).strip(),
        "chapter": str(row["chapter"]).strip(),
        "difficulty": str(row["difficulty"]).strip(),
        "question_type": str(row["type"]).strip(),
        "question": str(row["question"]).strip(),
        "choices": [by_key[key] for key in ("A", "B", "C", "D")],
        "answer": answer,
        "explanation": str(row["explanation"]).strip(),
    }


def import_htttql_html(db_path: Path, html_path: Path) -> dict[str, int]:
    """Import the inline HTTTQL dataset and return a small count report."""
    create_database(db_path)
    questions = [_validated_question(row) for row in _source_questions(html_path.read_text(encoding="utf-8"))]
    checksum = _checksum(html_path)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        existing_source = connection.execute(
            "SELECT id FROM sources WHERE filename = ?",
            (html_path.name,),
        ).fetchone()
        if existing_source is not None:
            existing_count = connection.execute(
                "SELECT COUNT(*) FROM source_questions WHERE source_id = ?",
                (existing_source[0],),
            ).fetchone()[0]
            return {"imported": 0, "existing": int(existing_count)}

        with connection:
            subject_id = get_or_create_subject(connection, SUBJECT_SLUG, SUBJECT_TITLE)
            source_id = record_source(connection, html_path.name, _compatible_source_kind(connection), checksum)
            imported = 0
            for ordinal, question in enumerate(questions, start=1):
                choices_json = json.dumps(question["choices"], ensure_ascii=False)
                content_hash = _content_hash(question["question"], question["choices"])
                existing = connection.execute(
                    "SELECT id FROM canonical_questions WHERE content_hash = ?",
                    (content_hash,),
                ).fetchone()
                if existing is None:
                    canonical_id = record_canonical_question(
                        connection,
                        question["question"],
                        choices_json,
                        question["answer"],
                        question["explanation"],
                        question["chapter"],
                        question["difficulty"],
                        content_hash,
                        subject_id=subject_id,
                        chapter=question["chapter"],
                        question_type=question["question_type"],
                    )
                    connection.execute(
                        """
                        UPDATE canonical_questions
                        SET solution_status = 'approved', reviewed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (canonical_id,),
                    )
                    imported += 1
                else:
                    canonical_id = int(existing[0])
                record_source_question(
                    connection,
                    source_id,
                    ordinal,
                    question["question"],
                    choices_json,
                    canonical_id,
                    source_label=f"Câu {question['source_id']}",
                    subject_id=subject_id,
                    chapter=question["chapter"],
                    question_type=question["question_type"],
                )
                connection.execute(
                    """
                    UPDATE source_questions
                    SET difficulty = ?, tag_status = 'source_verified',
                        proposed_answer = ?, solution = ?,
                        answer_status = 'verified', extraction_status = 'approved'
                    WHERE source_id = ? AND ordinal = ?
                    """,
                    (
                        question["difficulty"],
                        question["answer"],
                        question["explanation"],
                        source_id,
                        ordinal,
                    ),
                )
        return {"imported": imported, "existing": 0}
    finally:
        connection.close()


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Import HTTTQL questions from an inline SOURCE_QUESTIONS HTML file.")
    parser.add_argument(
        "html_path",
        nargs="?",
        type=Path,
        default=Path(r"F:\Downloads\HTTTQL_30_BO_DE_40_CAU_NANG_CAP.html"),
        help="Path to the HTTTQL HTML export.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=root / "data" / "review.db",
        help="SQLite review database to update.",
    )
    args = parser.parse_args()
    report = import_htttql_html(args.db, args.html_path)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
