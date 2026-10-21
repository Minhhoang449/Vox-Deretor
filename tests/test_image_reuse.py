"""Production-path checks for sharing original scene images without extra generation."""
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import sys
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from PIL import Image
import assemble
import codex_prompts
import ffmpeg_stills
from image_reuse import apply_image_reuse, image_sources


def episode():
    original = {
        "id": "A", "dur": 6, "scene": "A traveler buying rice in the market.",
        "characters": ["traveler"], "in_scene_text": "CHỢ GẠO",
        "text_placement": "the shop sign", "animation": {"camera": "locked-off"},
    }
    related = {
        "id": "B", "dur": 6, "scene": "Return to the same rice purchase.",
        "reuse_image_from": "B01A", "reuse_reason": "The same purchase explains the meal cost.",
        "animation": {"camera": "locked-off"},
    }
    second_original = copy.deepcopy(original)
    second_original["scene"] = "The traveler at home with the purchased rice."
    later_related = copy.deepcopy(related)
    later_related["reuse_image_from"] = "B01B"
    third_original = copy.deepcopy(original)
    third_original["id"] = "C"
    third_original["scene"] = "A market map showing the route from the shop to the home."
    fourth_original = copy.deepcopy(original)
    fourth_original["id"] = "C"
    fourth_original["scene"] = "The rice fields that supplied the market."
    return {
        "channel_id": "moc-vy", "pipeline": "local", "visual_mode": "revideo_stills",
        "aspect": "16:9", "captions": False, "image_text_policy": "contextual",
        "visual_plan": {"shot_seconds_min": 3},
        "format": {"target_seconds": 36, "target_seconds_min": 0, "target_seconds_max": 999},
        "beats": [{"id": "B01", "shots": [original, related, third_original]},
                  {"id": "B02", "shots": [second_original, later_related, fourth_original]}],
    }


