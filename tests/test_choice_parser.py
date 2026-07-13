import unittest

from scripts.choice_parser import parse_question_choices


class ChoiceParserTests(unittest.TestCase):
    def test_extracts_four_lettered_choices_and_removes_them_from_stem(self):
        raw = """Câu 2. Biến con trỏ có thể chứa:
a) Địa chỉ vùng nhớ của một biến khác.
b) Giá trị của một biến khác.
c) Cả a và b đều đúng.
d) Cả a và b đều sai."""

        result = parse_question_choices(raw)

        self.assertTrue(result.is_complete)
        self.assertEqual(result.question, "Câu 2. Biến con trỏ có thể chứa:")
        self.assertEqual(
            result.choices,
            [
                "Địa chỉ vùng nhớ của một biến khác.",
                "Giá trị của một biến khác.",
                "Cả a và b đều đúng.",
                "Cả a và b đều sai.",
            ],
        )

    def test_accepts_dot_labels_with_indentation(self):
        raw = """Câu 1.
    a. Phương án một.
    b. Phương án hai.
    c. Phương án ba.
    d. Phương án bốn."""

        result = parse_question_choices(raw)

        self.assertTrue(result.is_complete)
        self.assertEqual(result.choices[3], "Phương án bốn.")

    def test_reports_missing_choice_without_inventing_one(self):
        raw = """Câu 227: Ba màu cơ bản là:
a) RED, GREEN, BLUE.
b) RED, YELLOW, BLUE.
c) BLUE, YELLOW, BLUE."""

        result = parse_question_choices(raw)

        self.assertFalse(result.is_complete)
        self.assertEqual(result.reason, "missing choices: D")

    def test_extracts_inline_choices(self):
        raw = "Câu 191. Tổng số phần tử là? a)m phần tử b)n phần tử c)m + n phần tử d)m * n phần tử"

        result = parse_question_choices(raw)

        self.assertTrue(result.is_complete)
        self.assertEqual(result.question, "Câu 191. Tổng số phần tử là?")
        self.assertEqual(result.choices, ["m phần tử", "n phần tử", "m + n phần tử", "m * n phần tử"])

    def test_maps_a_four_choice_sequence_with_nonstandard_labels_to_a_through_d(self):
        raw = "Câu 27. Giá trị biểu thức là gì?\ne) -1.\nf) 0.\ng) 1.\nh) Không câu nào đúng."

        result = parse_question_choices(raw)

        self.assertTrue(result.is_complete)
        self.assertEqual(result.choices, ["-1.", "0.", "1.", "Không câu nào đúng."])

    def test_does_not_treat_a_variable_before_parenthesis_as_a_choice_label(self):
        raw = """Câu 20. Biểu thức nào sai?
a) (c = a & b).
b) (c = a && b).
c) (c = a / b).
d) (c = a << b)."""

        result = parse_question_choices(raw)

        self.assertTrue(result.is_complete)
        self.assertEqual(result.choices[0], "(c = a & b).")


if __name__ == "__main__":
    unittest.main()
