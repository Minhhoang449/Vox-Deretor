"""Mission defaults, legacy preservation and scenario notes through real prompt builders."""
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
import animation_prompts
import channels
import muse_pack
from cache_keys import stable_hash
import plan_runtime

FIXTURE = json.loads((ROOT / "tests/fixtures/sahara-mission/scenario.json").read_text(encoding="utf-8"))


class MissionAuthoringTests(unittest.TestCase):
    def test_six_channels_seed_own_formats_with_optional_scenario_inputs(self):
        for profile in channels.load_channels():
            with self.subTest(channel=profile["id"]), tempfile.TemporaryDirectory() as folder:
                current = dict(profile, destination=folder)
                with patch.object(channels, "resolve", return_value=current), contextlib.redirect_stdout(io.StringIO()):
                    channels.bind(profile["id"], "new-mission", topic="Selected mission")
                    path = Path(folder) / "new-mission/beats.json"
                    doc = json.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(doc["story_premise"]["format"], profile['story_format'])
                    self.assertEqual(doc["narration_dna"], channels.load_channel_config()["narration_dna"])
                    self.assertEqual(doc["story_premise"]["central_question"], "")
                    self.assertEqual(doc["story_premise"]["optional_scenario"], {})
                    self.assertEqual(doc["story_premise"]["consequences"], [])
                    self.assertFalse({"daily_goal", "modern_expectation", "protagonist_status"} & doc["story_premise"].keys())
                    self.assertEqual(doc["beats"], [])
                    self.assertEqual(doc["voice"]["reference_audio"], profile["voice_reference"]["audio"])

    def test_sahara_premise_roundtrips_into_read_only_context_with_production_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            profile = dict(channels.resolve("moc-vy"), destination=folder)
            with patch.object(channels, "resolve", return_value=profile), contextlib.redirect_stdout(io.StringIO()):
                path = Path(folder) / "sahara/beats.json"
                path.parent.mkdir()
                doc = {'channel_id':'moc-vy', 'topic':FIXTURE['topic'], 'channel':profile,
                       'story_premise':copy.deepcopy(FIXTURE['story_premise']), 'beats':[]}
                doc['story_premise']['exception_reason']='Recorded approved legacy hypothetical episode'
                path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
                before = path.read_bytes()
                current = channels.authoring_context("moc-vy", "sahara")
                self.assertEqual(current["story_premise"]["outcome"], "failure")
                self.assertEqual(current["story_premise"]["consequences"], FIXTURE["story_premise"]["consequences"])
                self.assertEqual(path.read_bytes(), before)
                plan_runtime.run(str(path.parent), 20)
                planned = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(planned["format"]["target_seconds"], 1200)
                self.assertEqual(planned["format"]["target_seconds_min"], 840)
                self.assertEqual(planned["story_premise"], doc["story_premise"])
                with self.assertRaises(SystemExit):
                    plan_runtime.run(str(path.parent), 5)

    def test_illustrative_water_arithmetic_and_sensitivity(self):
        inputs, expected = FIXTURE["assumptions"], FIXTURE["expected_arithmetic"]
        net = inputs["area_km2"] * 1_000_000 * inputs["annual_net_water_depth_m"]
        self.assertEqual(net, expected["annual_net_water_m3"])
        self.assertEqual(inputs["annual_project_water_cap_m3"] - net, expected["headroom_before_losses_m3"])
        self.assertEqual(net * 2, expected["annual_net_water_if_depth_doubles_m3"])
        self.assertGreater(net * 2, inputs["annual_project_water_cap_m3"])

    def scene(self):
        return ({"aspect": "16:9", "visual_bible": {"scenario_layers": "Actual baseline and conditional aftermath stay distinct"}},
                {"scenario_context": {"layer": "baseline", "branch": "actual present"}},
                {"scene": "Installed pipes beside a discontinued pilot plot", "image_text_policy": "none",
                 "scenario_context": copy.deepcopy(FIXTURE["shot_context"]),
                 "animation": {"start": "One quiet installed pipe", "camera": "hold"}})

    def test_shot_branch_overrides_beat_notes_and_reaches_both_prompt_routes(self):
        doc, beat, shot = self.scene()
        for builder in (animation_prompts.compose_animation_frame_prompt, animation_prompts.compose_animation_motion_prompt):
            prompt = builder(doc, beat, shot)
            self.assertIn(FIXTURE["shot_context"]["branch"], prompt)
            self.assertIn(FIXTURE["shot_context"]["uncertainty"], prompt)
            self.assertNotIn("branch: actual present", prompt)
            alternate = copy.deepcopy(shot)
            alternate["scenario_context"]["branch"] = "B1: conditional sustained operation"
            self.assertNotEqual(stable_hash(prompt), stable_hash(builder(doc, beat, alternate)))

    def test_beat_context_is_used_when_shot_has_no_override(self):
        doc, beat, shot = self.scene()
        shot.pop("scenario_context")
        prompt = animation_prompts.compose_animation_frame_prompt(doc, beat, shot)
        self.assertIn("branch: actual present", prompt)
        self.assertNotIn(FIXTURE["shot_context"]["branch"], prompt)

    def test_legacy_shot_without_context_still_exports_and_bad_context_fails(self):
        doc, beat, shot = self.scene()
        beat.pop("scenario_context")
        shot.pop("scenario_context")
        self.assertTrue(animation_prompts.compose_animation_frame_prompt(doc, beat, shot))
        shot["scenario_context"] = 123
        with self.assertRaisesRegex(SystemExit, "scenario_context"):
            animation_prompts.compose_animation_frame_prompt(doc, beat, shot)

    def test_character_reference_is_topic_neutral_and_keeps_spec(self):
        character = {"id": "operator", "status": "fictional", "description": "Modern survey operator with a blue sun hat"}
        prompt = muse_pack.character_design_prompt({}, character)
        self.assertIn(character["description"], prompt)
        self.assertIn('"status": "fictional"', prompt)
        self.assertNotIn("war-history explainer", prompt)


if __name__ == "__main__":
    unittest.main()
