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
from scripts.storage import create_database


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

    def test_student_payload_hides_answers_until_submission_and_submit_is_idempotent(self):
        created = self.client.post("/api/attempts", json={"seed": "api-test"})

        self.assertEqual(created.status_code, 201)
        payload = created.json()
        self.assertEqual(len(payload["questions"]), 40)
        self.assertNotIn("correctAnswer", payload["questions"][0])
        self.assertNotIn("explanation", payload["questions"][0])

        saved = self.client.put(
            f"/api/attempts/{payload['attemptId']}/answers/1",
            json={"selectedAnswer": "A", "markedForReview": True},
        )
        self.assertEqual(saved.status_code, 200)

        submitted = self.client.post(f"/api/attempts/{payload['attemptId']}/submit")
        repeated = self.client.post(f"/api/attempts/{payload['attemptId']}/submit")
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json(), repeated.json())
        self.assertIn("correctAnswer", submitted.json()["questions"][0])
        self.assertIn("explanation", submitted.json()["questions"][0])

    def test_admin_endpoint_requires_the_configured_token(self):
        self.assertEqual(self.client.get("/api/admin/questions").status_code, 403)
        allowed = self.client.get("/api/admin/questions", headers={"X-Admin-Token": "admin-test"})
        self.assertEqual(allowed.status_code, 200)
        self.assertIn("data", allowed.json())

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


if __name__ == "__main__":
    unittest.main()
