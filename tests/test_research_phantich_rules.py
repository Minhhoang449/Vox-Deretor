import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import research_youtube as ry  # noqa: E402
import research_packaging as rp  # noqa: E402

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)


def row(vid, title, views, subs, days=10, dur=600):
    r = {"video_id": vid, "title": title, "views": views, "subscribers": subs, "channel_title": f"ch{vid}",
         "url": f"https://www.youtube.com/watch?v={vid}", "duration_seconds": dur,
         "published_at": f"2026-10-{21 - days:02d}T00:00:00Z"}
    return ry.add_ratios(r, NOW)


class SmallChannelTests(unittest.TestCase):
    def test_small_channel_not_breakout(self):
        r = row("a", "x", 900, 11)
        self.assertTrue(r["small_channel"])
        self.assertFalse(r["breakout"])
        self.assertIn("small channel, not counted", ry._ratio_label(r))

    def test_big_channel_breakout(self):
        r = row("b", "x", 900, 1000)
        self.assertFalse(r["small_channel"])
        self.assertTrue(r["breakout"])

    def test_sort_views_per_day(self):
        rows = [row("a", "x", 100, 500), row("b", "x", 1000, 500), row("c", "x", None, 500)]
        self.assertEqual([r["video_id"] for r in ry.sort_by_views_per_day(rows)], ["b", "a", "c"])


class SaturationTests(unittest.TestCase):
    def test_detects_cluster(self):
        titles = ["What Did Ancient Egyptians Eat?", "What Did Ancient Egyptians ACTUALLY Eat?",
                  "What did ancient Egyptians really eat", "What Did Ancient Egyptians Eat Every Day?",
                  "Building the pyramids"]
        rows = [row(str(i), t, 100, 500) for i, t in enumerate(titles)]
        clusters = ry.saturated_patterns(rows)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(len(clusters[0]["rows"]), 4)

    def test_three_is_not_saturated(self):
        rows = [row(str(i), "What Did Ancient Egyptians Eat?", 100, 500) for i in range(3)]
        self.assertEqual(ry.saturated_patterns(rows), [])


class TopModelsTests(unittest.TestCase):
    def test_top3_excludes_small(self):
        rows = [row("s", "x", 99999, 5), row("a", "x", 500, 200), row("b", "x", 5000, 200),
                row("c", "x", 50, 200), row("d", "x", 10, 200), row("b", "x", 5000, 200)]
        self.assertEqual([r["video_id"] for r in ry.top_models(rows)], ["b", "a", "c"])

    def test_report_sections(self):
        rows = [row(str(i), "What Did Ancient Egyptians Actually Eat?", 100 * (i + 1), 500) for i in range(4)]
        report = {"scanned_at_utc": "x", "method": {"order": "relevance"},
                  "channels": [{"display_name": "C", "relevance_language": "en", "region_code": "US",
                                "queries": [{"query": "q", "results": rows}]}]}
        md = ry.render_report(report, 10)
        self.assertIn("## Saturated title pattern", md)
        self.assertIn("distinct angle in the second half", md)
        self.assertIn("## Top 3 models to sit beside", md)
        self.assertIn("End screens can only link this channel's own videos", md)
        self.assertIn("length 10:00", md)


class TargetLengthTests(unittest.TestCase):
    def v(self, vid, subs, views, vpd, dur):
        return {"video_id": vid, "subscribers": subs, "views": views, "views_per_day": vpd, "duration_seconds": dur}

    def test_median_and_clamp(self):
        vids = [self.v("a", 200, 100, 50, 11 * 60), self.v("b", 200, 100, 40, 13 * 60),
                self.v("c", 200, 100, 30, 20 * 60), self.v("s", 10, 9999, 999, 60 * 60)]
        t = rp.target_length(vids)
        self.assertEqual(t["target_minutes"], 13.0)
        self.assertEqual(t["min_minutes_before_warning"], 11.0)
        self.assertNotIn("s", [x["video_id"] for x in t["videos"]])

    def test_clamped_high(self):
        t = rp.target_length([self.v("a", 500, 10, 5, 40 * 60)])
        self.assertEqual(t["target_minutes"], 16)
        self.assertTrue(t["clamped"])

    def test_none_when_no_strong(self):
        self.assertIsNone(rp.target_length([self.v("a", 5, 10, 5, 600)]))

    def test_remember_writes_field(self):
        doc = {}
        rp.remember(doc, ["q"], ["relevance"], "r.md", 1, "", {"target_minutes": 12.0})
        self.assertEqual(doc["youtube_metadata"]["target_length"]["target_minutes"], 12.0)


if __name__ == "__main__":
    unittest.main()
