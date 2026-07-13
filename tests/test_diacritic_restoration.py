import unittest

from scripts.restore_diacritics import best_authoritative_match, restore_vietnamese_phrases, restore_ocr_quotes


class DiacriticRestorationTests(unittest.TestCase):
    def test_matches_an_ocr_question_to_its_diacritic_source(self):
        target = "Ham gotoxy(int x, int y) la ham:"
        candidates = [
            (295, "Hàm gotoxy(int x, int y) là hàm:"),
            (201, "Ba màu cơ bản trong máy tính là:"),
        ]

        match_id, score = best_authoritative_match(target, candidates)

        self.assertEqual(match_id, 295)
        self.assertGreaterEqual(score, 0.95)

    def test_ignores_ocr_answer_notes_after_the_question_stem(self):
        target = """Ham gotoxy(int x, int y) la ham:
b
gotoxy(int x, int y): di chuyen con tro toi vi tri cot x, dong y."""

        match_id, score = best_authoritative_match(
            target,
            [(295, "Hàm gotoxy(int x, int y) là hàm:")],
        )

        self.assertEqual(match_id, 295)
        self.assertGreaterEqual(score, 0.95)

    def test_restores_common_programming_vietnamese_without_changing_c_code(self):
        text = "Ngon ngu lap trinh C duoc phat trien dua tren ngon ngu B va BCPL."

        self.assertEqual(
            restore_vietnamese_phrases(text),
            "Ngôn ngữ lập trình C được phát triển dựa trên ngôn ngữ B và BCPL.",
        )

    def test_restores_lost_quotation_marks_around_program_output(self):
        self.assertEqual(restore_ocr_quotes("?29h?."), "“29h”.")


if __name__ == "__main__":
    unittest.main()
