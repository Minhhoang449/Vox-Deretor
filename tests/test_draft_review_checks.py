import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "draft_review_checks", Path(__file__).resolve().parents[1] / "scripts/draft_review_checks.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DraftReviewChecksTests(unittest.TestCase):
    def test_repeated_paragraph_locates_both_lines(self):
        result = module.review("A supported task.\n\nAnother detail.\n\nA supported task.")
        finding = result["findings"][0]
        self.assertEqual((finding["line"], finding["related_line"]), (5, 1))

    def test_multilingual_single_sentence_flagged_but_diagnostic_only(self):
        result = module.review("縄文人の食事です。\n\nMột câu ngắn.")
        kinds = {f["kind"] for f in result["findings"]}
        self.assertIn("one_sentence_paragraph", kinds)
        self.assertNotIn("exact_paragraph_repeat", kinds)
        self.assertEqual(result["status"], "diagnostics_only")

    def test_studio_hedge_and_number_checks(self):
        text = ("The jar is 1.2 km away. It may be old.\n\nPerhaps 1.2 km. Likely so. Probably.\n\n"
                "Walk 1.2 km again. It might be true. Maybe.")
        kinds = {f["kind"] for f in module.review(text)["findings"]}
        self.assertTrue({"early_hedge", "hedge_density", "repeated_number"} <= kinds)

    def test_stale_quote_is_flagged(self):
        evidence = [{"line": 1, "quote": "standing", "source_locator": "dossier §2",
                     "support": "Object depiction"}]
        self.assertEqual(module.review("The worker sits.", evidence)["claim_mappings"][0]["status"], "needs_fix")

    def test_mapping_does_not_claim_verification(self):
        evidence = [{"line": 1, "quote": "sits", "source_locator": "dossier §2",
                     "support": "Figure posture; interpretation remains qualified"}]
        result = module.review("The worker sits.", evidence)
        self.assertEqual(result["claim_mappings"][0]["status"], "mapped_not_verified")
        self.assertEqual(result["evidence_coverage"], "not_established")

    def test_missing_source_and_invalid_records(self):
        self.assertTrue(module.review("Claim.", [{"line": 1, "quote": "Claim."}])["findings"])
        with self.assertRaises(ValueError):
            module.review("Claim.", {})


if __name__ == "__main__":
    unittest.main()
