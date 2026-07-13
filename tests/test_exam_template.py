import unittest
from pathlib import Path


class ExamTemplateTests(unittest.TestCase):
    def test_exam_page_does_not_show_a_loading_label_in_the_save_status_area(self):
        template = (Path(__file__).parent.parent / "templates" / "exam.html").read_text(encoding="utf-8")

        self.assertNotIn('id="save-status"', template)

    def test_result_page_matches_exam_navigation_with_a_side_explanation_pane(self):
        result_template = (Path(__file__).parent.parent / "templates" / "result.html").read_text(encoding="utf-8")
        frontend = (Path(__file__).parent.parent / "frontend" / "app.ts").read_text(encoding="utf-8")

        self.assertIn('id="result-question-nav"', result_template)
        self.assertIn('id="result-explanation"', result_template)
        self.assertIn("renderResultQuestion", frontend)


if __name__ == "__main__":
    unittest.main()
