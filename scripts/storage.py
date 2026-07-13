"""SQLite storage for the programming-fundamentals review bank."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK (kind IN ('xlsx', 'pdf')),
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    checksum TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS canonical_questions (
    id INTEGER PRIMARY KEY,
    content_hash TEXT UNIQUE,
    question TEXT NOT NULL,
    choices_json TEXT NOT NULL,
    answer TEXT NOT NULL CHECK (answer IN ('A', 'B', 'C', 'D')),
    explanation TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('Dễ', 'Vừa', 'Khó', 'Rất khó')),
    assumptions TEXT,
    solution_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (solution_status IN ('pending', 'drafted', 'reviewed', 'approved')),
    is_publishable INTEGER NOT NULL DEFAULT 1 CHECK (is_publishable IN (0, 1)),
    reviewed_at TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_questions (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    source_label TEXT NOT NULL,
    page INTEGER,
    ordinal INTEGER NOT NULL,
    raw_question TEXT NOT NULL,
    raw_choices_json TEXT NOT NULL,
    normalized_question TEXT,
    choice_parse_reason TEXT,
    canonical_id INTEGER REFERENCES canonical_questions(id),
    difficulty TEXT CHECK (difficulty IN ('Dễ', 'Vừa', 'Khó', 'Rất khó')),
    tag_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (tag_status IN ('pending', 'source_verified', 'rule_based', 'manually_reviewed')),
    tag_reason TEXT,
    proposed_answer TEXT CHECK (proposed_answer IN ('A', 'B', 'C', 'D')),
    solution TEXT,
    answer_status TEXT NOT NULL DEFAULT 'missing'
        CHECK (answer_status IN ('missing', 'extracted', 'solved', 'verified', 'needs_review')),
    answer_reason TEXT,
    extraction_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (extraction_status IN ('pending', 'extracted', 'needs_review', 'approved')),
    UNIQUE(source_id, ordinal)
);

CREATE TABLE IF NOT EXISTS solution_audit (
    id INTEGER PRIMARY KEY,
    canonical_id INTEGER NOT NULL REFERENCES canonical_questions(id),
    action TEXT NOT NULL,
    before_json TEXT,
    after_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_source_questions_canonical
    ON source_questions(canonical_id);
CREATE INDEX IF NOT EXISTS idx_canonical_questions_status_difficulty
    ON canonical_questions(solution_status, difficulty);

CREATE TABLE IF NOT EXISTS exam_blueprints (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    easy_count INTEGER NOT NULL DEFAULT 12 CHECK (easy_count >= 0),
    medium_count INTEGER NOT NULL DEFAULT 8 CHECK (medium_count >= 0),
    hard_count INTEGER NOT NULL DEFAULT 8 CHECK (hard_count >= 0),
    very_hard_count INTEGER NOT NULL DEFAULT 12 CHECK (very_hard_count >= 0),
    min_topics INTEGER NOT NULL DEFAULT 5 CHECK (min_topics >= 1),
    max_topic_share REAL NOT NULL DEFAULT 0.35 CHECK (max_topic_share > 0 AND max_topic_share <= 1),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exam_instances (
    id TEXT PRIMARY KEY,
    blueprint_id INTEGER NOT NULL REFERENCES exam_blueprints(id),
    seed TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exam_instance_questions (
    exam_instance_id TEXT NOT NULL REFERENCES exam_instances(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 1),
    canonical_id INTEGER NOT NULL REFERENCES canonical_questions(id),
    snapshot_json TEXT NOT NULL,
    PRIMARY KEY (exam_instance_id, position),
    UNIQUE (exam_instance_id, canonical_id)
);

CREATE TABLE IF NOT EXISTS attempts (
    id TEXT PRIMARY KEY,
    exam_instance_id TEXT NOT NULL REFERENCES exam_instances(id),
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'submitted')),
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    submitted_at TEXT,
    score INTEGER,
    total_questions INTEGER NOT NULL,
    time_limit_seconds INTEGER NOT NULL DEFAULT 1800 CHECK (time_limit_seconds > 0),
    deadline_at TEXT
);

CREATE TABLE IF NOT EXISTS attempt_answers (
    attempt_id TEXT NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 1),
    selected_answer TEXT CHECK (selected_answer IN ('A', 'B', 'C', 'D')),
    marked_for_review INTEGER NOT NULL DEFAULT 0 CHECK (marked_for_review IN (0, 1)),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (attempt_id, position)
);

CREATE TABLE IF NOT EXISTS review_queue (
    id INTEGER PRIMARY KEY,
    canonical_id INTEGER REFERENCES canonical_questions(id),
    source_question_id INTEGER REFERENCES source_questions(id),
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_exam_instance_questions_canonical
    ON exam_instance_questions(canonical_id);
CREATE INDEX IF NOT EXISTS idx_attempts_exam_instance
    ON attempts(exam_instance_id);
CREATE INDEX IF NOT EXISTS idx_review_queue_status
    ON review_queue(status);
"""


