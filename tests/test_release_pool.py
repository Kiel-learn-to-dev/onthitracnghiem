import unittest

from scripts.release_pool import classify_topic


class ReleasePoolTests(unittest.TestCase):
    def test_classifies_distinct_programming_topics(self):
        self.assertEqual(classify_topic("Con trỏ trỏ đến vùng nhớ nào?"), "Con trỏ và bộ nhớ")
        self.assertEqual(classify_topic("Mảng một chiều có bao nhiêu phần tử?"), "Mảng và chuỗi")
        self.assertEqual(classify_topic("Vòng lặp for chạy bao nhiêu lần?"), "Điều khiển luồng")


if __name__ == "__main__":
    unittest.main()
