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
HTTTQL_SAMPLE_COUNTS = {"Dễ": 4, "Vừa": 8, "Khó": 16, "Rất khó": 12}


class InsufficientPoolError(ValueError):
    """Raised when an approved pool cannot honor the published blueprint."""


@dataclass(frozen=True)
class ExamInstance:
    id: str
    seed: str
    question_ids: list[int]
    counts_by_difficulty: dict[str, int]


def _blueprint_id(
    connection: sqlite3.Connection,
    *,
    slug: str = "standard-40",
    title: str = "Đề chuẩn 40 câu",
    counts: dict[str, int] | None = None,
) -> int:
    blueprint_counts = counts or BLUEPRINT_COUNTS
    connection.execute(
        """
        INSERT OR IGNORE INTO exam_blueprints
        (slug, title, easy_count, medium_count, hard_count, very_hard_count)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            slug,
            title,
            blueprint_counts.get("Dễ", 0),
            blueprint_counts.get("Vừa", 0),
            blueprint_counts.get("Khó", 0),
            blueprint_counts.get("Rất khó", 0),
        ),
    )
    row = connection.execute("SELECT id FROM exam_blueprints WHERE slug = ?", (slug,)).fetchone()
    assert row is not None
    return int(row[0])


def _subject_id(connection: sqlite3.Connection, slug: str) -> int:
    row = connection.execute("SELECT id FROM subjects WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise InsufficientPoolError(f"Không tìm thấy môn học {slug}")
    return int(row["id"])


def _approved_questions(connection: sqlite3.Connection, difficulty: str, subject_id: int = 1) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT id, question, choices_json, answer, explanation, topic, chapter, question_type, difficulty, assumptions
            FROM canonical_questions
            WHERE solution_status = 'approved' AND is_publishable = 1 AND difficulty = ? AND subject_id = ?
            ORDER BY id
            """,
            (difficulty, subject_id),
        )
    )


def _select_questions(
    connection: sqlite3.Connection,
    seed: str,
    excluded_ids: set[int] | None = None,
    subject_slug: str = "cslt",
    counts: dict[str, int] | None = None,
) -> list[sqlite3.Row]:
    rng = random.Random(seed)
    selected: list[sqlite3.Row] = []
    topic_counts: Counter[str] = Counter()
    excluded = excluded_ids or set()
    subject_id = _subject_id(connection, subject_slug)
    blueprint_counts = counts or BLUEPRINT_COUNTS
    max_per_topic = 14
    for difficulty, needed in blueprint_counts.items():
        candidates = [row for row in _approved_questions(connection, difficulty, subject_id) if row["id"] not in excluded]
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

    if len({row["id"] for row in selected}) != sum(blueprint_counts.values()):
        raise RuntimeError("Bộ tạo đề chọn trùng canonical id")
    if len(topic_counts) < 5:
        raise InsufficientPoolError("Không đủ 5 chủ đề trong pool approved")
    return selected


def _custom_approved_questions(
    connection: sqlite3.Connection,
    subject_slug: str,
    *,
    chapters: list[str] | None = None,
    topics: list[str] | None = None,
    difficulties: list[str] | None = None,
    question_types: list[str] | None = None,
    excluded_ids: set[int] | None = None,
) -> list[sqlite3.Row]:
    subject_id = _subject_id(connection, subject_slug)
    clauses = ["subject_id = ?", "solution_status = 'approved'", "is_publishable = 1"]
    params: list[Any] = [subject_id]
    filters = (
        ("chapter", chapters),
        ("topic", topics),
        ("difficulty", difficulties),
        ("question_type", question_types),
    )
    for column, values in filters:
        if values:
            placeholders = ", ".join("?" for _ in values)
            clauses.append(f"{column} IN ({placeholders})")
            params.extend(values)
    if excluded_ids:
        placeholders = ", ".join("?" for _ in excluded_ids)
        clauses.append(f"id NOT IN ({placeholders})")
        params.extend(excluded_ids)
    return list(
        connection.execute(
            f"""
            SELECT id, question, choices_json, answer, explanation, topic, chapter, question_type, difficulty, assumptions
            FROM canonical_questions
            WHERE {' AND '.join(clauses)}
            ORDER BY id
            """,
            params,
        )
    )


