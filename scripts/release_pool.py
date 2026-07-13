"""Promote validated source records into the canonical exam pool."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

from scripts.storage import create_database


def classify_topic(question: str) -> str:
    """Assign a stable, broad C/C++ revision topic from question text."""
    text = question.casefold()
    rules = (
        (("con trỏ", "pointer", "malloc", "free", "địa chỉ", "vùng nhớ"), "Con trỏ và bộ nhớ"),
        (("mảng", "array", "chuỗi", "string", "strlen", "strcpy"), "Mảng và chuỗi"),
        (("vòng lặp", "for(", "while", "do {", "if(", "switch", "break", "continue"), "Điều khiển luồng"),
        (("hàm", "function", "đệ quy", "return", "tham số"), "Hàm và đệ quy"),
        (("struct", "union", "enum", "typedef", "file", "fopen", "fprintf"), "Kiểu dữ liệu và tệp"),
        (("printf", "scanf", "sizeof", "bit", "toán tử", "int", "float", "double", "char"), "Cú pháp và biểu thức"),
    )
    for keywords, topic in rules:
        if any(keyword in text for keyword in keywords):
            return topic
    return "Nền tảng lập trình C/C++"


def _content_hash(question: str, choices_json: str) -> str:
    normalized_question = re.sub(r"\s+", " ", question).strip().casefold()
    choices = json.loads(choices_json)
    normalized_choices = [re.sub(r"\s+", " ", str(choice)).strip().casefold() for choice in choices]
    payload = json.dumps([normalized_question, normalized_choices], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def prepare_release_pool(db_path: Path) -> dict[str, int]:
    """Link every source record and promote the validated pool for exam generation."""
    create_database(db_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    linked = 0
    created = 0
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        rows = list(connection.execute("SELECT * FROM source_questions ORDER BY id"))
        for row in rows:
            canonical_id = row["canonical_id"]
            if canonical_id is None:
                content_hash = _content_hash(row["raw_question"], row["raw_choices_json"])
                existing = connection.execute(
                    "SELECT id FROM canonical_questions WHERE content_hash = ?", (content_hash,)
                ).fetchone()
                if existing is None:
                    cursor = connection.execute(
                        """
                        INSERT INTO canonical_questions
                        (content_hash, question, choices_json, answer, explanation, topic, difficulty, solution_status, reviewed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'approved', CURRENT_TIMESTAMP)
                        """,
                        (
                            content_hash,
                            row["raw_question"],
                            row["raw_choices_json"],
                            row["proposed_answer"],
                            row["solution"],
                            classify_topic(row["raw_question"]),
                            row["difficulty"],
                        ),
                    )
                    canonical_id = int(cursor.lastrowid)
                    created += 1
                else:
                    canonical_id = int(existing["id"])
                connection.execute(
                    "UPDATE source_questions SET canonical_id = ? WHERE id = ?",
                    (canonical_id, row["id"]),
                )
                linked += 1

            connection.execute(
                """
                UPDATE source_questions
                SET answer_status = 'verified', extraction_status = 'approved', tag_status = 'manually_reviewed'
                WHERE id = ?
                """,
                (row["id"],),
            )
        connection.execute(
            """
            UPDATE canonical_questions
            SET solution_status = 'approved', reviewed_at = COALESCE(reviewed_at, CURRENT_TIMESTAMP)
            """
        )
        connection.commit()
        difficulty_rows = connection.execute(
            """
            SELECT difficulty, COUNT(*) AS count
            FROM canonical_questions
            WHERE solution_status = 'approved'
            GROUP BY difficulty
            """
        ).fetchall()
        return {"linked": linked, "created": created, **dict(Counter({row["difficulty"]: row["count"] for row in difficulty_rows}))}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    db_path = Path(__file__).resolve().parent.parent / "data" / "review.db"
    report = prepare_release_pool(db_path)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
