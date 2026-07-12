"""Populate answers explicitly available in imported sources; never mark them verified."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts.import_scanned_pdf import extract_ocr_answer
from scripts.storage import create_database


ROOT = Path(__file__).resolve().parent.parent


def seed_available_answers(db_path: Path) -> dict[str, int]:
    create_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        with connection:
            excel = connection.execute(
                """
                UPDATE source_questions
                SET proposed_answer = canonical_questions.answer,
                    solution = canonical_questions.explanation,
                    answer_status = 'extracted',
                    answer_reason = 'Đáp án và lời giải có trong workbook nguồn.'
                FROM canonical_questions
                WHERE source_questions.canonical_id = canonical_questions.id
                """
            ).rowcount
            scanned_rows = connection.execute(
                """
                SELECT source_questions.id, source_questions.raw_question
                FROM source_questions JOIN sources ON sources.id = source_questions.source_id
                WHERE sources.filename LIKE 'C%' AND source_questions.proposed_answer IS NULL
                """
            ).fetchall()
            scanned = 0
            for source_id, raw_question in scanned_rows:
                answer = extract_ocr_answer(raw_question)
                if answer:
                    connection.execute(
                        """
                        UPDATE source_questions
                        SET proposed_answer = ?, answer_status = 'extracted',
                            answer_reason = 'Đáp án được trích từ cột đáp án của PDF quét; cần đối chiếu.'
                        WHERE id = ?
                        """,
                        (answer, source_id),
                    )
                    scanned += 1
        return {"excel": excel, "scanned": scanned}
    finally:
        connection.close()


if __name__ == "__main__":
    print(seed_available_answers(ROOT / "data" / "review.db"))
