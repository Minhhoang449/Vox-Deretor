"""Production-routing regressions for the authorized footage-first workflow."""
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
import codex_prompts
from animation_prompts import compose_animation_frame_prompt
from image_reuse import image_sources
from image_reuse_qa import build_report
from thumbnail_visual_direction import resolve_thumbnail_profile
from visual_policy import REALISTIC_STYLE, VISUAL_DNA, VISUAL_WORKFLOW, episode_style
from visual_sources import validate_source_plan


def source(decision):
    return {"decision": decision, "reason": "Test fixture; no real source claim",
            "searches": [{"provider": "test", "query": "spillway flow", "query_language": "en",
                          "accessed_on": "2026-10-18", "outcome": "Synthetic test record"}],
            "source_url": "https://example.org/test-record", "accessed_on": "2026-10-18",
            "label": "Illustrative footage" if decision == "video" else "AI reconstruction",
            "rights_url": "https://example.org/test-rights", "rights_note": "Synthetic test rights",
            "rights_status": "verified", "factual_role": "illustrative", "verification_note": "Synthetic fixture"}


def episode(folder):
    (folder / "clip.mp4").write_bytes(b"fixture only; structural checks do not inspect media")
    return {"project": "footage-test", "episode_slug": "footage-test", "channel_id": "last-safe-minute",
            "language": "en", "animation_style": REALISTIC_STYLE, "visual_dna": copy.deepcopy(VISUAL_DNA),
            "visual_workflow": copy.deepcopy(VISUAL_WORKFLOW), "visual_mode": "hybrid", "pipeline": "local",
            "image_text_policy": "none", "visual_plan": {"test": True},
            "format": {"target_seconds": 6, "scene_seconds_min": 3, "scene_seconds_max": 10},
            "beats": [{"id": "B1", "narration": "Approved test speech remains unchanged.", "shots": [
                {"id": "A", "dur": 3, "scene": "A flowing river", "clip_path": "clip.mp4", "visual_source": source("video")},
                {"id": "B", "dur": 3, "scene": "A researched spillway section", "visual_source": source("ai_reconstruction")}
            ]}]}


