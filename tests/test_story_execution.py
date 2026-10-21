"""Voice-budget behavior for the editorial execution update."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from cache_keys import stable_hash
from plan_runtime import estimate_narration_budget


class NarrationBudgetTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = {"omnivoice": {"default_speed": 0.9, "pause_after_period_seconds": 0.8, "num_step": 32}}
        self.channel = {
            "voice": "sample-voice", "voice_engine": "omnivoice", "language": "en",
            "narration_calibration": {
                "voice_id": "sample-voice", "engine": "omnivoice", "language": "en",
                "units_per_minute": 130, "count_method": "whitespace_units",
                "tts_speed": 0.9, "pause_after_period_seconds": 0.8, "num_step": 32,
                "engine_config_sha256": stable_hash(self.pipeline["omnivoice"]),
            },
        }

    def budget(self, episode=None, channel=None, pipeline=None):
        return estimate_narration_budget(1200, channel or self.channel, episode,
                                         pipeline or self.pipeline)

    def test_matching_voice_estimates_twenty_minutes_of_speech(self):
        result = self.budget({"voice": {"voice_id": "sample-voice"}})
        self.assertEqual(result["target_units"], 2600)
        self.assertEqual(result["count_method"], "whitespace_units")

    def test_japanese_budget_counts_characters_rather_than_words(self):
        channel = copy.deepcopy(self.channel)
        channel["language"] = "ja"
        channel["narration_calibration"].update(language="ja", units_per_minute=328,
                                                count_method="non_whitespace_characters")
        result = self.budget(channel=channel)
        self.assertEqual(result["target_units"], 6560)
        self.assertEqual(result["method"], "character_estimate")

    def test_episode_overrides_invalidate_the_sample(self):
        for override in ({"tts_speed": 1.0}, {"tts_pause_after_period_seconds": 0.4},
                         {"tts_num_step": 16}, {"voice": {"voice_id": "another-voice"}},
                         {"voice_engine": "another-engine"}):
            with self.subTest(override=override):
                self.assertIsNone(self.budget(override))

    def test_model_or_voice_profile_change_invalidates_the_sample(self):
        pipeline = copy.deepcopy(self.pipeline)
        pipeline["omnivoice"]["model"] = "new-model"
        self.assertIsNone(self.budget(pipeline=pipeline))
        channel = copy.deepcopy(self.channel)
        channel["voice"] = "new-enrollment"
        self.assertIsNone(self.budget(channel=channel))

    def test_changed_clone_file_under_the_same_id_invalidates_the_sample(self):
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "voice.pt"
            path.write_bytes(b"old-voice")
            channel = copy.deepcopy(self.channel)
            channel["voice_reference"] = {"prompt": str(path)}
            channel["narration_calibration"]["voice_source_sha256"] = {
                "prompt": hashlib.sha256(path.read_bytes()).hexdigest()}
            self.assertIsNotNone(self.budget(channel=channel))
            path.write_bytes(b"new-voice")
            self.assertIsNone(self.budget(channel=channel))

    def test_invalid_or_stretched_samples_do_not_generate_budgets(self):
        for value in (0, -1, "unknown", float("nan"), float("inf")):
            channel = copy.deepcopy(self.channel)
            channel["narration_calibration"]["units_per_minute"] = value
            self.assertIsNone(self.budget(channel=channel))
        channel = copy.deepcopy(self.channel)
        channel["narration_calibration"]["post_tts_tempo"] = 1.2
        self.assertIsNone(self.budget(channel=channel))

    def test_live_profiles_expose_matching_voice_budgets(self):
        data = json.loads((ROOT / "config/channels.json").read_text(encoding="utf-8-sig"))
        pipeline = json.loads((ROOT / "config/pipeline.json").read_text(encoding="utf-8-sig"))
        for channel in data["channels"]:
            with self.subTest(channel=channel["id"]):
                cal = channel["narration_calibration"]
                result = estimate_narration_budget(1200, channel, {}, pipeline)
                self.assertIsNotNone(result)
                self.assertAlmostEqual(cal["units_per_minute"], cal["sample_units"] / cal["sample_speech_seconds"] * 60)
                self.assertEqual(cal["voice_id"], channel["voice"])
                self.assertGreater(result["target_units"], 0)


if __name__ == "__main__":
    unittest.main()
