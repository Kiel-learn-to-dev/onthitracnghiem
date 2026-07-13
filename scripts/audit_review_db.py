"""Validate the question-bank invariants required by the future quiz app."""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path


VALID_ANSWERS = {"A", "B", "C", "D"}
VALID_DIFFICULTIES = {"Dễ", "Vừa", "Khó", "Rất khó"}


def audit(db_path: Path) -> dict[str, list[int]]:
    """Return question ids that violate each quiz-bank invariant."""
    failures: dict[str, list[int]] = {
        "empty_question": [],
        "not_four_choices": [],
        "empty_choice": [],
        "missing_answer": [],
        "missing_difficulty": [],
        "missing_solution": [],
    }
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        for row in connection.execute("SELECT * FROM source_questions ORDER BY id"):
            question_id = row["id"]
            if not (row["raw_question"] or "").strip():
                failures["empty_question"].append(question_id)
            try:
                choices = json.loads(row["raw_choices_json"] or "")
            except json.JSONDecodeError:
                choices = None
            if not isinstance(choices, list) or len(choices) != 4:
                failures["not_four_choices"].append(question_id)
            elif any(not isinstance(choice, str) or not choice.strip() for choice in choices):
                failures["empty_choice"].append(question_id)
            if row["proposed_answer"] not in VALID_ANSWERS:
                failures["missing_answer"].append(question_id)
            if row["difficulty"] not in VALID_DIFFICULTIES:
                failures["missing_difficulty"].append(question_id)
            if not (row["solution"] or "").strip():
                failures["missing_solution"].append(question_id)
    finally:
        connection.close()
    return failures


def main() -> int:
    db_path = Path(__file__).resolve().parent.parent / "data" / "review.db"
    failures = audit(db_path)
    total = sum(len(ids) for ids in failures.values())
    print("questions:", sum(1 for _ in sqlite3.connect(db_path).execute("SELECT 1 FROM source_questions")))
    for name, ids in failures.items():
        print(f"{name}: {len(ids)}" + (f"; ids={ids}" if ids else ""))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
