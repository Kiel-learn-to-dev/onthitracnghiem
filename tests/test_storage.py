import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.import_excel import import_excel
from scripts.import_text_pdfs import import_text_pdf
from scripts.storage import create_database


class StorageSchemaTests(unittest.TestCase):
    def test_creates_tables_and_enforces_difficulty_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "review.db"
            create_database(db_path)

            connection = sqlite3.connect(db_path)
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                self.assertTrue(
                    {"sources", "source_questions", "canonical_questions", "solution_audit"}
                    .issubset(tables)
                )
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "INSERT INTO canonical_questions "
                        "(question, choices_json, answer, explanation, topic, difficulty) "
                        "VALUES ('Q', '[]', 'A', 'G', 'T', 'Không xác định')"
                    )
            finally:
                connection.close()

    def test_imports_all_excel_questions_with_explanations(self):
        workbook = Path(__file__).parent.parent / "200_cau_hoi_CSLT.xlsx"
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "review.db"
            create_database(db_path)
            import_excel(db_path, workbook)

            connection = sqlite3.connect(db_path)
            try:
                source_count = connection.execute(
                    "SELECT COUNT(*) FROM source_questions"
                ).fetchone()[0]
                canonical_count = connection.execute(
                    "SELECT COUNT(*) FROM canonical_questions"
                ).fetchone()[0]
                solved = connection.execute(
                    "SELECT explanation, difficulty, solution_status "
                    "FROM canonical_questions WHERE id = 1"
                ).fetchone()
            finally:
                connection.close()

        self.assertEqual(source_count, 200)
        self.assertEqual(canonical_count, 200)
        self.assertTrue(solved[0])
        self.assertIn(solved[1], {"Khó", "Rất khó"})
        self.assertEqual(solved[2], "drafted")

    def test_imports_text_pdf_question_occurrences(self):
        root = Path(__file__).parent.parent
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "review.db"
            create_database(db_path)
            import_text_pdf(db_path, root / "đề 2.pdf")
            import_text_pdf(db_path, root / "đề 1.pdf")

            connection = sqlite3.connect(db_path)
            try:
                counts = dict(
                    connection.execute(
                        """
                        SELECT sources.filename, COUNT(source_questions.id)
                        FROM sources
                        JOIN source_questions ON source_questions.source_id = sources.id
                        GROUP BY sources.filename
                        """
                    ).fetchall()
                )
            finally:
                connection.close()

        self.assertEqual(counts["đề 2.pdf"], 50)
        self.assertEqual(counts["đề 1.pdf"], 241)


if __name__ == "__main__":
    unittest.main()