def _select_custom_questions(
    connection: sqlite3.Connection,
    seed: str,
    subject_slug: str,
    question_count: int,
    *,
    chapters: list[str] | None = None,
    topics: list[str] | None = None,
    difficulties: list[str] | None = None,
    question_types: list[str] | None = None,
    excluded_ids: set[int] | None = None,
) -> list[sqlite3.Row]:
    candidates = _custom_approved_questions(
        connection,
        subject_slug,
        chapters=chapters,
        topics=topics,
        difficulties=difficulties,
        question_types=question_types,
        excluded_ids=excluded_ids,
    )
    if len(candidates) < question_count:
        raise InsufficientPoolError(f"Thiếu {question_count - len(candidates)} câu phù hợp với cấu hình đã chọn")
    rng = random.Random(seed)
    rng.shuffle(candidates)
    return candidates[:question_count]


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
        "chapter": row["chapter"],
        "questionType": row["question_type"],
        "difficulty": row["difficulty"],
        "assumptions": row["assumptions"],
    }


def create_exam_instance(
    db_path: Path,
    seed: str,
    *,
    status: str = "draft",
    excluded_ids: set[int] | None = None,
    subject_slug: str = "cslt",
    question_count: int | None = None,
    chapters: list[str] | None = None,
    topics: list[str] | None = None,
    difficulties: list[str] | None = None,
    question_types: list[str] | None = None,
    title: str | None = None,
    blueprint_counts: dict[str, int] | None = None,
    blueprint_slug: str = "standard-40",
    blueprint_title: str = "Đề chuẩn 40 câu",
) -> ExamInstance:
    """Create and persist a 12/8/8/12 exam from approved questions only."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        subject_id = _subject_id(connection, subject_slug)
        if blueprint_counts is not None or (
            question_count is None and subject_slug == "cslt" and not any((chapters, topics, difficulties, question_types))
        ):
            selected = _select_questions(connection, seed, excluded_ids, subject_slug, blueprint_counts)
        else:
            selected = _select_custom_questions(
                connection,
                seed,
                subject_slug,
                question_count or sum(BLUEPRINT_COUNTS.values()),
                chapters=chapters,
                topics=topics,
                difficulties=difficulties,
                question_types=question_types,
                excluded_ids=excluded_ids,
            )
        rng = random.Random(f"{seed}:presentation")
        rng.shuffle(selected)
        instance_id = str(uuid.uuid4())
        blueprint_id = _blueprint_id(
            connection,
            slug=blueprint_slug,
            title=blueprint_title,
            counts=blueprint_counts or BLUEPRINT_COUNTS,
        )
        source_kind = "published" if status == "published" else "random"
        connection.execute(
            """
            INSERT INTO exam_instances (id, blueprint_id, subject_id, seed, source_kind, title, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (instance_id, blueprint_id, subject_id, seed, source_kind, title, status),
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


def _load_published_exam_by_seed(connection: sqlite3.Connection, seed: str) -> ExamInstance | None:
    row = connection.execute(
        """
        SELECT id, seed
        FROM exam_instances
        WHERE seed = ? AND status = 'published'
        """,
        (seed,),
    ).fetchone()
    if row is None:
        return None
    question_rows = connection.execute(
        """
        SELECT canonical.id, canonical.difficulty
        FROM exam_instance_questions AS exam_question
        JOIN canonical_questions AS canonical ON canonical.id = exam_question.canonical_id
        WHERE exam_question.exam_instance_id = ?
        ORDER BY exam_question.position
        """,
        (row["id"],),
    ).fetchall()
    return ExamInstance(
        id=row["id"],
        seed=row["seed"],
        question_ids=[int(question["id"]) for question in question_rows],
        counts_by_difficulty=dict(Counter(question["difficulty"] for question in question_rows)),
    )


def publish_htttql_sample_exams(
    db_path: Path,
    count: int = 10,
    seed_prefix: str = "htttql-sample",
    *,
    allow_cross_exam_reuse: bool = False,
) -> list[ExamInstance]:
    """Publish the 40-question HTTTQL sample set with a 4/8/16/12 mix."""
    if count < 1:
        raise ValueError("Số đề cần publish phải lớn hơn 0")
    existing: list[ExamInstance] = []
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        for index in range(1, count + 1):
            exam = _load_published_exam_by_seed(connection, f"{seed_prefix}-{index}")
            if exam is not None:
                existing.append(exam)
    finally:
        connection.close()
    if len(existing) == count:
        return existing

    published: list[ExamInstance] = list(existing)
    used_ids = {question_id for exam in existing for question_id in exam.question_ids}
    for index in range(len(existing) + 1, count + 1):
        exam = create_exam_instance(
            db_path,
            f"{seed_prefix}-{index}",
            status="published",
            excluded_ids=None if allow_cross_exam_reuse else used_ids,
            subject_slug="htttql",
            title=f"HTTTQL Đề {index:02}",
            blueprint_counts=HTTTQL_SAMPLE_COUNTS,
            blueprint_slug="htttql-standard-40",
            blueprint_title="HTTTQL 40 câu",
        )
        published.append(exam)
        used_ids.update(exam.question_ids)
    return published
