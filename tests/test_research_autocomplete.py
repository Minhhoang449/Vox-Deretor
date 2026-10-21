import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "research_autocomplete", Path(__file__).resolve().parents[1] / "scripts/research_autocomplete.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

FAKE = {"amarna": ["amarnath yatra", "amarna letters"], "唐堀遺跡": [],
        "栃の実 食べ方": ["栃の実 食べ方", "栃餅"],
        "how did ancient egyptians": ["how did ancient egyptians live"]}


def fetcher(p, hl, gl):
    return FAKE[p]


class AutocompleteGateTests(unittest.TestCase):
    def test_labels(self):
        rows = {r["phrase"]: r["label"] for r in m.check_phrases(list(FAKE), "en", fetcher)}
        self.assertEqual(rows["唐堀遺跡"], "no_suggestions")
        self.assertEqual(rows["栃の実 食べ方"], "searched")
        self.assertEqual(rows["amarna"], "searched")  # 'amarna letters' contains it; intent still human-checked

    def test_unsearched_title_fails(self):
        rows = m.check_phrases(["唐堀遺跡"], "ja", fetcher)
        self.assertFalse(m.title_gate("唐堀遺跡の水場", rows, "ja")["pass"])

    def test_japanese_head_and_cap(self):
        rows = m.check_phrases(["栃の実 食べ方"], "ja", fetcher)
        self.assertTrue(m.title_gate("栃の実 食べ方を縄文人に学ぶ", rows, "ja")["pass"])

    def test_english_title_passes(self):
        rows = m.check_phrases(["how did ancient egyptians"], "en", fetcher)
        gate = m.title_gate("How Did Ancient Egyptians Get Water? A Village With No Well", rows, "en")
        self.assertTrue(gate["pass"], gate)

    def test_fetch_error_never_passes(self):
        def broken(*a):
            raise OSError("socket denied")
        rows = m.check_phrases(["x"], "en", broken)
        self.assertEqual(rows[0]["label"], "fetch_error")
        self.assertFalse(m.title_gate("x", rows, "en")["pass"])


if __name__ == "__main__":
    unittest.main()


class WholeWordTests(unittest.TestCase):
    def test_vietnamese_partial_word_is_not_searched(self):
        rows = m.check_phrases(["hà nội có bao nhiêu hồ"], "vi",
                               lambda *a: ["hà nội có bao nhiêu cây cầu bắc qua sông hồng"])
        self.assertEqual(rows[0]["label"], "check_intent")
