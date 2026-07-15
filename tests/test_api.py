import json
import sqlite3
import tempfile
import unittest
import warnings
from pathlib import Path

with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        category=Warning,
        message=r"Using `httpx` with `starlette\.testclient` is deprecated",
    )
    from fastapi.testclient import TestClient

from app import create_app
from scripts.exams import create_exam_instance
from scripts.storage import create_database, get_or_create_subject


class ApiLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "review.db"
        create_database(self.db_path)
        connection = sqlite3.connect(self.db_path)
        try:
            for difficulty, count in (("Dễ", 12), ("Vừa", 8), ("Khó", 8), ("Rất khó", 12)):
                for index in range(count):
                    connection.execute(
                        """
                        INSERT INTO canonical_questions
                        (content_hash, question, choices_json, answer, explanation, topic, difficulty, solution_status)
                        VALUES (?, ?, ?, 'A', 'Giải thích', ?, ?, 'approved')
                        """,
                        (f"{difficulty}-{index}", f"Câu {index}", json.dumps(["A", "B", "C", "D"]), f"Chủ đề {index % 5}", difficulty),
                    )
            connection.commit()
        finally:
            connection.close()
        self.client = TestClient(create_app(self.db_path, admin_token="admin-test"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def _add_htttql_questions(self, count: int = 40) -> None:
        connection = sqlite3.connect(self.db_path)
        try:
            subject_id = get_or_create_subject(connection, "htttql", "Hệ thống thông tin quản lý")
            for index in range(count):
                connection.execute(
                    """
                    INSERT INTO canonical_questions
                    (subject_id, content_hash, question, choices_json, answer, explanation, topic, chapter, question_type, difficulty, solution_status)
                    VALUES (?, ?, ?, ?, 'A', 'Giải thích', 'Chương 1', 'Chương 1', 'Định nghĩa', 'Dễ', 'approved')
                    """,
                    (subject_id, f"htttql-api-helper-{index}", f"HTTTQL API {index}", json.dumps(["A", "B", "C", "D"])),
                )
            connection.commit()
        finally:
            connection.close()

    def test_student_payload_hides_answers_until_submission_and_submit_is_idempotent(self):
        created = self.client.post("/api/attempts", json={"seed": "api-test"})

        self.assertEqual(created.status_code, 201)
        payload = created.json()
        self.assertEqual(payload["mode"], "exam")
        self.assertEqual(len(payload["questions"]), 40)
        self.assertNotIn("correctAnswer", payload["questions"][0])
        self.assertNotIn("explanation", payload["questions"][0])

        connection = sqlite3.connect(self.db_path)
        try:
            rows = connection.execute(
                """
                SELECT position, snapshot_json
                FROM exam_instance_questions
                WHERE exam_instance_id = ?
                ORDER BY position
                LIMIT 2
                """,
                (payload["examInstanceId"],),
            ).fetchall()
        finally:
            connection.close()
        first_answer = json.loads(rows[0][1])["correctAnswer"]
        second_answer = json.loads(rows[1][1])["correctAnswer"]
        wrong_second_answer = next(answer for answer in "ABCD" if answer != second_answer)

        saved = self.client.put(
            f"/api/attempts/{payload['attemptId']}/answers/1",
            json={"selectedAnswer": first_answer, "markedForReview": True},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(
            self.client.put(
                f"/api/attempts/{payload['attemptId']}/answers/2",
                json={"selectedAnswer": wrong_second_answer, "markedForReview": False},
            ).status_code,
            200,
        )

        refreshed = self.client.get(f"/api/attempts/{payload['attemptId']}")
        self.assertNotIn("correctAnswer", json.dumps(refreshed.json()))
        self.assertNotIn("explanation", json.dumps(refreshed.json()))

        submitted = self.client.post(f"/api/attempts/{payload['attemptId']}/submit")
        repeated = self.client.post(f"/api/attempts/{payload['attemptId']}/submit")
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json(), repeated.json())
        result = submitted.json()
        self.assertEqual(result["score"], 1)
        self.assertEqual(result["correctCount"], 1)
        self.assertEqual(result["wrongCount"], 1)
        self.assertEqual(result["unansweredCount"], 38)
        self.assertEqual(result["totalQuestions"], 40)
        self.assertIn("correctAnswer", result["questions"][0])
        self.assertIn("explanation", result["questions"][0])

    def test_study_mode_reveals_feedback_only_after_answering(self):
        created = self.client.post("/api/attempts", json={"seed": "study-test", "mode": "study", "questionCount": 5})

        self.assertEqual(created.status_code, 201)
        payload = created.json()
        self.assertEqual(payload["mode"], "study")
        self.assertEqual(len(payload["questions"]), 5)
        self.assertNotIn("correctAnswer", payload["questions"][0])

        saved = self.client.put(
            f"/api/attempts/{payload['attemptId']}/answers/1",
            json={"selectedAnswer": "A", "markedForReview": False},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertIn("correctAnswer", saved.json())
        self.assertIn("explanation", saved.json())

        refreshed = self.client.get(f"/api/attempts/{payload['attemptId']}")
        self.assertIn("correctAnswer", refreshed.json()["questions"][0])
        self.assertNotIn("correctAnswer", refreshed.json()["questions"][1])

    def test_latest_submitted_attempt_ignores_newer_in_progress_attempts(self):
        empty = self.client.get("/api/attempts/latest-submitted")
        self.assertEqual(empty.status_code, 200)
        self.assertIsNone(empty.json()["data"])

        submitted = self.client.post("/api/attempts", json={"seed": "latest-submitted"})
        self.assertEqual(submitted.status_code, 201)
        submitted_payload = submitted.json()
        self.assertEqual(self.client.post(f"/api/attempts/{submitted_payload['attemptId']}/submit").status_code, 200)

        in_progress = self.client.post("/api/attempts", json={"seed": "newer-in-progress"})
        self.assertEqual(in_progress.status_code, 201)

        latest = self.client.get("/api/attempts/latest-submitted")

        self.assertEqual(latest.status_code, 200)
        payload = latest.json()["data"]
        self.assertEqual(payload["attemptId"], submitted_payload["attemptId"])
        self.assertEqual(payload["score"], 0)
        self.assertEqual(payload["totalQuestions"], 40)
        self.assertTrue(payload["submittedAt"].endswith("Z"))
        self.assertNotIn("questions", json.dumps(payload))
        self.assertNotIn("correctAnswer", json.dumps(payload))
        self.assertNotIn("explanation", json.dumps(payload))

    def test_admin_endpoint_requires_the_configured_token(self):
        self.assertEqual(self.client.get("/api/admin/questions").status_code, 403)
        allowed = self.client.get("/api/admin/questions", headers={"X-Admin-Token": "admin-test"})
        self.assertEqual(allowed.status_code, 200)
        self.assertIn("data", allowed.json())

    def test_lists_subjects_and_catalog_without_answer_data(self):
        subjects = self.client.get("/api/subjects")
        catalog = self.client.get("/api/subjects/cslt/catalog")

        self.assertEqual(subjects.status_code, 200)
        self.assertEqual(subjects.json()["data"][0]["slug"], "cslt")
        self.assertEqual(subjects.json()["data"][0]["questionCount"], 40)
        self.assertEqual(catalog.status_code, 200)
        self.assertIn("difficulties", catalog.json()["data"])
        self.assertNotIn("correctAnswer", json.dumps(catalog.json()))
        self.assertNotIn("explanation", json.dumps(catalog.json()))

    def test_can_start_one_of_the_published_exams_with_a_30_minute_limit(self):
        exam = create_exam_instance(self.db_path, seed="published", status="published")

        listed = self.client.get("/api/exams/published")
        started = self.client.post("/api/attempts", json={"examInstanceId": exam.id})

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"][0]["id"], exam.id)
        self.assertEqual(started.status_code, 201)
        self.assertEqual(started.json()["examInstanceId"], exam.id)
        self.assertEqual(started.json()["timeLimitSeconds"], 1800)
        self.assertTrue(started.json()["deadlineAt"].endswith("Z"))

    def test_lists_published_exams_filtered_by_subject_without_ratio_data(self):
        cslt_exam = create_exam_instance(self.db_path, seed="published-cslt", status="published", title="CSLT Đề 01")
        self._add_htttql_questions()
        htttql_exam = create_exam_instance(
            self.db_path,
            seed="published-htttql",
            status="published",
            subject_slug="htttql",
            question_count=40,
            title="HTTTQL Đề 01",
        )

        listed = self.client.get("/api/exams/published", params={"subjectSlug": "htttql"})

        self.assertEqual(listed.status_code, 200)
        payload = listed.json()["data"]
        self.assertEqual([item["id"] for item in payload], [htttql_exam.id])
        self.assertEqual(payload[0]["title"], "HTTTQL Đề 01")
        self.assertEqual(payload[0]["subject"]["slug"], "htttql")
        self.assertNotEqual(payload[0]["id"], cslt_exam.id)
        self.assertNotIn("difficulty", json.dumps(payload).lower())
        self.assertNotIn("ratio", json.dumps(payload).lower())

    def test_recent_attempt_history_returns_last_7_days_with_tags_and_counts(self):
        published_exam = create_exam_instance(self.db_path, seed="history-published", status="published", title="CSLT Đề 01")
        first = self.client.post("/api/attempts", json={"examInstanceId": published_exam.id}).json()
        self.assertEqual(self.client.post(f"/api/attempts/{first['attemptId']}/submit").status_code, 200)
        second = self.client.post("/api/attempts", json={"examInstanceId": published_exam.id}).json()
        self.assertEqual(self.client.post(f"/api/attempts/{second['attemptId']}/submit").status_code, 200)
        random_attempt = self.client.post("/api/attempts", json={"seed": "history-random"}).json()
        self.assertEqual(self.client.post(f"/api/attempts/{random_attempt['attemptId']}/submit").status_code, 200)
        old_attempt = self.client.post("/api/attempts", json={"seed": "history-old"}).json()
        self.assertEqual(self.client.post(f"/api/attempts/{old_attempt['attemptId']}/submit").status_code, 200)

        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute(
                "UPDATE attempts SET submitted_at = datetime('now', '-8 days') WHERE id = ?",
                (old_attempt["attemptId"],),
            )
            connection.commit()
        finally:
            connection.close()

        history = self.client.get("/api/attempts/recent", params={"days": 7})

        self.assertEqual(history.status_code, 200)
        payload = history.json()["data"]
        ids = [item["attemptId"] for item in payload]
        self.assertIn(first["attemptId"], ids)
        self.assertIn(second["attemptId"], ids)
        self.assertIn(random_attempt["attemptId"], ids)
        self.assertNotIn(old_attempt["attemptId"], ids)
        published_rows = [item for item in payload if item["examInstanceId"] == published_exam.id]
        self.assertTrue(all(item["tag"] == "Đề có sẵn" for item in published_rows))
        self.assertTrue(all(item["completedCountForExam"] == 2 for item in published_rows))
        random_row = next(item for item in payload if item["attemptId"] == random_attempt["attemptId"])
        self.assertEqual(random_row["tag"], "Đề ngẫu nhiên")
        self.assertIsNone(random_row["completedCountForExam"])
        self.assertNotIn("questions", json.dumps(payload))
        self.assertNotIn("correctAnswer", json.dumps(payload))
        self.assertNotIn("explanation", json.dumps(payload))

    def test_recent_attempt_history_can_filter_by_subject_and_submitted_date(self):
        self._add_htttql_questions(12)
        cslt_attempt = self.client.post("/api/attempts", json={"seed": "history-filter-cslt", "questionCount": 5}).json()
        self.assertEqual(self.client.post(f"/api/attempts/{cslt_attempt['attemptId']}/submit").status_code, 200)
        htttql_attempt = self.client.post(
            "/api/attempts",
            json={"subjectSlug": "htttql", "seed": "history-filter-htttql", "questionCount": 5},
        ).json()
        self.assertEqual(self.client.post(f"/api/attempts/{htttql_attempt['attemptId']}/submit").status_code, 200)

        connection = sqlite3.connect(self.db_path)
        try:
            today = connection.execute("SELECT date('now')").fetchone()[0]
            connection.execute(
                "UPDATE attempts SET submitted_at = datetime('now', '-1 day') WHERE id = ?",
                (cslt_attempt["attemptId"],),
            )
            connection.execute(
                "UPDATE attempts SET submitted_at = datetime('now') WHERE id = ?",
                (htttql_attempt["attemptId"],),
            )
            connection.commit()
        finally:
            connection.close()

        subject_filtered = self.client.get("/api/attempts/recent", params={"days": 7, "subjectSlug": "htttql"})
        date_filtered = self.client.get("/api/attempts/recent", params={"days": 7, "submittedDate": today})
        combined = self.client.get(
            "/api/attempts/recent",
            params={"days": 7, "subjectSlug": "htttql", "submittedDate": today},
        )

        self.assertEqual(subject_filtered.status_code, 200)
        self.assertEqual([item["attemptId"] for item in subject_filtered.json()["data"]], [htttql_attempt["attemptId"]])
        self.assertEqual([item["subject"]["slug"] for item in date_filtered.json()["data"]], ["htttql"])
        self.assertEqual([item["attemptId"] for item in combined.json()["data"]], [htttql_attempt["attemptId"]])

    def test_can_start_a_custom_subject_attempt_with_a_custom_time_limit(self):
        self._add_htttql_questions(20)

        started = self.client.post(
            "/api/attempts",
            json={"subjectSlug": "htttql", "questionCount": 20, "timeLimitSeconds": 900, "seed": "htttql-api"},
        )

        self.assertEqual(started.status_code, 201)
        payload = started.json()
        self.assertEqual(len(payload["questions"]), 20)
        self.assertEqual(payload["totalQuestions"], 20)
        self.assertEqual(payload["timeLimitSeconds"], 900)
        self.assertNotIn("correctAnswer", payload["questions"][0])


if __name__ == "__main__":
    unittest.main()
