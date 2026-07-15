"""FastAPI application for the CSLT exam review webapp."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from scripts.exams import InsufficientPoolError, create_exam_instance, publish_standard_exams
from scripts.storage import create_database


class CreateAttemptInput(BaseModel):
    seed: str | None = Field(default=None, min_length=1, max_length=128)
    examInstanceId: str | None = Field(default=None, min_length=1, max_length=64)
    mode: Literal["exam", "study"] = "exam"
    subjectSlug: str | None = Field(default=None, min_length=1, max_length=64)
    questionCount: int | None = Field(default=None, ge=1, le=200)
    timeLimitSeconds: int | None = Field(default=None, ge=60, le=14400)
    chapters: list[str] | None = None
    topics: list[str] | None = None
    difficulties: list[Literal["Dễ", "Vừa", "Khó", "Rất khó"]] | None = None
    questionTypes: list[str] | None = None


class SaveAnswerInput(BaseModel):
    selectedAnswer: str | None = Field(default=None, pattern="^[ABCD]$")
    markedForReview: bool = False


class PublishExamsInput(BaseModel):
    seedPrefix: str = Field(default="published", min_length=1, max_length=64)


class UpdateQuestionInput(BaseModel):
    answer: Literal["A", "B", "C", "D"] | None = None
    explanation: str | None = Field(default=None, min_length=1, max_length=10000)
    topic: str | None = Field(default=None, min_length=1, max_length=120)
    difficulty: Literal["Dễ", "Vừa", "Khó", "Rất khó"] | None = None
    solutionStatus: Literal["pending", "drafted", "reviewed", "approved"] | None = None


def _connection(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _public_question(snapshot: dict[str, Any], position: int, answer: sqlite3.Row | None, reveal_answer: bool = False) -> dict[str, Any]:
    question = {
        "position": position,
        "question": snapshot["question"],
        "choices": snapshot["choices"],
        "topic": snapshot["topic"],
        "chapter": snapshot.get("chapter"),
        "questionType": snapshot.get("questionType"),
        "difficulty": snapshot["difficulty"],
        "assumptions": snapshot["assumptions"],
        "selectedAnswer": answer["selected_answer"] if answer else None,
        "markedForReview": bool(answer["marked_for_review"]) if answer else False,
    }
    if reveal_answer:
        question.update(
            {
                "correctAnswer": snapshot["correctAnswer"],
                "explanation": snapshot["explanation"],
                "isCorrect": answer is not None and answer["selected_answer"] == snapshot["correctAnswer"],
            }
        )
    return question


def _iso_timestamp(timestamp: str | None) -> str | None:
    if timestamp is None:
        return None
    return f"{timestamp.replace(' ', 'T')}Z"


def _attempt_payload(connection: sqlite3.Connection, attempt_id: str, include_results: bool) -> dict[str, Any]:
    attempt = connection.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
    if attempt is None:
        raise _error(404, "ATTEMPT_NOT_FOUND", "Không tìm thấy lượt làm bài.")
    rows = connection.execute(
        """
        SELECT question.position, question.snapshot_json, answer.selected_answer, answer.marked_for_review
        FROM exam_instance_questions AS question
        LEFT JOIN attempt_answers AS answer
          ON answer.attempt_id = ? AND answer.position = question.position
        WHERE question.exam_instance_id = ?
        ORDER BY question.position
        """,
        (attempt_id, attempt["exam_instance_id"]),
    ).fetchall()
    questions = []
    for row in rows:
        snapshot = json.loads(row["snapshot_json"])
        reveal_answer = include_results or (attempt["mode"] == "study" and row["selected_answer"] is not None)
        question = _public_question(snapshot, int(row["position"]), row, reveal_answer)
        questions.append(question)
    payload: dict[str, Any] = {
        "attemptId": attempt["id"],
        "examInstanceId": attempt["exam_instance_id"],
        "mode": attempt["mode"],
        "status": attempt["status"],
        "startedAt": _iso_timestamp(attempt["started_at"]),
        "deadlineAt": _iso_timestamp(attempt["deadline_at"]),
        "timeLimitSeconds": attempt["time_limit_seconds"],
        "totalQuestions": attempt["total_questions"],
        "questions": questions,
    }
    if include_results:
        correct_count = sum(1 for question in questions if question["selectedAnswer"] is not None and question.get("isCorrect"))
        wrong_count = sum(1 for question in questions if question["selectedAnswer"] is not None and not question.get("isCorrect"))
        unanswered_count = sum(1 for question in questions if question["selectedAnswer"] is None)
        payload.update(
            {
                "score": attempt["score"],
                "correctCount": correct_count,
                "wrongCount": wrong_count,
                "unansweredCount": unanswered_count,
            }
        )
    return payload


def create_app(db_path: Path | None = None, admin_token: str | None = None) -> FastAPI:
    configured_database = os.getenv("CSLT_DATABASE_PATH")
    database = (
        db_path
        if db_path is not None
        else Path(configured_database).expanduser()
        if configured_database
        else Path(__file__).resolve().parent / "data" / "review.db"
    )
    create_database(database)
    expected_admin_token = admin_token if admin_token is not None else os.getenv("CSLT_ADMIN_TOKEN")
    app = FastAPI(title="Ôn thi HUB", version="1.0.0")
    root = Path(__file__).resolve().parent
    templates = Jinja2Templates(directory=root / "templates")
    app.mount("/static", StaticFiles(directory=root / "static"), name="static")

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'self'; frame-ancestors 'none'"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.exception_handler(HTTPException)
    async def handle_http_error(_, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "REQUEST_ERROR", "message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content={"error": detail})

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_, __):
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "message": "Dữ liệu gửi lên không hợp lệ."}},
        )

    def require_admin(x_admin_token: Annotated[str | None, Header()] = None) -> None:
        if not expected_admin_token:
            raise _error(503, "ADMIN_NOT_CONFIGURED", "Chưa cấu hình CSLT_ADMIN_TOKEN.")
        if x_admin_token != expected_admin_token:
            raise _error(403, "ADMIN_FORBIDDEN", "Không có quyền quản trị.")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/subjects")
    def list_subjects() -> dict[str, Any]:
        connection = _connection(database)
        try:
            rows = connection.execute(
                """
                SELECT subjects.slug, subjects.title,
                       COUNT(canonical_questions.id) AS question_count
                FROM subjects
                LEFT JOIN canonical_questions
                  ON canonical_questions.subject_id = subjects.id
                 AND canonical_questions.solution_status = 'approved'
                 AND canonical_questions.is_publishable = 1
                GROUP BY subjects.id, subjects.slug, subjects.title
                ORDER BY subjects.title
                """
            ).fetchall()
            return {
                "data": [
                    {
                        "slug": row["slug"],
                        "title": row["title"],
                        "questionCount": row["question_count"],
                    }
                    for row in rows
                ]
            }
        finally:
            connection.close()

    @app.get("/api/subjects/{subject_slug}/catalog")
    def get_subject_catalog(subject_slug: str) -> dict[str, Any]:
        connection = _connection(database)
        try:
            subject = connection.execute(
                "SELECT id, slug, title FROM subjects WHERE slug = ?",
                (subject_slug,),
            ).fetchone()
            if subject is None:
                raise _error(404, "SUBJECT_NOT_FOUND", "Không tìm thấy môn học.")

            def counts(field: str) -> list[dict[str, Any]]:
                rows = connection.execute(
                    f"""
                    SELECT {field} AS value, COUNT(*) AS count
                    FROM canonical_questions
                    WHERE subject_id = ?
                      AND solution_status = 'approved'
                      AND is_publishable = 1
                      AND {field} IS NOT NULL
                      AND {field} != ''
                    GROUP BY {field}
                    ORDER BY {field}
                    """,
                    (subject["id"],),
                ).fetchall()
                return [{"value": row["value"], "count": row["count"]} for row in rows]

            total = connection.execute(
                """
                SELECT COUNT(*)
                FROM canonical_questions
                WHERE subject_id = ?
                  AND solution_status = 'approved'
                  AND is_publishable = 1
                """,
                (subject["id"],),
            ).fetchone()[0]
            return {
                "data": {
                    "subject": {"slug": subject["slug"], "title": subject["title"]},
                    "questionCount": total,
                    "chapters": counts("chapter"),
                    "topics": counts("topic"),
                    "difficulties": counts("difficulty"),
                    "questionTypes": counts("question_type"),
                }
            }
        finally:
            connection.close()

    @app.get("/api/exams/published")
    def list_published_exams(subjectSlug: str | None = Query(default=None, min_length=1, max_length=64)) -> dict[str, Any]:
        connection = _connection(database)
        try:
            filters = ["exam_instances.status = 'published'"]
            params: list[Any] = []
            if subjectSlug:
                filters.append("subjects.slug = ?")
                params.append(subjectSlug)
            rows = connection.execute(
                f"""
                SELECT exam_instances.id,
                       exam_instances.title,
                       exam_instances.created_at,
                       subjects.slug AS subject_slug,
                       subjects.title AS subject_title,
                       COUNT(exam_instance_questions.position) AS question_count
                FROM exam_instances
                LEFT JOIN subjects ON subjects.id = exam_instances.subject_id
                LEFT JOIN exam_instance_questions
                  ON exam_instance_questions.exam_instance_id = exam_instances.id
                WHERE {' AND '.join(filters)}
                GROUP BY exam_instances.id, exam_instances.title, exam_instances.created_at, subjects.slug, subjects.title
                ORDER BY exam_instances.created_at, exam_instances.id
                """,
                params,
            ).fetchall()
            return {
                "data": [
                    {
                        "id": row["id"],
                        "title": row["title"] or f"Đề {index:02}",
                        "questionCount": row["question_count"],
                        "subject": {
                            "slug": row["subject_slug"] or "cslt",
                            "title": row["subject_title"] or "Cơ sở lập trình",
                        },
                    }
                    for index, row in enumerate(rows, start=1)
                ]
            }
        finally:
            connection.close()

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return templates.TemplateResponse(request, "home.html", {"page": "home"})

    @app.get("/exam/{attempt_id}", response_class=HTMLResponse)
    def exam_page(request: Request, attempt_id: str):
        return templates.TemplateResponse(request, "exam.html", {"page": "exam", "attempt_id": attempt_id})

    @app.get("/result/{attempt_id}", response_class=HTMLResponse)
    def result_page(request: Request, attempt_id: str):
        return templates.TemplateResponse(request, "result.html", {"page": "result", "attempt_id": attempt_id})

    @app.get("/admin", response_class=HTMLResponse)
    def admin_page(request: Request):
        return templates.TemplateResponse(request, "admin.html", {"page": "admin"})

    @app.post("/api/attempts", status_code=status.HTTP_201_CREATED)
    def create_attempt(input_data: CreateAttemptInput) -> dict[str, Any]:
        if input_data.seed and input_data.examInstanceId:
            raise _error(422, "VALIDATION_ERROR", "Chỉ chọn seed hoặc đề đã publish.")
        custom_fields = (
            input_data.subjectSlug,
            input_data.questionCount,
            input_data.timeLimitSeconds,
            input_data.chapters,
            input_data.topics,
            input_data.difficulties,
            input_data.questionTypes,
        )
        if input_data.examInstanceId and any(value is not None for value in custom_fields):
            raise _error(422, "VALIDATION_ERROR", "Đề đã publish không nhận thêm cấu hình tùy chỉnh.")
        if input_data.examInstanceId:
            connection = _connection(database)
            try:
                instance = connection.execute(
                    "SELECT id FROM exam_instances WHERE id = ? AND status = 'published'",
                    (input_data.examInstanceId,),
                ).fetchone()
            finally:
                connection.close()
            if instance is None:
                raise _error(404, "PUBLISHED_EXAM_NOT_FOUND", "Không tìm thấy đề đã publish.")
            instance_id = instance["id"]
        else:
            seed = input_data.seed or str(uuid.uuid4())
            try:
                instance_id = create_exam_instance(
                    database,
                    seed,
                    subject_slug=input_data.subjectSlug or "cslt",
                    question_count=input_data.questionCount,
                    chapters=input_data.chapters,
                    topics=input_data.topics,
                    difficulties=input_data.difficulties,
                    question_types=input_data.questionTypes,
                ).id
            except InsufficientPoolError as error:
                raise _error(409, "INSUFFICIENT_POOL", str(error)) from error
        attempt_id = str(uuid.uuid4())
        time_limit_seconds = input_data.timeLimitSeconds or 1800
        connection = _connection(database)
        try:
            total_questions = connection.execute(
                "SELECT COUNT(*) FROM exam_instance_questions WHERE exam_instance_id = ?",
                (instance_id,),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO attempts (id, exam_instance_id, mode, total_questions, time_limit_seconds, deadline_at)
                VALUES (?, ?, ?, ?, ?, datetime('now', ?))
                """,
                (attempt_id, instance_id, input_data.mode, total_questions, time_limit_seconds, f"+{time_limit_seconds} seconds"),
            )
            connection.commit()
            return _attempt_payload(connection, attempt_id, include_results=False)
        finally:
            connection.close()

    @app.get("/api/attempts/latest-submitted")
    def get_latest_submitted_attempt() -> dict[str, Any]:
        connection = _connection(database)
        try:
            attempt = connection.execute(
                """
                SELECT id, exam_instance_id, mode, started_at, submitted_at, score,
                       total_questions, time_limit_seconds
                FROM attempts
                WHERE status = 'submitted'
                ORDER BY submitted_at DESC, started_at DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
            if attempt is None:
                return {"data": None}
            return {
                "data": {
                    "attemptId": attempt["id"],
                    "examInstanceId": attempt["exam_instance_id"],
                    "mode": attempt["mode"],
                    "startedAt": _iso_timestamp(attempt["started_at"]),
                    "submittedAt": _iso_timestamp(attempt["submitted_at"]),
                    "score": attempt["score"],
                    "totalQuestions": attempt["total_questions"],
                    "timeLimitSeconds": attempt["time_limit_seconds"],
                }
            }
        finally:
            connection.close()

    @app.get("/api/attempts/recent")
    def get_recent_attempts(
        days: int = Query(default=7, ge=1, le=30),
        subjectSlug: str | None = Query(default=None, min_length=1, max_length=64),
        submittedDate: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    ) -> dict[str, Any]:
        connection = _connection(database)
        try:
            filters = ["attempts.status = 'submitted'", "attempts.submitted_at >= datetime('now', ?)"]
            params: list[Any] = [f"-{days} days"]
            if subjectSlug:
                filters.append("subjects.slug = ?")
                params.append(subjectSlug)
            if submittedDate:
                filters.append("date(attempts.submitted_at) = ?")
                params.append(submittedDate)
            rows = connection.execute(
                f"""
                SELECT attempts.id,
                       attempts.exam_instance_id,
                       attempts.mode,
                       attempts.started_at,
                       attempts.submitted_at,
                       attempts.score,
                       attempts.total_questions,
                       attempts.time_limit_seconds,
                       exam_instances.title,
                       exam_instances.source_kind,
                       exam_instances.status AS exam_status,
                       subjects.slug AS subject_slug,
                       subjects.title AS subject_title,
                       (
                           SELECT COUNT(*)
                           FROM attempts AS completed
                           WHERE completed.exam_instance_id = attempts.exam_instance_id
                             AND completed.status = 'submitted'
                       ) AS completed_count
                FROM attempts
                JOIN exam_instances ON exam_instances.id = attempts.exam_instance_id
                LEFT JOIN subjects ON subjects.id = exam_instances.subject_id
                WHERE {' AND '.join(filters)}
                ORDER BY attempts.submitted_at DESC, attempts.started_at DESC, attempts.id DESC
                """,
                params,
            ).fetchall()
            data = []
            for row in rows:
                is_published = row["source_kind"] == "published" or row["exam_status"] == "published"
                data.append(
                    {
                        "attemptId": row["id"],
                        "examInstanceId": row["exam_instance_id"],
                        "mode": row["mode"],
                        "startedAt": _iso_timestamp(row["started_at"]),
                        "submittedAt": _iso_timestamp(row["submitted_at"]),
                        "score": row["score"],
                        "totalQuestions": row["total_questions"],
                        "timeLimitSeconds": row["time_limit_seconds"],
                        "title": row["title"] or ("Đề có sẵn" if is_published else "Đề ngẫu nhiên"),
                        "subject": {
                            "slug": row["subject_slug"] or "cslt",
                            "title": row["subject_title"] or "Cơ sở lập trình",
                        },
                        "tag": "Đề có sẵn" if is_published else "Đề ngẫu nhiên",
                        "sourceKind": "published" if is_published else "random",
                        "completedCountForExam": row["completed_count"] if is_published else None,
                        "resultUrl": f"/result/{row['id']}",
                    }
                )
            return {"data": data}
        finally:
            connection.close()

    @app.get("/api/attempts/{attempt_id}")
    def get_attempt(attempt_id: str) -> dict[str, Any]:
        connection = _connection(database)
        try:
            attempt = connection.execute("SELECT status FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
            if attempt is None:
                raise _error(404, "ATTEMPT_NOT_FOUND", "Không tìm thấy lượt làm bài.")
            return _attempt_payload(connection, attempt_id, include_results=attempt["status"] == "submitted")
        finally:
            connection.close()

    @app.put("/api/attempts/{attempt_id}/answers/{position}")
    def save_answer(attempt_id: str, position: int, input_data: SaveAnswerInput) -> dict[str, Any]:
        connection = _connection(database)
        try:
            attempt = connection.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
            if attempt is None:
                raise _error(404, "ATTEMPT_NOT_FOUND", "Không tìm thấy lượt làm bài.")
            if attempt["status"] != "in_progress":
                raise _error(409, "ATTEMPT_SUBMITTED", "Lượt làm bài đã được nộp.")
            exists = connection.execute(
                "SELECT 1 FROM exam_instance_questions WHERE exam_instance_id = ? AND position = ?",
                (attempt["exam_instance_id"], position),
            ).fetchone()
            if exists is None:
                raise _error(404, "QUESTION_NOT_FOUND", "Không tìm thấy câu hỏi trong đề.")
            connection.execute(
                """
                INSERT INTO attempt_answers (attempt_id, position, selected_answer, marked_for_review)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(attempt_id, position) DO UPDATE SET
                    selected_answer = excluded.selected_answer,
                    marked_for_review = excluded.marked_for_review,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (attempt_id, position, input_data.selectedAnswer, int(input_data.markedForReview)),
            )
            connection.commit()
            payload: dict[str, Any] = {"position": position, "saved": True}
            if attempt["mode"] == "study" and input_data.selectedAnswer is not None:
                row = connection.execute(
                    """
                    SELECT snapshot_json
                    FROM exam_instance_questions
                    WHERE exam_instance_id = ? AND position = ?
                    """,
                    (attempt["exam_instance_id"], position),
                ).fetchone()
                snapshot = json.loads(row["snapshot_json"])
                payload.update(
                    {
                        "correctAnswer": snapshot["correctAnswer"],
                        "explanation": snapshot["explanation"],
                        "isCorrect": input_data.selectedAnswer == snapshot["correctAnswer"],
                    }
                )
            return payload
        finally:
            connection.close()

    @app.post("/api/attempts/{attempt_id}/submit")
    def submit_attempt(attempt_id: str) -> dict[str, Any]:
        connection = _connection(database)
        try:
            attempt = connection.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
            if attempt is None:
                raise _error(404, "ATTEMPT_NOT_FOUND", "Không tìm thấy lượt làm bài.")
            if attempt["status"] == "in_progress":
                score = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM exam_instance_questions AS question
                    JOIN attempt_answers AS answer
                      ON answer.attempt_id = ? AND answer.position = question.position
                    WHERE question.exam_instance_id = ?
                      AND json_extract(question.snapshot_json, '$.correctAnswer') = answer.selected_answer
                    """,
                    (attempt_id, attempt["exam_instance_id"]),
                ).fetchone()[0]
                connection.execute(
                    """
                    UPDATE attempts
                    SET status = 'submitted', submitted_at = CURRENT_TIMESTAMP, score = ?
                    WHERE id = ?
                    """,
                    (score, attempt_id),
                )
                connection.commit()
            return _attempt_payload(connection, attempt_id, include_results=True)
        finally:
            connection.close()

    @app.get("/api/admin/questions", dependencies=[Depends(require_admin)])
    def list_admin_questions(
        page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=25, le=50)
    ) -> dict[str, Any]:
        connection = _connection(database)
        try:
            total = connection.execute("SELECT COUNT(*) FROM canonical_questions").fetchone()[0]
            rows = connection.execute(
                """
                SELECT id, question, topic, difficulty, solution_status, updated_at
                FROM canonical_questions
                ORDER BY id
                LIMIT ? OFFSET ?
                """,
                (page_size, (page - 1) * page_size),
            ).fetchall()
            return {
                "data": [dict(row) for row in rows],
                "pagination": {"page": page, "pageSize": page_size, "totalItems": total},
            }
        finally:
            connection.close()

    @app.get("/api/admin/review-queue", dependencies=[Depends(require_admin)])
    def list_review_queue(page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=25, le=50)) -> dict[str, Any]:
        connection = _connection(database)
        try:
            total = connection.execute("SELECT COUNT(*) FROM review_queue WHERE status = 'open'").fetchone()[0]
            rows = connection.execute(
                """
                SELECT id, canonical_id, source_question_id, reason, created_at
                FROM review_queue WHERE status = 'open'
                ORDER BY id LIMIT ? OFFSET ?
                """,
                (page_size, (page - 1) * page_size),
            ).fetchall()
            return {"data": [dict(row) for row in rows], "pagination": {"page": page, "pageSize": page_size, "totalItems": total}}
        finally:
            connection.close()

    @app.patch("/api/admin/questions/{question_id}", dependencies=[Depends(require_admin)])
    def update_question(question_id: int, input_data: UpdateQuestionInput) -> dict[str, Any]:
        values = input_data.model_dump(exclude_none=True)
        field_map = {"answer": "answer", "explanation": "explanation", "topic": "topic", "difficulty": "difficulty", "solutionStatus": "solution_status"}
        if not values:
            raise _error(422, "VALIDATION_ERROR", "Cần cung cấp ít nhất một trường để cập nhật.")
        connection = _connection(database)
        try:
            before = connection.execute("SELECT * FROM canonical_questions WHERE id = ?", (question_id,)).fetchone()
            if before is None:
                raise _error(404, "QUESTION_NOT_FOUND", "Không tìm thấy câu hỏi.")
            assignments = ", ".join(f"{field_map[key]} = ?" for key in values)
            connection.execute(f"UPDATE canonical_questions SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (*values.values(), question_id))
            after = connection.execute("SELECT * FROM canonical_questions WHERE id = ?", (question_id,)).fetchone()
            connection.execute(
                "INSERT INTO solution_audit (canonical_id, action, before_json, after_json) VALUES (?, 'admin_update', ?, ?)",
                (question_id, json.dumps(dict(before), ensure_ascii=False), json.dumps(dict(after), ensure_ascii=False)),
            )
            connection.commit()
            return {"data": dict(after)}
        finally:
            connection.close()

    @app.post("/api/admin/exams/publish", dependencies=[Depends(require_admin)])
    def publish_exams(input_data: PublishExamsInput) -> dict[str, Any]:
        connection = _connection(database)
        try:
            existing = connection.execute("SELECT COUNT(*) FROM exam_instances WHERE status = 'published'").fetchone()[0]
        finally:
            connection.close()
        if existing:
            raise _error(409, "STANDARD_EXAMS_ALREADY_PUBLISHED", "Đề chuẩn đã được publish; không tạo thêm để tránh lặp câu.")
        try:
            exams = publish_standard_exams(
                database,
                count=10,
                seed_prefix=input_data.seedPrefix,
                allow_cross_exam_reuse=True,
            )
        except InsufficientPoolError as error:
            raise _error(409, "INSUFFICIENT_POOL", str(error)) from error
        return {"examIds": [exam.id for exam in exams], "count": len(exams)}

    return app


app = create_app()
