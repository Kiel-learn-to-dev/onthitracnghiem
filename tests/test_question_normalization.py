import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.normalize_questions import normalize_choices
from scripts.storage import create_database


class QuestionNormalizationTests(unittest.TestCase):
    def test_splits_embedded_choices_and_preserves_original_raw_text(self):
        raw = """Câu 2. Biến con trỏ có thể chứa:
a) Địa chỉ vùng nhớ của một biến khác.
b) Giá trị của một biến khác.
c) Cả a và b đều đúng.
d) Cả a và b đều sai."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "review.db"
            create_database(db_path)
            connection = sqlite3.connect(db_path)
            try:
                with connection:
                    source_id = connection.execute(
                        "INSERT INTO sources(filename, kind, checksum) VALUES ('sample.pdf', 'pdf', 'x')"
                    ).lastrowid
                    connection.execute(
                        """
                        INSERT INTO source_questions
                        (source_id, source_label, ordinal, raw_question, raw_choices_json)
                        VALUES (?, 'Câu 2', 1, ?, '[]')
                        """,
                        (source_id, raw),
                    )
            finally:
                connection.close()

            result = normalize_choices(db_path)

            connection = sqlite3.connect(db_path)
            try:
                row = connection.execute(
                    "SELECT raw_question, normalized_question, raw_choices_json, choice_parse_reason "
                    "FROM source_questions"
                ).fetchone()
            finally:
                connection.close()

        self.assertEqual(result["normalized"], 1)
        self.assertEqual(row[0], raw)
        self.assertEqual(row[1], "Câu 2. Biến con trỏ có thể chứa:")
        self.assertEqual(len(json.loads(row[2])), 4)
        self.assertIsNone(row[3])

    def test_extracts_a_clean_stem_even_when_choices_were_previously_filled(self):
        raw = """Câu 227: Ba màu cơ bản là:
a) RED, GREEN, BLUE.
b) RED, YELLOW, BLUE.
c) BLUE, YELLOW, BLUE."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "review.db"
            create_database(db_path)
            connection = sqlite3.connect(db_path)
            try:
                with connection:
                    source_id = connection.execute(
                        "INSERT INTO sources(filename, kind, checksum) VALUES ('sample.pdf', 'pdf', 'x')"
                    ).lastrowid
                    connection.execute(
                        """
                        INSERT INTO source_questions
                        (source_id, source_label, ordinal, raw_question, raw_choices_json)
                        VALUES (?, 'Câu 227', 1, ?, ?)
                        """,
                        (source_id, raw, json.dumps(["A", "B", "C", "D"])),
                    )
            finally:
                connection.close()

            normalize_choices(db_path)

            connection = sqlite3.connect(db_path)
            try:
                normalized_question = connection.execute(
                    "SELECT normalized_question FROM source_questions"
                ).fetchone()[0]
            finally:
                connection.close()

        self.assertEqual(normalized_question, "Câu 227: Ba màu cơ bản là:")


if __name__ == "__main__":
    unittest.main()
