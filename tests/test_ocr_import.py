import unittest

from scripts.import_scanned_pdf import split_ocr_questions


class ScannedPdfParsingTests(unittest.TestCase):
    def test_splits_question_rows_from_ocr_text(self):
        lines = [
            "Cau hoi 8. Kieu du lieu nao la co ban?",
            "a) Kieu double.",
            "b) Kieu con tro.",
            "Cau hoi 9. Bieu thuc nao sai?",
            "a) a += b",
        ]

        questions = split_ocr_questions(lines)

        self.assertEqual([item[0] for item in questions], [8, 9])
        self.assertIn("Kieu du lieu", questions[0][1])
        self.assertIn("a += b", questions[1][1])

    def test_accepts_headings_without_the_word_hoi(self):
        questions = split_ocr_questions(["Cau 223: Chon cau dung.", "a) Lua chon A"])

        self.assertEqual(questions, [(223, "Cau 223: Chon cau dung.\na) Lua chon A")])

    def test_corrects_common_ocr_digits_in_question_numbers(self):
        questions = split_ocr_questions(["Cau hoi 2o7. Cau hoi ve ham."])

        self.assertEqual(questions, [(207, "Cau hoi 2o7. Cau hoi ve ham.")])


if __name__ == "__main__":
    unittest.main()
