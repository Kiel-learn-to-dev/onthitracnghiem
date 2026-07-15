import sqlite3
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.import_htttql_html import import_htttql_html
from scripts.storage import create_database


class HtttqlHtmlImportTests(unittest.TestCase):
    def test_imports_source_questions_from_inline_html_dataset(self):
        html = textwrap.dedent(
            """
            <!doctype html>
            <script>
            const SOURCE_QUESTIONS = [{
              "id":"Câu 1",
              "sourceId":"1",
              "chapter":"Chương 1",
              "difficulty":"Dễ",
              "type":"Định nghĩa",
              "question":"Dữ liệu là gì?",
              "options":[
                {"key":"A","text":"Thông tin"},
                {"key":"B","text":"Dữ liệu thô"},
                {"key":"C","text":"Tri thức"},
                {"key":"D","text":"Báo cáo"}
              ],
              "correctAnswer":"B",
              "explanation":"Dữ liệu là sự kiện thô."
            }];
            </script>
            """
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "review.db"
            html_path = Path(temp_dir) / "htttql.html"
            html_path.write_text(html, encoding="utf-8")
            create_database(db_path)

            report = import_htttql_html(db_path, html_path)

            connection = sqlite3.connect(db_path)
            try:
                row = connection.execute(
                    """
                    SELECT subjects.slug, canonical_questions.question, canonical_questions.chapter,
                           canonical_questions.question_type, canonical_questions.difficulty,
                           canonical_questions.answer, canonical_questions.explanation
                    FROM canonical_questions
                    JOIN subjects ON subjects.id = canonical_questions.subject_id
                    WHERE canonical_questions.question = 'Dữ liệu là gì?'
                    """
                ).fetchone()
            finally:
                connection.close()

        self.assertEqual(report["imported"], 1)
        self.assertEqual(row, ("htttql", "Dữ liệu là gì?", "Chương 1", "Định nghĩa", "Dễ", "B", "Dữ liệu là sự kiện thô."))


if __name__ == "__main__":
    unittest.main()