def create_database(db_path: Path) -> None:
    """Create or upgrade the local review database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(SCHEMA)
        _add_source_question_columns(connection)
        _add_canonical_question_columns(connection)
        _add_attempt_columns(connection)
        # ``ALTER TABLE`` upgrades run inside an implicit transaction.  Commit
        # them before closing so installed copies of an older database retain
        # their upgraded columns on the next application launch.
        connection.commit()
    finally:
        connection.close()


def _add_source_question_columns(connection: sqlite3.Connection) -> None:
    """Upgrade older local databases without rebuilding imported source data."""
    columns = {row[1] for row in connection.execute("PRAGMA table_info(source_questions)")}
    migrations = {
        "difficulty": "ALTER TABLE source_questions ADD COLUMN difficulty TEXT "
        "CHECK (difficulty IN ('Dễ', 'Vừa', 'Khó', 'Rất khó'))",
        "tag_status": "ALTER TABLE source_questions ADD COLUMN tag_status TEXT NOT NULL "
        "DEFAULT 'pending' CHECK (tag_status IN "
        "('pending', 'source_verified', 'rule_based', 'manually_reviewed'))",
        "tag_reason": "ALTER TABLE source_questions ADD COLUMN tag_reason TEXT",
        "proposed_answer": "ALTER TABLE source_questions ADD COLUMN proposed_answer TEXT "
        "CHECK (proposed_answer IN ('A', 'B', 'C', 'D'))",
        "solution": "ALTER TABLE source_questions ADD COLUMN solution TEXT",
        "answer_status": "ALTER TABLE source_questions ADD COLUMN answer_status TEXT NOT NULL "
        "DEFAULT 'missing' CHECK (answer_status IN "
        "('missing', 'extracted', 'solved', 'verified', 'needs_review'))",
        "answer_reason": "ALTER TABLE source_questions ADD COLUMN answer_reason TEXT",
        "normalized_question": "ALTER TABLE source_questions ADD COLUMN normalized_question TEXT",
        "choice_parse_reason": "ALTER TABLE source_questions ADD COLUMN choice_parse_reason TEXT",
    }
    for column, statement in migrations.items():
        if column not in columns:
            connection.execute(statement)
    connection.execute(
        "UPDATE source_questions SET normalized_question = raw_question "
        "WHERE normalized_question IS NULL AND canonical_id IS NOT NULL"
    )


def _add_canonical_question_columns(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(canonical_questions)")}
    if "is_publishable" not in columns:
        connection.execute(
            "ALTER TABLE canonical_questions ADD COLUMN is_publishable INTEGER NOT NULL DEFAULT 1 "
            "CHECK (is_publishable IN (0, 1))"
        )


def _add_attempt_columns(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(attempts)")}
    if "time_limit_seconds" not in columns:
        connection.execute(
            "ALTER TABLE attempts ADD COLUMN time_limit_seconds INTEGER NOT NULL DEFAULT 1800 "
            "CHECK (time_limit_seconds > 0)"
        )
    if "deadline_at" not in columns:
        connection.execute("ALTER TABLE attempts ADD COLUMN deadline_at TEXT")
        connection.execute(
            "UPDATE attempts SET deadline_at = datetime(started_at, '+30 minutes') WHERE deadline_at IS NULL"
        )


def record_source(connection: sqlite3.Connection, filename: str, kind: str, checksum: str) -> int:
    """Insert a source document once and return its identifier."""
    connection.execute(
        "INSERT INTO sources (filename, kind, checksum) VALUES (?, ?, ?)",
        (filename, kind, checksum),
    )
    return int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])


def record_canonical_question(
    connection: sqlite3.Connection,
    question: str,
    choices_json: str,
    answer: str,
    explanation: str,
    topic: str,
    difficulty: str,
    content_hash: str,
) -> int:
    """Store a normalized question and return its identifier."""
    connection.execute(
        """
        INSERT INTO canonical_questions
        (content_hash, question, choices_json, answer, explanation, topic, difficulty, solution_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'drafted')
        """,
        (content_hash, question, choices_json, answer, explanation, topic, difficulty),
    )
    return int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])


def record_source_question(
    connection: sqlite3.Connection,
    source_id: int,
    ordinal: int,
    question: str,
    choices_json: str,
    canonical_id: int,
    source_label: str | None = None,
    page: int | None = None,
) -> None:
    """Preserve the source representation of a question."""
    connection.execute(
        """
        INSERT INTO source_questions
        (source_id, source_label, page, ordinal, raw_question, raw_choices_json, canonical_id, extraction_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'extracted')
        """,
        (
            source_id,
            source_label or str(ordinal),
            page,
            ordinal,
            question,
            choices_json,
            canonical_id,
        ),
    )
