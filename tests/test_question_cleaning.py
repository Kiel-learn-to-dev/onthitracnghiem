import unittest

from scripts.question_cleaning import clean_question_text, is_safe_for_release


class QuestionCleaningTests(unittest.TestCase):
    def test_removes_source_number_and_embedded_answer_options_from_stem(self):
        raw = """Câu 32: Kiểu dữ liệu float có thể xử lí dữ liệu trong phạm vi nào:
a) 3.4*10-38 đến 3.4*1038.
b) -32768 đến 32767.
c) -128 đến 127.
d) 0…65535."""

        self.assertEqual(
            clean_question_text(raw),
            "Kiểu dữ liệu float có thể xử lí dữ liệu trong phạm vi nào:",
        )

    def test_rejects_ocr_text_with_replacement_marks_from_release_pool(self):
        self.assertFalse(is_safe_for_release("Ki?u d? li?u float ??n 3.4*10^38."))
        self.assertTrue(is_safe_for_release("Kiểu dữ liệu float đến 3.4×10^38."))


    def test_removes_choices_when_ocr_misses_the_last_option_delimiter(self):
        raw = """Cau hoi 33.Kieu dur lieu float co the xur li du lieu trong pham vi nao:
a

a)3.4*10-38den3.4*1038.
b)-32768den32767.
c)-128 den 127.
d0...65535."""

        self.assertEqual(
            clean_question_text(raw),
            "Kieu dur lieu float co the xur li du lieu trong pham vi nao:",
        )


if __name__ == "__main__":
    unittest.main()
