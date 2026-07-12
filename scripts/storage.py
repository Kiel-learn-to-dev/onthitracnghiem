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
"""


def create_database(db_path: Path) -> None:
    """Create or upgrade the local review database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(SCHEMA)
        _add_source_question_columns(connection)
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
    }
    for column, statement in migrations.items():
        if column not in columns:
            connection.execute(statement)


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
