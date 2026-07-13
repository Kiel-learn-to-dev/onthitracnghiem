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


class CreateAttemptInput(BaseModel):
    seed: str | None = Field(default=None, min_length=1, max_length=128)
    examInstanceId: str | None = Field(default=None, min_length=1, max_length=64)


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


def _public_question(snapshot: dict[str, Any], position: int, answer: sqlite3.Row | None) -> dict[str, Any]:
    return {
        "position": position,
        "question": snapshot["question"],
        "choices": snapshot["choices"],
        "topic": snapshot["topic"],
        "difficulty": snapshot["difficulty"],
        "assumptions": snapshot["assumptions"],
        "selectedAnswer": answer["selected_answer"] if answer else None,
        "markedForReview": bool(answer["marked_for_review"]) if answer else False,
    }


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
        question = _public_question(snapshot, int(row["position"]), row)
        if include_results:
            question.update(
                {
                    "correctAnswer": snapshot["correctAnswer"],
                    "explanation": snapshot["explanation"],
                    "isCorrect": row["selected_answer"] == snapshot["correctAnswer"],
                }
            )
        questions.append(question)
    payload: dict[str, Any] = {
        "attemptId": attempt["id"],
        "examInstanceId": attempt["exam_instance_id"],
        "status": attempt["status"],
        "startedAt": _iso_timestamp(attempt["started_at"]),
        "deadlineAt": _iso_timestamp(attempt["deadline_at"]),
        "timeLimitSeconds": attempt["time_limit_seconds"],
        "questions": questions,
    }
    if include_results:
        payload.update({"score": attempt["score"], "totalQuestions": attempt["total_questions"]})
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
    expected_admin_token = admin_token if admin_token is not None else os.getenv("CSLT_ADMIN_TOKEN")
    app = FastAPI(title="CSLT Ôn thi", version="1.0.0")
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

    @app.get("/api/exams/published")
    def list_published_exams() -> dict[str, Any]:
        connection = _connection(database)
        try:
            rows = connection.execute(
                """
                SELECT id, created_at FROM exam_instances
                WHERE status = 'published'
                ORDER BY created_at, id
                """
            ).fetchall()
            return {
                "data": [
                    {"id": row["id"], "title": f"Đề {index:02}", "questionCount": 40}
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
                instance_id = create_exam_instance(database, seed).id
            except InsufficientPoolError as error:
                raise _error(409, "INSUFFICIENT_POOL", str(error)) from error
        attempt_id = str(uuid.uuid4())
        connection = _connection(database)
        try:
            connection.execute(
                """
                INSERT INTO attempts (id, exam_instance_id, total_questions, time_limit_seconds, deadline_at)
                VALUES (?, ?, 40, 1800, datetime('now', '+30 minutes'))
                """,
                (attempt_id, instance_id),
            )
            connection.commit()
            return _attempt_payload(connection, attempt_id, include_results=False)
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
            return {"position": position, "saved": True}
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