class FootageFirstTests(unittest.TestCase):
    def test_all_six_new_bindings_get_realism_and_hybrid(self):
        for profile in channels.load_channels():
            with self.subTest(channel=profile["id"]), tempfile.TemporaryDirectory() as folder:
                selected = dict(channels.resolve(profile["id"]), destination=folder)
                with patch.object(channels, "resolve", return_value=selected), contextlib.redirect_stdout(io.StringIO()):
                    channels.bind(profile["id"], "test-new-style", topic="A fresh documented question")
                doc = json.loads((Path(folder) / "test-new-style" / "beats.json").read_text(encoding="utf-8"))
                self.assertEqual(doc["animation_style"], REALISTIC_STYLE)
                self.assertEqual(doc["visual_mode"], "hybrid")
                self.assertEqual(doc["visual_workflow"]["source_order"], "footage_first")
                self.assertEqual(doc["language"], profile["language"])

    def test_rebinding_does_not_migrate_legacy_visuals(self):
        with tempfile.TemporaryDirectory() as folder:
            selected = dict(channels.resolve("last-safe-minute"), destination=folder)
            target = Path(folder) / "legacy"
            target.mkdir()
            old = {"project": "legacy", "topic": "A recorded event", "channel_id": "last-safe-minute",
                   "animation_style": "chibi-2d", "visual_mode": "revideo_stills", "beats": [],
                   "visual_dna": {"revision": "documentary-visual-v1", "default_style": "chibi-2d"}}
            (target / "beats.json").write_text(json.dumps(old), encoding="utf-8")
            with patch.object(channels, "resolve", return_value=selected), contextlib.redirect_stdout(io.StringIO()):
                channels.bind("last-safe-minute", "legacy", topic="A recorded event")
            result = json.loads((target / "beats.json").read_text(encoding="utf-8"))
            for key in ("animation_style", "visual_mode", "visual_dna"):
                self.assertEqual(result[key], old[key])
            self.assertNotIn("visual_workflow", result)
            self.assertEqual(episode_style({}), "chibi-2d")

    def test_pending_search_blocks_image_export(self):
        with tempfile.TemporaryDirectory() as folder:
            doc = episode(Path(folder))
            doc["beats"][0]["shots"][0]["visual_source"] = {"decision": "pending"}
            (Path(folder) / "beats.json").write_text(json.dumps(doc), encoding="utf-8")
            with patch.object(codex_prompts, "require_research"), self.assertRaisesRegex(SystemExit, "finish footage sourcing"):
                codex_prompts.write_prompts(folder)
            self.assertFalse((Path(folder) / "imagegen").exists())

    def test_download_and_item_rights_are_required(self):
        with tempfile.TemporaryDirectory() as folder:
            doc = episode(Path(folder))
            record = doc["beats"][0]["shots"][0]["visual_source"]
            record["rights_status"] = "unknown"
            with self.assertRaisesRegex(SystemExit, "usage rights"):
                validate_source_plan(folder, doc)
            record["rights_status"] = "verified"
            (Path(folder) / "clip.mp4").unlink()
            with self.assertRaisesRegex(SystemExit, "download and inspect"):
                validate_source_plan(folder, doc)

    def test_cross_language_scan_cannot_replace_primary_scan(self):
        with tempfile.TemporaryDirectory() as folder:
            doc = episode(Path(folder))
            doc["language"] = "ja"
            for shot in doc["beats"][0]["shots"]:
                shot["visual_source"]["searches"][0]["cross_language_note"] = "Supplemental archive terminology"
            with self.assertRaisesRegex(SystemExit, "primary audience-language"):
                validate_source_plan(folder, doc)

    def test_invalid_source_range_is_rejected_before_image_export(self):
        with tempfile.TemporaryDirectory() as folder:
            doc = episode(Path(folder))
            for offset in (-1, float("nan"), "not-a-number"):
                doc["beats"][0]["shots"][0]["source_in_seconds"] = offset
                with self.subTest(offset=offset), self.assertRaisesRegex(SystemExit, "finite nonnegative"):
                    validate_source_plan(folder, doc)

    def test_realistic_and_diagram_prompts_preserve_distinct_purposes(self):
        with tempfile.TemporaryDirectory() as folder:
            doc = episode(Path(folder))
            beat = doc["beats"][0]
            still = beat["shots"][1]
            prompt = compose_animation_frame_prompt(doc, beat, still)
            self.assertIn("photorealistic documentary reconstruction", prompt)
            self.assertNotIn("CHIBI DESIGN:", prompt)
            self.assertNotIn("no photorealism", prompt)
            still["visual_source"] = source("diagram")
            prompt = compose_animation_frame_prompt(doc, beat, still)
            self.assertIn("clear documentary explanatory graphics", prompt)
            self.assertNotIn("Use natural anatomy and credible optics", prompt)

    def test_manifest_requests_only_missing_stills_and_keeps_hybrid(self):
        with tempfile.TemporaryDirectory() as folder:
            doc = episode(Path(folder))
            speech = doc["beats"][0]["narration"]
            (Path(folder) / "beats.json").write_text(json.dumps(doc), encoding="utf-8")
            with patch.object(codex_prompts, "require_research"), contextlib.redirect_stdout(io.StringIO()):
                codex_prompts.write_prompts(folder)
            manifest = json.loads((Path(folder) / "imagegen" / "manifest.json").read_text(encoding="utf-8"))
            saved = json.loads((Path(folder) / "beats.json").read_text(encoding="utf-8"))
            self.assertEqual([a["key"] for a in manifest["assets"]], ["B1B"])
            self.assertEqual([a["key"] for a in manifest["footage_shots"]], ["B1A"])
            self.assertEqual(saved["visual_mode"], "hybrid")
            self.assertEqual(saved["beats"][0]["narration"], speech)
            self.assertEqual(image_sources(doc), {"B1B": "B1B"})

    def test_thumbnail_uses_episode_style_and_preserves_legacy(self):
        new = resolve_thumbnail_profile("last-safe-minute", {"animation_style": REALISTIC_STYLE})
        old = resolve_thumbnail_profile("last-safe-minute", {"animation_style": "chibi-2d"})
        # Studio rule 2026-10-21: every thumbnail is Chibi 2D, even for legacy realistic episodes.
        self.assertIn("Chibi", new["style"])
        self.assertIn("Chibi", old["style"])
        self.assertEqual(new["revision"], old["revision"])

    def test_hybrid_reuse_counts_video_slots_and_real_sequence_distance(self):
        with tempfile.TemporaryDirectory() as folder:
            still = Path(folder) / "synthetic-image"
            still.write_bytes(b"Synthetic fingerprint fixture")
            segments = [{"image": str(still), "dur": 1, "shot_key": "first"}]
            segments += [{"clip": "synthetic-video", "dur": 1} for _ in range(8)]
            segments += [{"image": str(still), "dur": 1, "shot_key": "last", "reuse_image_from": "first"}]
            report = build_report(segments)
            self.assertEqual(report["scene_shots"], 10)
            self.assertEqual(report["image_shots"], 2)
            self.assertEqual(report["reused_shots"], 1)
            self.assertEqual(report["max_reused_shots"], 3)
            self.assertEqual(report["nearby_returns"], [])


if __name__ == "__main__":
    unittest.main()
