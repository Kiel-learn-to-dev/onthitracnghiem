import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.curate_question_bank import curate_question_bank
from scripts.storage import create_database


class QuestionCurationTests(unittest.TestCase):
    def test_strips_source_number_and_excludes_unmatched_broken_ocr_from_release(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "review.db"
            create_database(db_path)
            connection = sqlite3.connect(db_path)
            try:
                connection.execute("INSERT INTO sources (id, filename, kind, checksum) VALUES (1, 'đề 1.pdf', 'pdf', 'clean')")
                connection.execute("INSERT INTO sources (id, filename, kind, checksum) VALUES (2, 'Câu hỏi ôn tập-e.pdf', 'pdf', 'ocr')")
                connection.execute(
                    """
                    INSERT INTO canonical_questions
                    (id, content_hash, question, choices_json, answer, explanation, topic, difficulty, solution_status)
                    VALUES (1, 'clean', 'Câu 32: Kiểu dữ liệu float có thể xử lí dữ liệu trong phạm vi nào:\na) Đúng.\nb) Sai.\nc) Sai.\nd) Sai.', ?, 'A', 'Giải thích', 'Kiểu dữ liệu', 'Dễ', 'approved')
                    """,
                    (json.dumps(["Đúng.", "Sai.", "Sai.", "Sai."]),),
                )
                connection.execute(
                    """
                    INSERT INTO canonical_questions
                    (id, content_hash, question, choices_json, answer, explanation, topic, difficulty, solution_status)
                    VALUES (2, 'ocr', 'Cau hoi 33. Kieu dur lieu float ??n 3.4*10^38.', ?, 'A', 'Giải thích', 'Kiểu dữ liệu', 'Dễ', 'approved')
                    """,
                    (json.dumps(["Ki?u", "Sai", "Sai", "Sai"]),),
                )
                for source_id, canonical_id in ((1, 1), (2, 2)):
                    connection.execute(
                        """
                        INSERT INTO source_questions
                        (source_id, source_label, ordinal, raw_question, raw_choices_json, canonical_id, difficulty, proposed_answer, solution, answer_status, extraction_status)
                        VALUES (?, '1', 1, 'raw', '[]', ?, 'Dễ', 'A', 'Giải thích', 'verified', 'approved')
                        """,
                        (source_id, canonical_id),
                    )
                connection.commit()
            finally:
                connection.close()

            report = curate_question_bank(db_path)

            self.assertEqual(report["excluded"], 1)
            connection = sqlite3.connect(db_path)
            try:
                clean = connection.execute("SELECT question, is_publishable FROM canonical_questions WHERE id = 1").fetchone()
                bad = connection.execute("SELECT is_publishable FROM canonical_questions WHERE id = 2").fetchone()
            finally:
                connection.close()
            self.assertEqual(clean, ("Kiểu dữ liệu float có thể xử lí dữ liệu trong phạm vi nào:", 1))
            self.assertEqual(bad, (0,))


if __name__ == "__main__":
    unittest.main()
