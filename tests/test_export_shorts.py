import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from export_youtube import validate_shorts

OK = {"id": "s1", "title": "This village had no well", "source_passage": "The village lay",
      "hook": "No well. So how?", "closing_line": "The full route is in the video."}

class ShortsTest(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(len(validate_shorts({"shorts": [OK]}, "Long title", "en")), 1)
    def test_none_allowed(self):
        self.assertEqual(validate_shorts({}, "x", "en"), [])
    def test_missing_closing(self):
        with self.assertRaises(SystemExit):
            validate_shorts({"shorts": [dict(OK, closing_line="")]}, "x", "en")
    def test_duplicate_long(self):
        with self.assertRaises(SystemExit):
            validate_shorts({"shorts": [OK]}, OK["title"], "en")
    def test_ja_cap(self):
        with self.assertRaises(SystemExit):
            validate_shorts({"shorts": [dict(OK, title="栃" * 33)]}, "x", "ja")
    def test_max_three(self):
        with self.assertRaises(SystemExit):
            validate_shorts({"shorts": [dict(OK, title=str(i)) for i in range(4)]}, "x", "en")

if __name__ == "__main__":
    unittest.main()
