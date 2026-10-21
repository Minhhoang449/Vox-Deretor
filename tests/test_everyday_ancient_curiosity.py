"""Ensure the editorial revision reaches authoring without reusing old plots."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import channels

REVISION = "everyday-ancient-curiosity-v1-2026-10-21"


class EverydayAncientCuriosityTests(unittest.TestCase):
    def test_shared_scope_and_exclusions_reach_every_live_channel(self):
        config = channels.load_channel_config()
        scope = config["narration_dna"]["topic_scope"]
        self.assertEqual(config["editorial_revision"], REVISION)
        self.assertEqual(len(scope["borrowed_topics_not_for_production"]), 3)
        for c in channels.load_channels():
            self.assertEqual(c["editorial_revision"], REVISION)
            self.assertEqual(c["writing_contract"]["editorial_revision"], REVISION)
            self.assertEqual(c["packaging_direction"]["editorial_revision"], REVISION)
            self.assertTrue(c["writing_contract"]["humor_direction"])
            self.assertEqual(c["pilot_topics"], [])

    def test_previous_editorial_plot_is_not_silently_reused(self):
        for c in channels.load_channels():
            saved = channels._new_story_premise(c)
            saved.update(editorial_revision="previous-editorial-policy",
                         opening="Earlier lecture opening", answer="Earlier answer",
                         period="A recorded period", place="A recorded place")
            original = copy.deepcopy(saved)
            current = channels._authoring_premise({"story_premise": saved}, c)
            self.assertEqual(current["editorial_revision"], REVISION)
            self.assertEqual(current["opening"], "")
            self.assertEqual(current["answer"], "")
            self.assertEqual(current["period"], saved["period"])
            self.assertEqual(saved, original)

    def test_context_exposes_scope_and_preserves_recorded_speech(self):
        for original in channels.load_channels():
            with self.subTest(channel=original["id"]), tempfile.TemporaryDirectory() as folder:
                c = {**original, "destination": folder}
                with patch.object(channels, "resolve", return_value=c), contextlib.redirect_stdout(io.StringIO()):
                    channels.bind(c["id"], "editorial-test", topic="Explicit non-production test question")
                    path = Path(folder) / "editorial-test/beats.json"
                    doc = json.loads(path.read_text(encoding="utf-8"))
                    doc["beats"] = [{"narration": "Recorded speech remains intact"}]
                    path.write_text(json.dumps(doc), encoding="utf-8")
                    before = path.read_bytes()
                    ctx = channels.authoring_context(c["id"], "editorial-test")
                self.assertEqual(ctx["editorial_revision"], REVISION)
                self.assertEqual(ctx["topic_scope"]["revision"], REVISION)
                self.assertEqual(ctx["writing_contract"]["humor_direction"], c["writing_contract"]["humor_direction"])
                self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
