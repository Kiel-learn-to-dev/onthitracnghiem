"""Normalize source questions without discarding their original text evidence."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from scripts.choice_parser import extract_question_stem, parse_question_choices
from scripts.storage import create_database


ROOT = Path(__file__).resolve().parent.parent


def normalize_choices(db_path: Path) -> dict[str, int]:
    """Populate separated choices and a display-ready question stem when certain."""
    create_database(db_path)
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "SELECT id, raw_question, raw_choices_json FROM source_questions ORDER BY id"
        ).fetchall()
        results = {"normalized": 0, "already_complete": 0, "needs_review": 0}
        with connection:
            for source_id, raw_question, choices_json in rows:
                choices = json.loads(choices_json)
                if len(choices) == 4 and all(isinstance(choice, str) and choice.strip() for choice in choices):
                    connection.execute(
                        """
                        UPDATE source_questions
                        SET normalized_question = ?,
                            choice_parse_reason = NULL
                        WHERE id = ?
                        """,
                        (extract_question_stem(raw_question), source_id),
                    )
                    results["already_complete"] += 1
                    continue

                parsed = parse_question_choices(raw_question)
                if parsed.is_complete:
                    connection.execute(
                        """
                        UPDATE source_questions
                        SET normalized_question = ?, raw_choices_json = ?, choice_parse_reason = NULL
                        WHERE id = ?
                        """,
                        (parsed.question, json.dumps(parsed.choices, ensure_ascii=False), source_id),
                    )
                    results["normalized"] += 1
                else:
                    connection.execute(
                        "UPDATE source_questions SET choice_parse_reason = ? WHERE id = ?",
                        (parsed.reason, source_id),
                    )
                    results["needs_review"] += 1
        return results
    finally:
        connection.close()


def main() -> None:
    database = ROOT / "data" / "review.db"
    print("Choices:", normalize_choices(database))


if __name__ == "__main__":
    main()