class ImageReuseTests(unittest.TestCase):
    def setUp(self):
        self.base = ROOT / "tmp" / "image-reuse-tests"
        self.base.mkdir(parents=True, exist_ok=True)
        self.folder = self.base / uuid.uuid4().hex
        self.folder.mkdir()
        self.addCleanup(self.cleanup)
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()
        self.addCleanup(self.quiet.__exit__, None, None, None)

    def cleanup(self):
        target = self.folder.resolve()
        if target.parent != self.base.resolve():
            raise RuntimeError("Test cleanup escaped its workspace directory.")
        shutil.rmtree(target)

    def write(self, doc):
        (self.folder / "beats.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    def read(self):
        return json.loads((self.folder / "beats.json").read_text(encoding="utf-8"))

    def export(self, doc=None):
        if doc is not None:
            self.write(doc)
        with patch.object(codex_prompts, "require_research"):
            return codex_prompts.write_prompts(str(self.folder))

    def create_originals(self):
        for key, color in [("B01A", "red"), ("B01C", "green"),
                           ("B02A", "blue"), ("B02C", "yellow")]:
            Image.new("RGB", (192, 108), color).save(self.folder / "keyframes" / f"kf_{key}.png")

    def test_export_register_and_assembly_share_four_full_images_in_six_shots(self):
        self.assertEqual(self.export(episode()), 4)
        manifest_path = self.folder / "imagegen" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["image_summary"], {"shots": 6, "unique_images": 4, "reused_shots": 2})
        self.assertEqual(len(list((self.folder / "imagegen").glob("kf_*.txt"))), 4)
        for job in manifest["shots"]:
            if job["action"] == "reuse":
                self.assertIsNone(job["prompt_file"])
                self.assertEqual(job["source_key"], "B01A")
        self.create_originals()
        codex_prompts.register(str(self.folder))
        registered = self.read()
        source = registered["beats"][0]["shots"][0]
        self.assertEqual(registered["beats"][0]["shots"][1]["keyframe_path"], source["keyframe_path"])
        self.assertEqual(registered["beats"][1]["shots"][1]["keyframe_prompt_hash"], source["keyframe_prompt_hash"])
        self.assertEqual(len(list((self.folder / "keyframes").glob("*.png"))), 4)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertTrue(all(job["status"] == "ready" for job in manifest["shots"] + manifest["assets"]))
        for beat in registered["beats"]:
            audio = self.folder / f"{beat['id']}.wav"
            audio.touch()
            beat["narration_audio"] = str(audio)
        # An obsolete per-shot path must not win over the current source image.
        registered["beats"][0]["shots"][1]["keyframe_path"] = str(self.folder / "obsolete.png")
        self.write(registered)
        class CapturedRender(Exception):
            pass
        with patch.object(assemble, "probe_dur", return_value=11.5), \
                patch.object(ffmpeg_stills, "render_cache_fingerprint", return_value="test"), \
                patch.object(ffmpeg_stills, "render", side_effect=CapturedRender) as renderer:
            with self.assertRaises(CapturedRender):
                assemble.run(str(self.folder), stills_renderer="ffmpeg")
        segments = renderer.call_args.args[1]
        self.assertEqual([seg["dur"] for seg in segments], [6, 6, 6, 6, 6, 6])
        self.assertEqual(segments[0]["image"], segments[1]["image"])
        self.assertEqual(segments[0]["image"], segments[4]["image"])
        self.assertNotEqual(segments[0]["image"], segments[2]["image"])
        self.assertTrue(all("crop" not in seg and "scale" not in seg for seg in segments))

    def test_export_rejects_reuse_above_35_percent(self):
        doc = episode()
        extra_reuse = copy.deepcopy(doc["beats"][1]["shots"][0])
        extra_reuse["id"] = "D"
        extra_reuse["reuse_image_from"] = "B02A"
        extra_reuse["reuse_reason"] = "The same purchase is referenced again."
        doc["beats"][1]["shots"].append(extra_reuse)
        with self.assertRaisesRegex(SystemExit, "35% limit allows at most 2"):
            self.export(doc)
        self.assertFalse((self.folder / "imagegen").exists())

    def test_export_rejects_original_image_reused_more_than_twice(self):
        doc = episode()
        extra_reuse = copy.deepcopy(doc["beats"][1]["shots"][0])
        extra_reuse["id"] = "D"
        extra_reuse["reuse_image_from"] = "B01A"
        extra_reuse["reuse_reason"] = "The original purchase appears once more."
        doc["beats"][1]["shots"].append(extra_reuse)
        for index in range(3):
            extra_original = copy.deepcopy(doc["beats"][1]["shots"][0])
            extra_original["id"] = chr(ord("E") + index)
            extra_original["scene"] = f"Additional researched location {index}."
            doc["beats"].append({"id": f"B{index + 3:02d}", "shots": [extra_original]})
        doc["format"]["target_seconds"] = 60
        # Three reuse shots among ten still fit the episode-wide 35% limit;
        # the original-source limit must independently reject this manifest.
        with self.assertRaisesRegex(SystemExit, "is reused 3 times; the maximum is 2"):
            self.export(doc)
        self.assertFalse((self.folder / "imagegen").exists())

    def test_existing_registered_source_requires_no_new_image(self):
        self.export(episode())
        self.create_originals()
        codex_prompts.register(str(self.folder))
        self.assertEqual(self.export(), 0)
        self.assertEqual(len(list((self.folder / "keyframes").glob("*.png"))), 4)

    def test_source_prompt_change_invalidates_reused_appearances(self):
        self.export(episode())
        self.create_originals()
        codex_prompts.register(str(self.folder))
        doc = self.read()
        doc["beats"][0]["shots"][0]["scene"] = "The purchase has a different visible state."
        self.assertEqual(self.export(doc), 1)
        manifest = json.loads((self.folder / "imagegen" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["assets"][0]["status"], "needs_image")
        for job in manifest["shots"]:
            if job["action"] == "reuse":
                self.assertEqual(job["source_status"], "needs_image")
                self.assertEqual(job["status"], "reuse")
        with self.assertRaisesRegex(SystemExit, "needs generation/review"):
            apply_image_reuse(self.read())

    def test_missing_source_does_not_use_old_alias_file(self):
        self.export(episode())
        self.create_originals()
        codex_prompts.register(str(self.folder))
        (self.folder / "keyframes" / "kf_B01A.png").unlink()
        Image.new("RGB", (192, 108), "green").save(self.folder / "keyframes" / "kf_B01B.png")
        with self.assertRaisesRegex(SystemExit, "1 stills still missing"):
            codex_prompts.register(str(self.folder))
        doc = self.read()
        self.assertNotIn("keyframe_path", doc["beats"][0]["shots"][1])
        with self.assertRaisesRegex(SystemExit, "not registered"):
            apply_image_reuse(doc)

    def test_invalid_references_stop_before_prompt_files_are_written(self):
        for target, expected in [("missing", "unknown"), ("", "unknown"), ("B01B", "cycle")]:
            doc = episode()
            doc["beats"][0]["shots"][1]["reuse_image_from"] = target
            with self.assertRaisesRegex(SystemExit, expected):
                self.export(doc)
            self.assertFalse((self.folder / "imagegen").exists())

    def test_reuse_checks_reason_characters_and_baked_text(self):
        cases = [("reuse_reason", "", "needs reuse_reason"),
                 ("characters", ["someone_else"], "different characters"),
                 ("in_scene_text", "GIÁ MỚI", "cannot change text"),
                 ("image_text_policy", "none", "cannot remove")]
        for field, value, message in cases:
            with self.subTest(field=field):
                doc = episode()
                doc["beats"][0]["shots"][1][field] = value
                with self.assertRaisesRegex(SystemExit, message):
                    image_sources(doc)

    def test_old_episodes_without_reuse_still_export_every_shot(self):
        doc = episode()
        for beat in doc["beats"]:
            for shot in beat["shots"]:
                shot.pop("reuse_image_from", None)
                shot.pop("reuse_reason", None)
                shot.setdefault("image_text_policy", "none")
        self.assertEqual(self.export(doc), 6)
        self.assertEqual(len(list((self.folder / "imagegen").glob("kf_*.txt"))), 6)

    def test_visual_cache_changes_when_a_shared_source_image_changes(self):
        self.export(episode())
        self.create_originals()
        first = str(self.folder / "keyframes" / "kf_B01A.png")
        other = str(self.folder / "keyframes" / "kf_B02A.png")
        segments = [{"image": image, "dur": 6, "camera": "locked-off"}
                    for image in [first, first, other, first]]
        before = ffmpeg_stills.jobs_for(segments, 192, 108, 30, ffmpeg_stills.settings())
        Image.new("RGB", (192, 108), "yellow").save(first)
        after = ffmpeg_stills.jobs_for(segments, 192, 108, 30, ffmpeg_stills.settings())
        # All shared appearances and the following incoming transition must refresh.
        self.assertTrue(all(a["fingerprint"] != b["fingerprint"] for a, b in zip(before, after)))


if __name__ == "__main__":
    unittest.main()
