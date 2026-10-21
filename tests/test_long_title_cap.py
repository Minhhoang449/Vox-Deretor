import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from export_youtube import long_title_cap

class LongTitleCapTest(unittest.TestCase):
    def test_english(self):
        t = "How Did Ancient Egyptians Get Water? A Village With No Well"
        self.assertEqual(long_title_cap(t), 60)
        self.assertLessEqual(len(t), 60)
    def test_vietnamese_uses_60(self):
        self.assertEqual(long_title_cap("Vì sao Hà Nội có nhiều hồ?"), 60)
    def test_japanese(self):
        t = "縄文人は栃の実をどう食べた？20メートルの水場の謎"
        self.assertEqual(long_title_cap(t), 32)
        self.assertLessEqual(len(t), 32)
    def test_too_long_english(self):
        self.assertGreater(len("x" * 61), long_title_cap("x" * 61))

if __name__ == "__main__":
    unittest.main()
