import contextlib
import io
import json
import os
import shutil
import sys
import unittest
import uuid
from unittest.mock import patch

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, SCRIPTS)

import channels
import export_youtube
import thumbnail_visual_direction


@contextlib.contextmanager
def test_workspace():
    root = os.path.abspath(os.path.join(SCRIPTS, "..", "tmp", "thumbnail-visual-tests"))
    folder = os.path.join(root, uuid.uuid4().hex)
    os.makedirs(folder)
    try:
        yield folder
    finally:
        if os.path.commonpath([root, os.path.abspath(folder)]) != root:
            raise ValueError("Test cleanup path escaped its workspace.")
        shutil.rmtree(folder)


def packaging_doc(channel_id, phrase):
    return {
        "channel_id": channel_id,
        "animation_style": "documentary-realistic",
        "topic": "Could we save the Titanic?",
        "aspect": "9:16",
        "language": "stale",
        "channel": {"thumbnail_brand": {"primary_color": "#BADBAD"}},
        "youtube_metadata": {
            "packaging_research": [{"observation": "An episode-specific question."}],
            "description": "The researched historical question and sources.",
            "search_phrases": ["Titanic rescue mission"],
            "candidates": [{
                "id": "map-led",
                "title": "Could we save the Titanic?",
                "thumbnail_concept": "A map and the iceberg reveal the collision geometry.",
                "thumbnail_prompt": "An illustrated map shows the Titanic and iceberg without characters.",
                "thumbnail_file": "thumbnails/map-led.png",
                "thumbnail_text": phrase,
            }],
        },
    }


class ThumbnailVisualDirectionTests(unittest.TestCase):
    def test_text_free_candidate_exports_without_typography_and_requires_reason(self):
        with test_workspace() as folder:
            os.makedirs(os.path.join(folder, 'research'))
            with open(os.path.join(folder, 'research', 'packaging-test.md'), 'w', encoding='utf-8') as handle:
                handle.write('Discovery snapshot')
            doc = packaging_doc('terra-rewired', '')
            doc['topic'] = 'An ancient material process'
            doc['animation_style'] = 'chibi-2d'
            candidate = doc['youtube_metadata']['candidates'][0]
            candidate['title'] = 'An ancient material process'
            path = os.path.join(folder, 'beats.json')
            def save():
                with open(path, 'w', encoding='utf-8') as handle:
                    json.dump(doc, handle)
            save()
            with self.assertRaisesRegex(SystemExit, 'thumbnail_text_reason'):
                export_youtube.run(folder)
            candidate['thumbnail_text_reason'] = 'The cutaway makes the relationship clear.'
            os.makedirs(os.path.join(folder, 'thumbnails'))
            # Export checks existence, not image quality.
            with open(os.path.join(folder, candidate['thumbnail_file']), 'wb') as handle:
                handle.write(b'test-only-placeholder')
            doc['youtube_metadata']['selected_candidate_id'] = candidate['id']
            save()
            with contextlib.redirect_stdout(io.StringIO()):
                export_youtube.run(folder)
            with open(os.path.join(folder, 'thumbnail-prompts.md'), encoding='utf-8') as handle:
                prompt = handle.read()
            self.assertIn('Do not render any text, letters, numbers, labels', prompt)
            self.assertNotIn('Render only this exact en phrase:', prompt)
            self.assertNotIn('large, high-contrast, cleanly spelled thumbnail typography', prompt)
            with open(os.path.join(folder, 'youtube-upload.txt'), encoding='utf-8') as handle:
                self.assertIn('No lettering. Editorial reason:', handle.read())
            del candidate['thumbnail_text']
            save()
            with self.assertRaisesRegex(SystemExit, 'explicit empty string'):
                export_youtube.run(folder)

    def test_all_six_export_live_editorial_angle_and_exact_phrase_without_brand_template(self):
        phrases = {
            "en": "Could it be saved?",
            "es": "¿Se podía salvar?",
            "vi": "CỨU ĐƯỢC KHÔNG?",
            "ja": "救えたのか？",
            "ko": "구할 수 있었을까?",
        }
        for channel in channels.load_channels():
            with self.subTest(channel=channel["id"]), test_workspace() as folder:
                # This fixture is an explicitly recorded realistic episode;
                # new channel defaults must not migrate its saved style.
                profile = thumbnail_visual_direction.resolve_thumbnail_profile(
                    channel["id"], packaging_doc(channel["id"], phrases[channel["language"]]))
                os.makedirs(os.path.join(folder, "research"))
                with open(os.path.join(folder, "research", "packaging-test.md"), "w", encoding="utf-8") as handle:
                    handle.write("Test discovery snapshot")
                phrase = phrases[channel["language"]]
                with open(os.path.join(folder, "beats.json"), "w", encoding="utf-8") as handle:
                    json.dump(packaging_doc(channel["id"], phrase), handle, ensure_ascii=False)

                with contextlib.redirect_stdout(io.StringIO()):
                    export_youtube.run(folder)

                with open(os.path.join(folder, "thumbnail-prompts.md"), encoding="utf-8") as handle:
                    prompt = handle.read()
                self.assertIn(profile["revision"], prompt)
                self.assertIn("photorealistic documentary reconstruction", prompt)
                self.assertIn("A person is optional", prompt)
                self.assertIn("no per-channel visual template is required", prompt)
                self.assertIn("An illustrated map shows the Titanic and iceberg without characters.", prompt)
                self.assertNotIn(f"Channel: {channel['id']}", prompt)
                self.assertNotIn("text_left_subject_right", prompt)
                self.assertNotIn("#176A56", prompt)
                self.assertNotIn("#BADBAD", prompt)
                self.assertIn(f"Render only this exact {channel['language']} phrase: {phrase}", prompt)
                self.assertIn("1280x720", prompt)
                self.assertIn("Target ratio: 16:9", prompt)
                rules = channel['packaging_direction']
                self.assertIn(rules['thumbnail_direction'], prompt)
                self.assertIn(rules['opening_contract'], prompt)
                with open(os.path.join(folder, 'packaging-direction.md'), encoding='utf-8') as handle:
                    title_guide = handle.read()
                for pattern in rules['title_patterns']:
                    self.assertIn(pattern, title_guide)
                self.assertFalse(os.path.exists(os.path.join(folder, "youtube-upload.txt")))

    def test_bind_and_show_do_not_seed_channel_thumbnail_branding(self):
        with test_workspace() as folder:
            channel = dict(channels.resolve("vi-sao-noi-nay"), destination=folder)
            with patch.object(channels, "resolve", return_value=channel):
                with contextlib.redirect_stdout(io.StringIO()):
                    channels.bind("vi-sao-noi-nay", "test-thumbnail-dna")
            with open(os.path.join(folder, "test-thumbnail-dna", "beats.json"), encoding="utf-8") as handle:
                doc = json.load(handle)
            self.assertNotIn("thumbnail_brand", doc)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                channels.show("vi-sao-noi-nay")
            profile = json.loads(output.getvalue())
            self.assertNotIn("thumbnail_brand", profile)
            self.assertEqual(profile['packaging_direction']['revision'], 'human-history-portfolio-v2-2026-10-20')


if __name__ == "__main__":
    unittest.main()
