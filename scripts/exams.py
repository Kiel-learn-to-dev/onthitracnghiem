"""Deterministic exam generation and SQLite persistence."""

from __future__ import annotations

import json
import random
import sqlite3
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BLUEPRINT_COUNTS = {"Dễ": 12, "Vừa": 8, "Khó": 8, "Rất khó": 12}


class InsufficientPoolError(ValueError):
    """Raised when an approved pool cannot honor the published blueprint."""


@dataclass(frozen=True)
class ExamInstance:
    id: str
    seed: str
    question_ids: list[int]
    counts_by_difficulty: dict[str, int]


def _blueprint_id(connection: sqlite3.Connection) -> int:
    connection.execute(
        """
        INSERT OR IGNORE INTO exam_blueprints (slug, title)
        VALUES ('standard-40', 'Đề chuẩn 40 câu')
        """
    )
    row = connection.execute(
        "SELECT id FROM exam_blueprints WHERE slug = 'standard-40'"
    ).fetchone()
    assert row is not None
    return int(row[0])


def _approved_questions(connection: sqlite3.Connection, difficulty: str) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT id, question, choices_json, answer, explanation, topic, difficulty, assumptions
            FROM canonical_questions
            WHERE solution_status = 'approved' AND is_publishable = 1 AND difficulty = ?
            ORDER BY id
            """,
            (difficulty,),
        )
    )


def _select_questions(
    connection: sqlite3.Connection, seed: str, excluded_ids: set[int] | None = None
) -> list[sqlite3.Row]:
    rng = random.Random(seed)
    selected: list[sqlite3.Row] = []
    topic_counts: Counter[str] = Counter()
    excluded = excluded_ids or set()
    max_per_topic = 14
    for difficulty, needed in BLUEPRINT_COUNTS.items():
        candidates = [row for row in _approved_questions(connection, difficulty) if row["id"] not in excluded]
        if len(candidates) < needed:
            raise InsufficientPoolError(f"{difficulty}: thiếu {needed - len(candidates)} câu approved")
        rng.shuffle(candidates)
        bucket: list[sqlite3.Row] = []
        for row in candidates:
            if topic_counts[row["topic"]] >= max_per_topic:
                continue
            bucket.append(row)
            topic_counts[row["topic"]] += 1
            if len(bucket) == needed:
                break
        if len(bucket) < needed:
            raise InsufficientPoolError(f"{difficulty}: không thể giữ giới hạn {max_per_topic} câu mỗi chủ đề")
        selected.extend(bucket)

    if len({row["id"] for row in selected}) != sum(BLUEPRINT_COUNTS.values()):
        raise RuntimeError("Bộ tạo đề chọn trùng canonical id")
    if len(topic_counts) < 5:
        raise InsufficientPoolError("Không đủ 5 chủ đề trong pool approved")
    return selected


def _snapshot(row: sqlite3.Row, rng: random.Random) -> dict[str, Any]:
    choices = list(json.loads(row["choices_json"]))
    if len(choices) != 4:
        raise ValueError(f"Canonical question {row['id']} không có đúng bốn lựa chọn")
    indexed_choices = list(zip(("A", "B", "C", "D"), choices, strict=True))
    rng.shuffle(indexed_choices)
    answer = row["answer"]
    correct_index = next(index for index, (label, _) in enumerate(indexed_choices) if label == answer)
    return {
        "canonicalId": row["id"],
        "question": row["question"],
        "choices": [choice for _, choice in indexed_choices],
        "correctAnswer": "ABCD"[correct_index],
        "explanation": row["explanation"],
        "topic": row["topic"],
        "difficulty": row["difficulty"],
        "assumptions": row["assumptions"],
    }


def create_exam_instance(
    db_path: Path, seed: str, *, status: str = "draft", excluded_ids: set[int] | None = None
) -> ExamInstance:
    """Create and persist a 12/8/8/12 exam from approved questions only."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        selected = _select_questions(connection, seed, excluded_ids)
        rng = random.Random(f"{seed}:presentation")
        rng.shuffle(selected)
        instance_id = str(uuid.uuid4())
        blueprint_id = _blueprint_id(connection)
        connection.execute(
            "INSERT INTO exam_instances (id, blueprint_id, seed, status) VALUES (?, ?, ?, ?)",
            (instance_id, blueprint_id, seed, status),
        )
        for position, row in enumerate(selected, start=1):
            connection.execute(
                """
                INSERT INTO exam_instance_questions
                (exam_instance_id, position, canonical_id, snapshot_json)
                VALUES (?, ?, ?, ?)
                """,
                (instance_id, position, row["id"], json.dumps(_snapshot(row, rng), ensure_ascii=False)),
            )
        connection.commit()
        return ExamInstance(
            id=instance_id,
            seed=seed,
            question_ids=[int(row["id"]) for row in selected],
            counts_by_difficulty=dict(Counter(row["difficulty"] for row in selected)),
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def refresh_exam_snapshots(db_path: Path) -> int:
    """Update display stems in existing exams after the question bank is curated.

    Choice order and correct-answer positions remain frozen in each snapshot;
    only the question text is refreshed from the canonical record.
    """
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT exam_instance_id, position, snapshot_json, canonical.question
            FROM exam_instance_questions AS exam_question
            JOIN canonical_questions AS canonical ON canonical.id = exam_question.canonical_id
            """
        ).fetchall()
        with connection:
            for row in rows:
                snapshot = json.loads(row["snapshot_json"])
                snapshot["question"] = row["question"]
                connection.execute(
                    """
                    UPDATE exam_instance_questions
                    SET snapshot_json = ?
                    WHERE exam_instance_id = ? AND position = ?
                    """,
                    (json.dumps(snapshot, ensure_ascii=False), row["exam_instance_id"], row["position"]),
                )
        return len(rows)
    finally:
        connection.close()


def publish_standard_exams(
    db_path: Path,
    count: int = 10,
    seed_prefix: str = "published",
    *,
    allow_cross_exam_reuse: bool = False,
) -> list[ExamInstance]:
    """Publish standard exams, optionally reusing questions only across separate exams."""
    if count < 1:
        raise ValueError("Số đề cần publish phải lớn hơn 0")
    published: list[ExamInstance] = []
    used_ids: set[int] = set()
    for index in range(1, count + 1):
        exam = create_exam_instance(
            db_path,
            f"{seed_prefix}-{index}",
            status="published",
            excluded_ids=None if allow_cross_exam_reuse else used_ids,
        )
        published.append(exam)
        used_ids.update(exam.question_ids)
    return published
