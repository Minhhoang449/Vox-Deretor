import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import muse_pack
import channels
from plan_runtime import plan_visuals
import plan_runtime


def project_doc(reference_image="characters/scout/reference.png"):
    character = {
        "id": "scout",
        "display_name": "Scout",
        "status": "hypothetical illustrative character",
        "description": "Chibi scout with a simple period-appropriate uniform and map pouch.",
        "reference_image": reference_image,
    }
    shot = {
        "id": "1",
        "scene": "A scout studies a route beside a mountain pass.",
        "characters": ["scout"],
        "dur": 6,
        "animation": {
            "start": "The scout holds a folded map beside the trail.",
            "action": "The scout checks the pass, then traces a route on the map.",
            "end": "The scout points toward the chosen path.",
            "camera": "A slow pan from the pass to the route, then hold.",
            "continuity": "Keep the same scout, map pouch, and left-to-right geography.",
        },
    }
    return {
        "project": "muse-test",
        "channel_id": "vi-sao-noi-nay",
        "pipeline": "local",
        "visual_mode": "clips",
        "aspect": "16:9",
        "animation_style": "chibi-2d",
        "format": {"scene_seconds_min": 3, "scene_seconds_max": 10},
        "visual_bible": {
            "style": "original hand-drawn Chibi 2D",
            "world": "researched historical setting",
            "characters": [character],
        },
        "beats": [{"id": "a", "title_en": "A route choice", "narration": "The scout chooses a route.", "shots": [shot]}],
    }


class MusePackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="muse-pack-test-")
        self.project_dir = self.temp.name
        self.beats_path = os.path.join(self.project_dir, "beats.json")
        self.write_doc(project_doc())

    def tearDown(self):
        self.temp.cleanup()

    def write_doc(self, doc):
        with open(self.beats_path, "w", encoding="utf-8") as handle:
            json.dump(doc, handle, ensure_ascii=False, indent=2)

    def read_doc(self):
        with open(self.beats_path, encoding="utf-8") as handle:
            return json.load(handle)

    def test_character_stage_exports_prompt_only_and_sets_reference_path(self):
        doc = project_doc(reference_image="")
        self.write_doc(doc)

        with contextlib.redirect_stdout(io.StringIO()):
            muse_pack.export(self.project_dir, characters_only=True)

        result = self.read_doc()
        char = result["visual_bible"]["characters"][0]
        self.assertEqual(char["reference_image"], "characters/scout/reference.png")
        prompt_path = os.path.join(self.project_dir, "muse", "characters", "scout", "design_prompt.txt")
        self.assertTrue(os.path.isfile(prompt_path))
        self.assertFalse(os.path.exists(os.path.join(self.project_dir, "keyframes")))
        with open(prompt_path, encoding="utf-8") as handle:
            prompt = handle.read()
        self.assertIn("reference sheet", prompt.lower())
        self.assertIn("front, three-quarter, profile, and back views", prompt)
        self.assertFalse(os.path.exists(os.path.join(self.project_dir, "muse", "001", "prompt.txt")))

    def test_shot_export_requires_approved_character_reference(self):
        with self.assertRaisesRegex(SystemExit, "Muse character reference.*missing"):
            muse_pack.export(self.project_dir)

    def test_motion_prompt_preserves_exact_legacy_calendar_wording(self):
        doc = project_doc()
        beat = doc["beats"][0]
        shot = beat["shots"][0]
        shot["prompt_text_exception"] = "A calendar page reads exactly JAN 28, 1968."

        prompt = muse_pack.compose_animation_motion_prompt(doc, beat, shot)

        self.assertIn('Render this exact wording: "A calendar page reads exactly JAN 28, 1968."', prompt)
        self.assertIn("Do not add other wording", prompt)
        self.assertNotIn("Keep all readable text, letters, numbers", prompt)

    def test_shot_export_uses_character_reference_and_needs_no_scene_image(self):
        reference = os.path.join(self.project_dir, "characters", "scout", "reference.png")
        os.makedirs(os.path.dirname(reference), exist_ok=True)
        with open(reference, "wb") as handle:
            handle.write(b"approved reference placeholder")

        with contextlib.redirect_stdout(io.StringIO()):
            muse_pack.export(self.project_dir)

        shot_dir = os.path.join(self.project_dir, "muse", "001")
        prompt_path = os.path.join(shot_dir, "prompt.txt")
        with open(prompt_path, encoding="utf-8") as handle:
            prompt = handle.read()
        with open(os.path.join(shot_dir, "meta.json"), encoding="utf-8") as handle:
            meta = json.load(handle)
        self.assertIn("Chibi", prompt)
        self.assertIn("there is no supplied scene frame", prompt)
        self.assertIn("CHARACTER REFERENCES", prompt)
        self.assertEqual(meta["generation_mode"], "text_to_video_with_character_references")
        self.assertTrue(meta["character_references"][0]["reference_image_available"])
        self.assertEqual(meta["save_clip_as"], "clips/clip_001.mp4")
        self.assertFalse(os.path.exists(os.path.join(self.project_dir, "keyframes")))
        self.assertFalse(any(name.lower().endswith((".png", ".jpg", ".webp")) for name in os.listdir(shot_dir)))

    def test_register_records_muse_clip(self):
        clip_dir = os.path.join(self.project_dir, "clips")
        os.makedirs(clip_dir)
        clip_path = os.path.join(clip_dir, "clip_001.mp4")
        with open(clip_path, "wb") as handle:
            handle.write(b"test clip placeholder")

        with contextlib.redirect_stdout(io.StringIO()):
            muse_pack.register(self.project_dir)

        registered = self.read_doc()["beats"][0]["shots"][0]["clip_path"]
        self.assertEqual(os.path.abspath(registered), os.path.abspath(clip_path))

    def test_runtime_planner_leaves_shot_count_to_approved_narration(self):
        visual = plan_visuals({
            "scene_seconds_min": 3,
            "scene_seconds_max": 10,
            "scene_seconds_typical": 5,
        })
        self.assertEqual(visual["shot_seconds_min"], 3)
        self.assertEqual(visual["shot_seconds_max"], 10)
        self.assertNotIn("shots_to_generate", visual)
        self.assertNotIn("stills_to_render", visual)

    def test_new_channel_project_defaults_to_local_stills(self):
        destination = os.path.join(self.project_dir, "episodes")
        channel = copy.deepcopy(channels.resolve("vi-sao-noi-nay"))
        channel["destination"] = destination
        with patch.object(channels, "resolve", return_value=channel):
            with contextlib.redirect_stdout(io.StringIO()):
                channels.bind("vi-sao-noi-nay", "test-war")
        episode_dir = os.path.join(destination, "test-war")
        with contextlib.redirect_stdout(io.StringIO()):
            plan_runtime.run(episode_dir, 20)
        with open(os.path.join(episode_dir, "beats.json"), encoding="utf-8") as handle:
            doc = json.load(handle)
        self.assertEqual(doc["pipeline"], "local")
        self.assertEqual(doc["visual_mode"], "revideo_stills")
        self.assertEqual(doc["channel_id"], "vi-sao-noi-nay")
        self.assertNotIn("shots_to_generate", doc["visual_plan"])
        self.assertEqual(doc["story_premise"]["format"], channel['story_format'])


if __name__ == "__main__":
    unittest.main()
