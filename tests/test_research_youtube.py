import json
import os
import sys
import unittest
from datetime import datetime, timezone
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import research_youtube as ry  # noqa: E402

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)


class RatioTests(unittest.TestCase):
    def test_breakout_and_per_day(self):
        row = ry.add_ratios({"views": 800, "subscribers": 1000, "published_at": "2026-10-11T00:00:00Z"}, NOW)
        self.assertEqual(row["views_per_sub"], 0.8)
        self.assertTrue(row["breakout"])
        self.assertEqual(row["views_per_day"], 80.0)

    def test_hidden_subs_unavailable(self):
        row = ry.add_ratios({"views": 5000, "subscribers": None, "published_at": "2026-10-11T00:00:00Z"}, NOW)
        self.assertIsNone(row["views_per_sub"])
        self.assertFalse(row["breakout"])
        self.assertEqual(ry._num(row["views_per_sub"]), "unavailable")

    def test_channel_stats_hidden(self):
        out = ry.parse_channel_stats({"items": [
            {"id": "a", "statistics": {"subscriberCount": "68"}},
            {"id": "b", "statistics": {"hiddenSubscriberCount": True}},
        ]})
        self.assertEqual(out, {"a": 68, "b": None})

    def test_order_list_dedupe(self):
        args = ry.parse_args(["--order", "date,relevance,date"])
        self.assertEqual(args["orders"], ["date", "relevance"])
        self.assertEqual(ry.parse_args([])["orders"], ["relevance", "date"])
        self.assertEqual(ry.parse_args([])["top_per_query"], 10)


class YtDlpParsingTests(unittest.TestCase):
    def test_search_lines(self):
        out = "\n".join(json.dumps(x) for x in [{"id": "v1", "ie_key": "Youtube"}, {"id": "v1"}, {"id": "v2"}]) + "\nnot json\n"
        self.assertEqual(ry.parse_ytdlp_search(out), ["v1", "v2"])

    def test_row_from_info(self):
        row = ry.row_from_ytdlp({"id": "v1", "title": "T", "channel": "C", "view_count": 120,
                                 "channel_follower_count": 68, "duration": 600, "upload_date": "20261001"}, 1)
        self.assertEqual(row["published_at"], "2026-10-01T00:00:00Z")
        self.assertEqual(row["subscribers"], 68)
        ry.add_ratios(row, NOW)
        # 68 subscribers is below the 100-sub floor: ratio shown, not counted as breakout.
        self.assertFalse(row["breakout"])
        self.assertTrue(row["small_channel"])

    def test_blocked_video_recorded(self):
        search = mock.Mock(returncode=0, stdout=json.dumps({"id": "v1"}) + "\n", stderr="")
        blocked = mock.Mock(returncode=1, stdout="", stderr="ERROR: Sign in to confirm you're not a bot")
        failures = []
        with mock.patch.object(ry, "_run_ytdlp", side_effect=[search, blocked]):
            rows = ry.ytdlp_query("q", "relevance", 5, failures)
        self.assertIsNone(rows[0]["views"])
        self.assertIn("not a bot", failures[0]["error"])

    def test_report_renders_breakout_and_failures(self):
        row = ry.add_ratios(ry.row_from_ytdlp({"id": "v1", "title": "T", "channel": "C", "view_count": 900,
                                               "channel_follower_count": 100, "upload_date": "20261001"}, 1), NOW)
        report = {"scanned_at_utc": "x", "method": {"order": "relevance", "source": "yt-dlp"},
                  "failed_cells": [{"query": "q", "order": "date", "cell": "search", "error": "bot"}],
                  "channels": [{"display_name": "D", "relevance_language": "en", "region_code": "US",
                                "queries": [{"query": "q", "order": "relevance", "results": [row]}]}]}
        md = ry.render_report(report, 10)
        self.assertIn("Breakout videos (>=0.8 views/sub)", md)
        self.assertIn("9.00", md)
        self.assertIn("yt-dlp", md)
        self.assertIn("Cells that could not be fetched", md)


if __name__ == "__main__":
    unittest.main()
