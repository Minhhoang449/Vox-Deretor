import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from export_youtube import check_seo_metadata

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
        late = "Tomb builders were paid in grain. Scribes wrote it down. What did ancient Egyptians eat?"
        self.assertTrue(check_seo_metadata(T, late, TAGS, P))
    def test_phrase_missing_from_title(self):
        self.assertTrue(check_seo_metadata("Paid in Grain", D, TAGS, P))
    def test_japanese_sentences(self):
        self.assertEqual(check_seo_metadata("縄文人は栃の実をどう食べた？", "縄文人は栃の実を食べた。苦い。", ["a","b","c"], ["縄文人"]), [])

if __name__ == "__main__":
    unittest.main()
