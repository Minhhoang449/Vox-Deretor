import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from export_youtube import check_seo_metadata, check_chapters

T = "What Did Ancient Egyptians Eat? A Tomb Builder's Lunch"
D = ("What did ancient Egyptians eat for lunch? At Deir el-Medina the tomb builders were paid in grain. "
     "We follow the scribe Amennakht.")
TAGS = ["what did ancient egyptians eat", "ancient egyptian food", "deir el medina", "amennakht", "turin strike papyrus"]
P = ["what did ancient egyptians eat"]

class SeoMetadataTest(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(check_seo_metadata(T, D, TAGS, P), [])
    def test_too_many_tags(self):
        self.assertTrue(check_seo_metadata(T, D, TAGS + ["a", "b"], P))
    def test_too_few_tags(self):
        self.assertTrue(check_seo_metadata(T, D, TAGS[:2], P))
    def test_phrase_late_in_description(self):
        late = "Tomb builders were paid in grain. What did ancient Egyptians eat?"
        self.assertTrue(check_seo_metadata(T, late, TAGS, P))
    def test_phrase_missing_from_title(self):
        self.assertTrue(check_seo_metadata("Paid in Grain", D, TAGS, P))
    def test_japanese_sentences(self):
        self.assertEqual(check_seo_metadata("縄文人は栃の実をどう食べた？", "縄文人は栃の実を食べた。苦い。", ["a","b","c"], ["縄文人"]), [])

class ChaptersTest(unittest.TestCase):
    OK = [{"time": "00:00", "title": "Paid in grain"}, {"time": "01:10", "title": "Bread"}, {"time": "03:00", "title": "Strike"}]
    def test_none_ok(self):
        self.assertEqual(check_chapters([], ""), [])
    def test_measured_ok(self):
        self.assertEqual(check_chapters(self.OK, "measured", 600), [])
    def test_estimated_blocked(self):
        self.assertTrue(check_chapters(self.OK, "estimated"))
    def test_not_from_zero(self):
        self.assertTrue(check_chapters([dict(self.OK[0], time="00:05")] + self.OK[1:], "measured"))
    def test_too_short(self):
        self.assertTrue(check_chapters(self.OK[:2] + [{"time": "01:15", "title": "x"}], "measured"))
    def test_two_only(self):
        self.assertTrue(check_chapters(self.OK[:2], "measured"))


if __name__ == "__main__":
    unittest.main()
