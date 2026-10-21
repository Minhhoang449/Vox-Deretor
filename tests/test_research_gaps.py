import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import research_gaps as rg  # noqa: E402

SCAN = {"top_models": [{"title": "What Did Ancient Egyptians Actually Eat?", "url": "u1",
                        "channel_title": "C1", "duration_seconds": 1635},
                       {"title": "Pyramid workers' food", "url": "u2", "channel_title": "C2", "duration_seconds": 0}]}


def draft(words):
    return "# T\n\n## Narration\n\n" + " ".join(["bread"] * words) + ".\n\n## Sources\n\n" + "x " * 5000


class GapTests(unittest.TestCase):
    def test_gap_opens_items_and_ignores_sources(self):
        r = rg.evaluate(draft(1500), 16, rg.models_from_scan(SCAN))  # 10 min
        self.assertTrue(r["gap"])
        self.assertEqual(r["status"], "open")
        self.assertEqual(r["minutes_to_fill"], 6.0)
        self.assertEqual(len(r["items"]), 4)
        self.assertTrue(all(i["status"] == "open" for i in r["items"]))
        self.assertIn("Never pad", r["rule"])
        self.assertIsNone(rg.models_from_scan(SCAN)[1]["length_minutes"])

    def test_no_gap(self):
        r = rg.evaluate(draft(2100), 16, [])  # 14 min >= 13.6
        self.assertFalse(r["gap"])
        self.assertEqual(r["status"], "no_gap")

    def test_closing_items(self):
        r = rg.evaluate(draft(1500), 16, [])
        for i in r["items"]:
            i["status"] = "sources_exhausted"
        self.assertEqual(rg.evaluate(draft(1500), 16, [], r)["status"], "open")  # no 'searched'
        for i in r["items"]:
            i["searched"] = ["Museo Egizio online catalogue"]
        self.assertEqual(rg.evaluate(draft(1500), 16, [], r)["status"], "closed")

    def test_sourced_needs_citation_and_filled_question(self):
        item = {"status": "sourced", "question": "[FILL] x", "source": "O. Cairo 25608"}
        self.assertFalse(rg.item_closed(item))
        item["question"] = "What did the bakery issue?"
        self.assertTrue(rg.item_closed(item))

    def test_target_from_beats(self):
        self.assertEqual(rg.target_from_packaging({"youtube_metadata": {"target_length": {"target_minutes": 12.0}}}), 12.0)
        self.assertIsNone(rg.target_from_packaging({}))

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            dp, sp = os.path.join(d, "lunch.md"), os.path.join(d, "scan.json")
            open(dp, "w").write(draft(1500))
            json.dump(SCAN, open(sp, "w"))
            self.assertEqual(rg.main(["--draft", dp, "--target-minutes", "16", "--scan", sp]), 2)
            md = open(os.path.join(d, "lunch-research-gaps.md")).read()
            self.assertIn("u1", md)
            self.assertEqual(rg.main(["--draft", dp, "--target-minutes", "10"]), 0)


if __name__ == "__main__":
    unittest.main()
