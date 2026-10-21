"""Regression checks for the live portfolio and preservation of newer contracts."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import channels
from editorial_policy import EXECUTION_CHECKS, execution_contract
from thumbnail_visual_direction import resolve_thumbnail_profile


class ActiveAuthoringPolicyTests(unittest.TestCase):
    def test_missing_contract_gets_the_current_channel_check(self):
        for channel in channels.load_channels():
            cid = channel["id"]
            self.assertEqual(execution_contract({}, cid)["execution_check"],
                             channel["writing_contract"]["execution_check"])
        self.assertEqual(len(set(EXECUTION_CHECKS.values())), 6)

    def test_refresh_preserves_a_newer_custom_contract(self):
        existing = {"revision": "channel-custom-next", "policy_updated_on": "2026-10-21",
                    "execution_check": "New channel-specific guidance",
                    "progression_test": "Supported custom path"}
        refreshed = execution_contract(existing, "chikyu-shikumi")
        for key, value in existing.items():
            self.assertEqual(refreshed[key], value)
        self.assertIsNot(refreshed, existing)

    def test_thumbnail_defaults_and_recorded_realistic_media_remain_separate(self):
        for channel in channels.load_channels():
            cid = channel["id"]
            self.assertEqual(resolve_thumbnail_profile(cid)["revision"],
                             "human-history-thumbnail-v2")
            saved = resolve_thumbnail_profile(cid, {"animation_style": "documentary-realistic"})
            self.assertEqual(saved["revision"], "documentary-thumbnail-v2-realistic")

    def test_retired_launch_source_is_outside_active_configuration(self):
        self.assertFalse((ROOT / "config/channel-launch-2026-10-15.json").exists())
        self.assertFalse((ROOT / "scripts/relaunch_setup.py").exists())
        self.assertTrue((ROOT / "config/channels.json").is_file())


if __name__ == "__main__":
    unittest.main()
