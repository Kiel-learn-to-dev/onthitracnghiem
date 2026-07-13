import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.exams import InsufficientPoolError, create_exam_instance, publish_standard_exams, refresh_exam_snapshots
from scripts.storage import create_database


class ExamGeneratorTests(unittest.TestCase):
    def _database_with_questions(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "review.db"
        create_database(db_path)
        connection = sqlite3.connect(db_path)
        try:
            for difficulty, count in (("Dễ", 12), ("Vừa", 8), ("Khó", 8), ("Rất khó", 12)):
                for index in range(count):
                    connection.execute(
                        """
                        INSERT INTO canonical_questions
                        (content_hash, question, choices_json, answer, explanation, topic, difficulty, solution_status)
                        VALUES (?, ?, ?, 'A', 'Giải thích', ?, ?, 'approved')
                        """,
                        (
                            f"{difficulty}-{index}",
                            f"Câu {difficulty} {index}",
                            json.dumps(["A", "B", "C", "D"]),
                            f"Chủ đề {index % 5}",
                            difficulty,
                        ),
                    )
            connection.commit()
        finally:
            connection.close()
        return db_path

    def test_creates_a_reproducible_40_question_blueprint(self):
        db_path = self._database_with_questions()

        first = create_exam_instance(db_path, seed="reproducible")
        second = create_exam_instance(db_path, seed="reproducible")

        self.assertEqual(first.question_ids, second.question_ids)
        self.assertEqual(len(first.question_ids), 40)
        self.assertEqual(len(set(first.question_ids)), 40)
        self.assertEqual(first.counts_by_difficulty, {"Dễ": 12, "Vừa": 8, "Khó": 8, "Rất khó": 12})

    def test_reports_the_specific_missing_difficulty_bucket(self):
        db_path = self._database_with_questions()
        connection = sqlite3.connect(db_path)
        try:
            connection.execute("DELETE FROM canonical_questions WHERE difficulty = 'Rất khó'")
            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(InsufficientPoolError, "Rất khó: thiếu 12"):
            create_exam_instance(db_path, seed="not-enough")

    def test_publishes_non_overlapping_standard_exams(self):
        db_path = self._database_with_questions()
        connection = sqlite3.connect(db_path)
        try:
            for difficulty, count in (("Dễ", 108), ("Vừa", 72), ("Khó", 72), ("Rất khó", 108)):
                for index in range(count):
                    connection.execute(
                        """
                        INSERT INTO canonical_questions
                        (content_hash, question, choices_json, answer, explanation, topic, difficulty, solution_status)
                        VALUES (?, ?, ?, 'A', 'Giải thích', ?, ?, 'approved')
                        """,
                        (f"extra-{difficulty}-{index}", f"Câu thêm {index}", json.dumps(["A", "B", "C", "D"]), f"Chủ đề {index % 5}", difficulty),
                    )
            connection.commit()
        finally:
            connection.close()

        exams = publish_standard_exams(db_path, count=10, seed_prefix="published-test")

        ids = [question_id for exam in exams for question_id in exam.question_ids]
        self.assertEqual(len(exams), 10)
        self.assertEqual(len(ids), len(set(ids)))

    def test_generates_one_hundred_random_exams_with_the_published_ratio(self):
        db_path = self._database_with_questions()

        generated = [create_exam_instance(db_path, seed=f"random-{index}") for index in range(100)]

        self.assertTrue(all(len(exam.question_ids) == 40 for exam in generated))
        self.assertTrue(
            all(
                exam.counts_by_difficulty == {"Dễ": 12, "Vừa": 8, "Khó": 8, "Rất khó": 12}
                for exam in generated
            )
        )

    def test_refreshes_existing_exam_stems_after_question_curation(self):
        db_path = self._database_with_questions()
        exam = create_exam_instance(db_path, seed="refresh-stem")
        question_id = exam.question_ids[0]

        connection = sqlite3.connect(db_path)
        try:
            connection.execute(
                "UPDATE canonical_questions SET question = 'Chỉ còn đề bài.' WHERE id = ?",
                (question_id,),
            )
            connection.commit()
        finally:
            connection.close()

        refreshed = refresh_exam_snapshots(db_path)

        connection = sqlite3.connect(db_path)
        try:
            snapshot = json.loads(
                connection.execute(
                    "SELECT snapshot_json FROM exam_instance_questions WHERE canonical_id = ?",
                    (question_id,),
                ).fetchone()[0]
            )
        finally:
            connection.close()

        self.assertEqual(refreshed, 40)
        self.assertEqual(snapshot["question"], "Chỉ còn đề bài.")

    def test_can_publish_multiple_quality_checked_exams_when_cross_exam_reuse_is_allowed(self):
        db_path = self._database_with_questions()

        exams = publish_standard_exams(db_path, count=10, seed_prefix="reused", allow_cross_exam_reuse=True)

        self.assertEqual(len(exams), 10)
        self.assertTrue(all(len(exam.question_ids) == 40 for exam in exams))


if __name__ == "__main__":
    unittest.main()
