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
        self.assertIn('id="result-breakdown"', result_template)
        self.assertIn("unanswered", frontend)
        self.assertIn("renderResultQuestion", frontend)

    def test_home_page_can_show_recent_attempt_history_and_filter_published_subjects(self):
        home_template = (Path(__file__).parent.parent / "templates" / "home.html").read_text(encoding="utf-8")
        frontend = (Path(__file__).parent.parent / "frontend" / "app.ts").read_text(encoding="utf-8")

        self.assertIn('id="recent-attempts"', home_template)
        self.assertIn('id="recent-attempt-list"', home_template)
        self.assertIn('id="published-subject-select"', home_template)
        self.assertIn('id="history-subject-select"', home_template)
        self.assertIn('id="history-date-input"', home_template)
        self.assertIn('id="clear-history-filters"', home_template)
        self.assertIn('class="home-workspace"', home_template)
        self.assertIn('class="home-history-column"', home_template)
        self.assertIn("/api/attempts/recent", frontend)
        self.assertIn("submittedDate", frontend)
        self.assertIn("historySubjectSelect", frontend)
        self.assertIn("Đề có sẵn", frontend)
        self.assertIn("Đề ngẫu nhiên", frontend)


if __name__ == "__main__":
    unittest.main()
