"""Decision history must be traceable, append-only and separate from production."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import topic_memory as memory


class TopicMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "memory"
        self.config = memory.load_config()
        self.payload = {"channel_id": "battlefield-bearings", "candidate_id": "pompeii-laundry",
            "question": "How did people in Pompeii wash clothes?", "reason": "Bounded workshop evidence; market demand is uncertain.",
            "decision_source": "agent", "disposition": "research_next",
            "evidence_refs": ["research/report.md"]}

    def record(self, data=None):
        return memory.record_event(data or self.payload, root=self.root, config=self.config)

    def test_missing_store_reads_empty_without_creating_it(self):
        self.assertEqual(memory.history(root=self.root), [])
        self.assertEqual(memory.summaries(root=self.root), [])
        self.assertFalse(self.root.exists())

    def test_decisions_append_and_leave_original_input_and_file_unchanged(self):
        original = copy.deepcopy(self.payload)
        first = self.record()
        first_bytes = Path(first["path"]).read_bytes()
        revised = dict(self.payload, disposition="defer", reason="Need stronger source evidence.")
        self.record(revised)
        self.assertEqual(self.payload, original)
        self.assertEqual(Path(first["path"]).read_bytes(), first_bytes)
        self.assertEqual(len(memory.history(root=self.root)), 2)
        self.assertEqual(memory.summaries(root=self.root)[0]["latest_disposition"], "defer")

    def test_search_of_old_reason_returns_latest_decision_not_stale_recommendation(self):
        self.record(dict(self.payload, reason="An unusual washing workshop."))
        self.record(dict(self.payload, disposition="reject", reason="Essential premise was disproven."))
        found = memory.summaries(query="unusual", root=self.root)
        self.assertEqual(found[0]["latest_disposition"], "reject")
        self.assertEqual(len(memory.history(candidate="pompeii-laundry", root=self.root)), 2)

    def test_channel_filters_and_cross_channel_search_keep_separate_identities(self):
        self.record()
        self.record(dict(self.payload, channel_id="chikyu-shikumi", question="ポンペイの洗濯"))
        self.assertEqual(len(memory.summaries(root=self.root)), 2)
        self.assertEqual(len(memory.summaries(channel="chikyu-shikumi", root=self.root)), 1)

    def test_selected_for_development_requires_decision_reference_and_is_not_approval(self):
        data = dict(self.payload, disposition="selected_for_development")
        with self.assertRaises(ValueError):
            self.record(data)
        self.assertFalse(self.root.exists())
        data.update(decision_reference="User selected this question in the current conversation", decision_source="user")
        event = self.record(data)["event"]
        self.assertNotIn("narration_approved", event)
        self.assertEqual(event["disposition"], "selected_for_development")

    def outcome(self):
        data = {k:v for k,v in self.payload.items() if k != "disposition"}
        data.update(event_type="outcome", outcome={
            "source": "Supplied public snapshot", "period": "2026-10-21 snapshot",
            "video_url": "https://www.youtube.com/watch?v=example", "published_version": "Unknown narration version; public metadata only",
            "observations": ["Public views were supplied; retention unavailable."],
            "hypotheses": ["The opening may need a clearer promise; not measured here."]})
        return data

    def test_outcomes_do_not_overwrite_decision_or_fabricate_missing_metrics(self):
        self.record()
        self.record(self.outcome())
        summary = memory.summaries(root=self.root)[0]
        self.assertEqual(summary["latest_disposition"], "research_next")
        self.assertEqual(summary["outcome_count"], 1)
        outcome = memory.history(root=self.root)[-1]["outcome"]
        self.assertNotIn("ctr", outcome)
        self.assertNotIn("retention", outcome)

    def test_outcome_requires_evidence_and_published_version_context(self):
        data = self.outcome()
        data["evidence_refs"] = []
        with self.assertRaises(ValueError):
            self.record(data)
        data = self.outcome()
        del data["outcome"]["published_version"]
        with self.assertRaises(ValueError):
            self.record(data)
        self.assertFalse(self.root.exists())

    def test_invalid_inputs_do_not_create_store(self):
        for change in ({"channel_id": "../escape"}, {"candidate_id": "../../episode"},
                       {"channel_id": "retired-channel"}, {"disposition": "narration_approved"},
                       {"narration_approved": True}, {"question": ""}, {"decision_source": "guessed"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.record(dict(self.payload, **change))
        self.assertFalse(self.root.exists())

    def test_nontext_provenance_does_not_leave_a_partial_record(self):
        data = dict(self.payload, comparison_packet=float("nan"))
        with self.assertRaises(ValueError):
            self.record(data)
        self.assertFalse(self.root.exists())

    def test_outcome_cannot_hide_approval_flags_in_observation_data(self):
        data = self.outcome()
        data["outcome"]["narration_approved"] = True
        with self.assertRaises(ValueError):
            self.record(data)
        self.assertFalse(self.root.exists())

    def test_uuid_collision_does_not_overwrite_history(self):
        class FixedID:
            hex = "fixed-id-for-test"
        with patch.object(memory, "uuid4", return_value=FixedID()):
            first = self.record()
            before = Path(first["path"]).read_bytes()
            with self.assertRaises(FileExistsError):
                self.record(dict(self.payload, disposition="reject"))
        self.assertEqual(Path(first["path"]).read_bytes(), before)

    def test_malformed_history_is_reported_not_silently_forgotten(self):
        self.record()
        path = self.root / self.payload["channel_id"] / "bad.json"
        path.write_text("{broken", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Unreadable topic history"):
            memory.summaries(root=self.root)

    def test_configured_memory_root_cannot_escape_repository(self):
        config = copy.deepcopy(self.config)
        config.setdefault("topic_discovery", {})["decision_memory"] = {"root": "../outside"}
        with self.assertRaises(ValueError):
            memory.memory_root(config)


if __name__ == "__main__":
    unittest.main()
