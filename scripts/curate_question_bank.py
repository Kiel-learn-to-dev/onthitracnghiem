"""Normalize display text and keep unverified OCR out of the release pool."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from scripts.question_cleaning import clean_choice_text, clean_question_text, is_safe_for_release
from scripts.storage import create_database


OCR_SOURCE = "Câu hỏi ôn tập-e.pdf"


def curate_question_bank(db_path: Path) -> dict[str, int]:
    """Remove source labels and exclude corrupted/unverified OCR from generated exams."""
    create_database(db_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    normalized = 0
    excluded = 0
    try:
        rows = connection.execute(
            """
            SELECT canonical.id, canonical.question, canonical.choices_json, source.filename
            FROM canonical_questions AS canonical
            JOIN source_questions AS source_question ON source_question.canonical_id = canonical.id
            JOIN sources AS source ON source.id = source_question.source_id
            ORDER BY canonical.id
            """
        ).fetchall()
        for row in rows:
            question = clean_question_text(row["question"])
            choices = [clean_choice_text(choice) for choice in json.loads(row["choices_json"])]
            safe = (
                row["filename"] != OCR_SOURCE
                and is_safe_for_release(question)
                and all(is_safe_for_release(choice) for choice in choices)
            )
            connection.execute(
                """
                UPDATE canonical_questions
                SET question = ?, choices_json = ?, is_publishable = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (question, json.dumps(choices, ensure_ascii=False), int(safe), row["id"]),
            )
            normalized += 1
            if not safe:
                excluded += 1
                connection.execute(
                    """
                    INSERT INTO review_queue (canonical_id, reason)
                    SELECT ?, 'OCR hoặc ký tự hỏng cần đối chiếu tài liệu gốc'
                    WHERE NOT EXISTS (
                        SELECT 1 FROM review_queue
                        WHERE canonical_id = ? AND status = 'open'
                    )
                    """,
                    (row["id"], row["id"]),
                )
        connection.commit()
        return {"normalized": normalized, "excluded": excluded}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    print(curate_question_bank(root / "data" / "review.db"))


if __name__ == "__main__":
    main()
