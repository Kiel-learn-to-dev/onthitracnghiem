"""Apply auditable difficulty tags to every imported source question."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts.storage import create_database
from scripts.tagging import classify_question


ROOT = Path(__file__).resolve().parent.parent


def apply_tags(db_path: Path) -> dict[str, int]:
    create_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            """
            SELECT source_questions.id, source_questions.raw_question, sources.filename,
                   canonical_questions.difficulty
            FROM source_questions
            JOIN sources ON sources.id = source_questions.source_id
            LEFT JOIN canonical_questions ON canonical_questions.id = source_questions.canonical_id
            ORDER BY source_questions.id
            """
        ).fetchall()
        counts: dict[str, int] = {"Dễ": 0, "Vừa": 0, "Khó": 0, "Rất khó": 0}
        with connection:
            for source_id, question, filename, existing_difficulty in rows:
                result = classify_question(question, filename, existing_difficulty)
                connection.execute(
                    """
                    UPDATE source_questions
                    SET difficulty = ?, tag_status = ?, tag_reason = ?
                    WHERE id = ?
                    """,
                    (result.difficulty, result.status, result.reason, source_id),
                )
                counts[result.difficulty] += 1
        return counts
    finally:
        connection.close()


if __name__ == "__main__":
    print(apply_tags(ROOT / "data" / "review.db"))
