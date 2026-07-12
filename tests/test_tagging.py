import unittest

from scripts.tagging import classify_question


class DifficultyTaggingTests(unittest.TestCase):
    def test_preserves_a_verified_source_difficulty(self):
        result = classify_question(
            "Một câu bất kỳ",
            "200_cau_hoi_CSLT.xlsx",
            existing_difficulty="Rất khó",
        )

        self.assertEqual(result.difficulty, "Rất khó")
        self.assertEqual(result.status, "source_verified")

    def test_marks_direct_definition_as_easy(self):
        result = classify_question(
            "Kiểu dữ liệu int trong C dùng để lưu giá trị nào?",
            "Câu hỏi ôn tập-e.pdf",
        )

        self.assertEqual(result.difficulty, "Dễ")

    def test_marks_long_pointer_trace_as_very_hard(self):
        result = classify_question(
            "#include <stdio.h>\nint main(){ int **p; int a[10]; "
            "for(int i=0;i<10;i++){a[i]=i;} printf(\"%d\", **p); }" * 8,
            "đề 2.pdf",
        )

        self.assertEqual(result.difficulty, "Rất khó")


if __name__ == "__main__":
    unittest.main()
