"""Regression checks for topic isolation and live channel documentary authoring context."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import channels


class EpisodeContextTests(unittest.TestCase):
    def setUp(self):
        self.base = ROOT / "tmp" / "topic-context-tests"
        self.base.mkdir(parents=True, exist_ok=True)
        self.folder = self.base / uuid.uuid4().hex
        self.folder.mkdir()
        self.channel = copy.deepcopy(channels.resolve("vi-sao-noi-nay"))
        self.channel["destination"] = str(self.folder)
        self.resolve_patch = patch.object(channels, "resolve", return_value=self.channel)
        self.resolve_patch.start()
        self.addCleanup(self.resolve_patch.stop)
        self.addCleanup(self.cleanup_folder)

    def cleanup_folder(self):
        target = self.folder.resolve()
        if target.parent != self.base.resolve():
            raise RuntimeError("Test cleanup escaped its workspace directory.")
        shutil.rmtree(target)

    def bind(self, slug, topic=None):
        with contextlib.redirect_stdout(io.StringIO()):
            channels.bind("vi-sao-noi-nay", slug, topic=topic)
        return self.read(slug)

    def path(self, slug):
        return self.folder / slug / "beats.json"

    def read(self, slug):
        return json.loads(self.path(slug).read_text(encoding="utf-8"))

    def write(self, slug, doc):
        self.path(slug).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    def test_new_topic_gets_channel_premise_and_separate_empty_production(self):
        old = self.bind("old-topic", "Can a city be rescued from water failure?")
        old["beats"] = [{"narration": "Approved old water story."}]
        old["youtube_metadata"]["description"] = "Old water package"
        old["story_premise"]["objective"] = "Restore the water system"
        self.write("old-topic", old)
        before = self.path("old-topic").read_bytes()
        new = self.bind("new-topic", "Can the Sahara be greened sustainably?")
        self.assertEqual(new["topic"], "Can the Sahara be greened sustainably?")
        self.assertEqual(new["story_premise"]["format"], self.channel["story_format"])
        self.assertEqual(new["story_premise"]["central_question"], "")
        self.assertEqual(new["story_premise"]["consequences"], [])
        self.assertNotIn("daily_goal", new["story_premise"])
        self.assertEqual(new["beats"], [])
        self.assertEqual(new["youtube_metadata"]["description"], "")
        self.assertEqual(new["youtube_metadata"]["selected_candidate_id"], "")
        self.assertEqual(self.path("old-topic").read_bytes(), before)
        self.assertEqual(channels.authoring_context("vi-sao-noi-nay", "new-topic")["topic"], new["topic"])

    def test_conflicting_rebind_refuses_before_any_write(self):
        self.bind("episode", "Find water")
        before = self.path("episode").read_bytes()
        with self.assertRaisesRegex(SystemExit, "new slug"):
            self.bind("episode", "Find a job")
        self.assertEqual(self.path("episode").read_bytes(), before)

    def test_resume_preserves_approved_story_and_explicit_production_settings(self):
        doc = self.bind("episode", "Find water")
        doc["beats"] = [{"narration": "Approved words", "shots": [{"id": "kept"}]}]
        doc["tts_speed"] = 1.0
        doc["tts_pause_after_period_seconds"] = 0.3
        doc["story_premise"]["objective"] = "Restore a supply network"
        doc["youtube_metadata"]["selected_candidate_id"] = "approved-thumb"
        self.write("episode", doc)
        resumed = self.bind("episode", "  FIND   WATER  ")
        for key in ("topic", "beats", "tts_speed", "tts_pause_after_period_seconds", "story_premise", "youtube_metadata"):
            self.assertEqual(resumed[key], doc[key])

    def test_context_uses_current_dna_and_direction_without_mutating_approved_data(self):
        doc = self.bind("episode", "Find water")
        doc["narration_dna"] = {"revision": "obsolete-documentary"}
        doc["channel"]["narration_direction"] = "old documentary direction"
        self.write("episode", doc)
        before = self.path("episode").read_bytes()
        current = channels.authoring_context("vi-sao-noi-nay", "episode")
        self.assertEqual(current["narration_dna"], channels.load_channel_config()["narration_dna"])
        self.assertEqual(current["narration_direction"], self.channel["narration_direction"])
        self.assertEqual(self.path("episode").read_bytes(), before)

    def test_channel_mismatch_is_rejected_without_rebinding(self):
        doc = self.bind("episode", "Find water")
        doc["channel_id"] = "levi-solace"
        self.write("episode", doc)
        before = self.path("episode").read_bytes()
        with self.assertRaisesRegex(SystemExit, "channel mismatch"):
            self.bind("episode")
        with self.assertRaisesRegex(SystemExit, "channel mismatch"):
            channels.authoring_context("vi-sao-noi-nay", "episode")
        self.assertEqual(self.path("episode").read_bytes(), before)

    def test_slug_mismatch_is_rejected(self):
        doc = self.bind("episode", "Find water")
        doc["episode_slug"] = "other-episode"
        self.write("episode", doc)
        with self.assertRaisesRegex(SystemExit, "slug mismatch"):
            channels.authoring_context("vi-sao-noi-nay", "episode")

    def test_topic_and_context_disagreement_is_rejected(self):
        doc = self.bind("episode", "Find water")
        doc["topic"] = "Find a job"
        self.write("episode", doc)
        with self.assertRaisesRegex(SystemExit, "topic conflicts"):
            self.bind("episode")
        with self.assertRaisesRegex(SystemExit, "topic conflicts"):
            channels.authoring_context("vi-sao-noi-nay", "episode")

    def test_empty_binding_cannot_silently_draft_a_pilot_topic(self):
        self.bind("episode")
        with self.assertRaisesRegex(SystemExit, "No selected episode topic"):
            channels.authoring_context("vi-sao-noi-nay", "episode")
        self.bind("episode", "Explicit selected topic")
        self.assertEqual(channels.authoring_context("vi-sao-noi-nay", "episode")["topic"], "Explicit selected topic")

    def test_existing_unidentified_production_cannot_receive_a_new_topic(self):
        doc = self.bind("episode")
        doc["beats"] = [{"narration": "An old story without a recorded topic"}]
        self.write("episode", doc)
        before = self.path("episode").read_bytes()
        with self.assertRaisesRegex(SystemExit, "Existing production has no recorded topic"):
            self.bind("episode", "A new topic")
        self.assertEqual(self.path("episode").read_bytes(), before)

    def test_missing_episode_does_not_resume_another_slug(self):
        self.bind("old-topic", "Find water")
        with self.assertRaisesRegex(SystemExit, "No episode at this slug"):
            channels.authoring_context("vi-sao-noi-nay", "new-topic")
        self.assertFalse((self.folder / "new-topic").exists())

    def test_legacy_episode_context_is_read_only_and_does_not_rewrite_old_format(self):
        doc = self.bind("episode", "Find water")
        doc.pop("episode_context")
        doc.pop("story_premise")
        doc["beats"] = [{"narration": "Legacy approved story"}]
        self.write("episode", doc)
        handoff = self.folder / "episode" / "PROJECT_HANDOFF.md"
        handoff.write_text("Existing approved story; inspect before editing.", encoding="utf-8")
        before = self.path("episode").read_bytes()
        current = channels.authoring_context("vi-sao-noi-nay", "episode")
        self.assertEqual(current["topic"], "Find water")
        self.assertEqual(current["story_premise"]["format"], self.channel["story_format"])
        self.assertIn(str(handoff), current["identity_documents"])
        self.assertEqual(self.path("episode").read_bytes(), before)

    def test_explicit_episode_format_exception_is_preserved(self):
        doc = self.bind("episode", "Find water")
        doc["story_premise"] = {"format": "documented_event", "exception_reason": "Explicit requested battle account"}
        self.write("episode", doc)
        current = channels.authoring_context("vi-sao-noi-nay", "episode")["story_premise"]
        self.assertEqual(current["format"], "documented_event")
        self.assertEqual(current["exception_reason"], doc["story_premise"]["exception_reason"])

    def test_old_format_snapshot_without_explicit_exception_does_not_override_current_dna(self):
        doc = self.bind("episode", "Find water")
        doc["story_premise"] = {"format": "time_traveler_life", "period": "Selected historical period",
                                "daily_goal": "Find dinner", "protagonist_status": "fictional_present_day_traveler"}
        self.write("episode", doc)
        before = self.path("episode").read_bytes()
        current = channels.authoring_context("vi-sao-noi-nay", "episode")["story_premise"]
        self.assertEqual(current["format"], self.channel["story_format"])
        self.assertEqual(current["period"], "Selected historical period")
        self.assertNotIn("daily_goal", current)
        self.assertNotIn("protagonist_status", current)
        self.assertEqual(channels.authoring_context("vi-sao-noi-nay", "episode")["recorded_story_premise"], doc["story_premise"])
        self.assertEqual(self.path("episode").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
