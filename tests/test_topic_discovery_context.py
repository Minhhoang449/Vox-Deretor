"""Live, market-specific topic context must be available before production binding."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import channels
from editorial_policy import execution_contract


class TopicDiscoveryContextTests(unittest.TestCase):
    def test_real_scout_cli_parses_and_exposes_all_four_editorial_checks(self):
        result = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts/channels.py"),
                                 "scout", "battlefield-bearings"], cwd=ROOT,
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)
        for key in ("curiosity_check", "angle_trials", "challenge_pass", "decision_memory"):
            self.assertIn(key, context["topic_discovery"])
        self.assertIn("topic_memory", context)
        self.assertFalse(context["episode_created"])

    def test_scout_resolves_all_six_native_markets_and_channel_lenses(self):
        seen = set()
        for profile in channels.load_channels():
            result = channels.scouting_context(profile["id"])
            seen.add(result["channel_lens"]["story_format"])
            market = profile["youtube_research"]
            self.assertEqual(result["query_contract"], {
                "query_language": market["relevance_language"],
                "relevance_language": market["relevance_language"],
                "region_code": market["region_code"],
            })
            self.assertEqual(result["channel_lens"]["writing_contract"], profile["writing_contract"])
            self.assertFalse(result["episode_created"])
        self.assertEqual(len(seen), 6)

    def test_scout_never_binds_or_resolves_an_episode_path(self):
        profile = copy.deepcopy(channels.resolve("battlefield-bearings"))
        with tempfile.TemporaryDirectory() as folder:
            profile["destination"] = str(Path(folder) / "does-not-exist")
            with patch.object(channels, "resolve", return_value=profile), \
                 patch.object(channels, "bind", side_effect=AssertionError("must not bind")), \
                 patch.object(channels, "episode_dir", side_effect=AssertionError("must not resolve an episode")):
                channels.scouting_context(profile["id"])
            self.assertFalse(Path(profile["destination"]).exists())

    def test_scout_rejects_retired_profiles(self):
        profile = copy.deepcopy(channels.load_channels()[0])
        profile["profile_status"] = "archived"
        with patch.object(channels, "resolve", return_value=profile), self.assertRaises(SystemExit):
            channels.scouting_context(profile["id"])

    def test_missing_market_is_not_silently_invented(self):
        profile = copy.deepcopy(channels.load_channels()[0])
        profile["youtube_research"].pop("region_code")
        with patch.object(channels, "resolve", return_value=profile), self.assertRaises(SystemExit):
            channels.scouting_context(profile["id"])

    def test_scout_and_show_read_changed_live_discovery_policy(self):
        config = copy.deepcopy(channels.load_channel_config())
        config["topic_discovery"]["revision"] = "future-policy-test"
        config["narration_dna"]["question_design"]["default_shape"] = "future-shape-test"
        with patch.object(channels, "load_channel_config", return_value=config):
            result = channels.scouting_context(config["channels"][0]["id"])
            self.assertEqual(result["topic_discovery"]["revision"], "future-policy-test")
            self.assertEqual(result["question_design"]["default_shape"], "future-shape-test")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                channels.show(config["channels"][0]["id"])
            self.assertEqual(json.loads(output.getvalue())["topic_discovery"]["revision"], "future-policy-test")

    def test_context_exposes_live_rules_without_rewriting_approved_production(self):
        profile = copy.deepcopy(channels.load_channels()[0])
        with tempfile.TemporaryDirectory() as folder:
            profile["destination"] = folder
            episode = Path(folder) / "existing-topic"
            episode.mkdir()
            doc = {"channel_id": profile["id"], "episode_slug": "existing-topic",
                   "topic": "Recorded selected question", "narration_approved": True,
                   "story_premise": {"format": "legacy-format", "opening": "Approved recorded words"},
                   "animation_style": "documentary-realistic", "beats": []}
            source = episode / "beats.json"
            source.write_text(json.dumps(doc), encoding="utf-8")
            before = source.read_bytes()
            with patch.object(channels, "resolve", return_value=profile):
                result = channels.authoring_context(profile["id"], "existing-topic")
            live = channels.load_channel_config()
            self.assertEqual(result["question_design"], live["narration_dna"]["question_design"])
            self.assertEqual(result["topic_discovery"], live["topic_discovery"])
            self.assertEqual(result["recorded_story_premise"], doc["story_premise"])
            self.assertEqual(source.read_bytes(), before)

    def test_contract_refresh_keeps_explicit_custom_shape_guidance(self):
        existing = {"question_scope": "User-approved custom scope", "opening_task": "Specific approved opening"}
        result = execution_contract(existing, "battlefield-bearings")
        for key, value in existing.items():
            self.assertEqual(result[key], value)
        self.assertIn("topic_selection_reference", result)
        self.assertEqual(existing, {"question_scope": "User-approved custom scope", "opening_task": "Specific approved opening"})


if __name__ == "__main__":
    unittest.main()
