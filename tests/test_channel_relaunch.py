"""Regression checks for the authorized active/legacy channel split."""
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
sys.path.insert(0, str(ROOT / 'scripts'))
import channels
import playlists


class ChannelRelaunchTests(unittest.TestCase):
    def test_active_roster_and_dna_are_replaced(self):
        roster = channels.load_channels()
        self.assertEqual(len(roster), 6)
        self.assertEqual(sorted(p['language'] for p in roster), ['en']*4 + ['ja', 'vi'])
        self.assertEqual(channels.load_channel_config()['narration_dna']['revision'], 'research-led-documentary-v1')
        self.assertTrue(all(p['destination'].startswith('D:/Video/') for p in roster))

    def test_active_catalog_has_thirty_unpublished_playlists(self):
        catalog = playlists.load_catalog()
        self.assertEqual({p['channel_id'] for p in catalog['channels']}, {p['id'] for p in channels.load_channels()})
        self.assertEqual(sum(len(p['playlists']) for p in catalog['channels']), 30)
        self.assertTrue(all(not p['youtube_playlist_id'] for c in catalog['channels'] for p in c['playlists']))

    def test_new_seed_uses_each_channels_actual_format(self):
        for profile in channels.load_channels():
            premise = channels._new_story_premise(profile)
            self.assertEqual(premise['format'], profile['story_format'])
            self.assertIn('central_question', premise)
            self.assertNotIn('mission_introduction', premise)
            self.assertNotIn('success_criteria', premise)

    def test_bind_keeps_selected_question_and_voice_route(self):
        profile = copy.deepcopy(channels.resolve('vi-sao-noi-nay'))
        with tempfile.TemporaryDirectory() as folder:
            profile['destination'] = folder
            with patch.object(channels, 'resolve', return_value=profile), contextlib.redirect_stdout(io.StringIO()):
                channels.bind(profile['id'], 'roof-water', topic='How does household rainwater storage work?')
                context = channels.authoring_context(profile['id'], 'roof-water')
            doc = json.loads((Path(folder)/'roof-water'/'beats.json').read_text(encoding='utf-8'))
            self.assertEqual(doc['channel_id'], profile['id'])
            self.assertEqual(doc['voice']['voice_id'], profile['voice'])
            self.assertEqual(context['topic'], 'How does household rainwater storage work?')
            self.assertEqual(context['story_premise']['format'], profile['story_format'])

    def test_conflicting_new_question_does_not_rebind(self):
        profile = copy.deepcopy(channels.resolve('terra-rewired'))
        with tempfile.TemporaryDirectory() as folder:
            profile['destination'] = folder
            with patch.object(channels, 'resolve', return_value=profile), contextlib.redirect_stdout(io.StringIO()):
                channels.bind(profile['id'], 'one-place', topic='The selected place question')
                before = (Path(folder)/'one-place'/'beats.json').read_bytes()
                with self.assertRaises(SystemExit):
                    channels.bind(profile['id'], 'one-place', topic='An unrelated question')
                self.assertEqual(before, (Path(folder)/'one-place'/'beats.json').read_bytes())

    def test_retired_ids_and_playlist_keys_still_resolve(self):
        old = channels.resolve('moc-vy')
        self.assertEqual(old['profile_status'], 'archived')
        self.assertTrue(old['destination'].startswith('D:/Vox-Video/'))
        legacy = playlists.channel_playlists('moc-vy')
        self.assertEqual(len(legacy), 5)
        self.assertTrue(all(p['id'].startswith('moc-vy-') for p in legacy))

    def test_retired_profile_cannot_start_a_new_episode(self):
        profile = copy.deepcopy(channels.resolve('moc-vy'))
        with tempfile.TemporaryDirectory() as folder:
            profile['destination'] = folder
            with patch.object(channels, 'resolve', return_value=profile), self.assertRaises(SystemExit):
                channels.bind(profile['id'], 'new-legacy-topic', topic='New topic')
            self.assertFalse((Path(folder)/'new-legacy-topic').exists())

    def test_legacy_episode_playlist_assignment_keeps_original_catalog(self):
        old_playlist = playlists.channel_playlists('moc-vy')[0]
        bundle = playlists.episode_playlists({'channel_id':'moc-vy', 'youtube_metadata':{
            'playlists':{'primary_id':old_playlist['id'], 'additional_ids':[], 'selection_reason':'Legacy recorded assignment'}}})
        self.assertEqual(bundle['status'], 'selected')
        self.assertEqual(bundle['catalog_revision'], 'mission-playlists-v3')
        self.assertEqual(bundle['primary_id'], old_playlist['id'])

    def test_new_episode_refuses_another_channels_playlist(self):
        wrong = playlists.channel_playlists('terra-rewired')[0]['id']
        with self.assertRaises(ValueError):
            playlists.episode_playlists({'channel_id':'last-safe-minute', 'youtube_metadata':{
                'playlists':{'primary_id':wrong, 'additional_ids':[], 'selection_reason':'Wrong channel'}}})

    def test_music_and_episode_roots(self):
        pipeline = json.loads((ROOT/'config/pipeline.json').read_text(encoding='utf-8'))
        self.assertEqual(pipeline['music_library']['path'], 'D:/Music')
        self.assertEqual(pipeline['episode_root'], 'D:/Video')

    def test_copy_fields_fit_conservative_editorial_budgets(self):
        for channel in channels.load_channels():
            profile = channel['youtube_setup']
            self.assertLessEqual(len(profile['description']), 1000)
            self.assertLessEqual(len(', '.join(profile['channel_keywords'])), 450)

    def test_each_active_channel_has_distinct_editorial_packaging(self):
        rules = [p['packaging_direction'] for p in channels.load_channels()]
        self.assertEqual(len({p['thumbnail_direction'] for p in rules}), 6)
        for rule in rules:
            self.assertTrue(rule['revision'])
            self.assertEqual(rule['metadata_direction']['public_sources_section'], 'omit_by_default')
            self.assertEqual(len(rule['title_patterns']), 3)
            self.assertEqual(len(rule['thumbnail_approaches']), 3)
            self.assertTrue(rule['opening_contract'])


if __name__ == '__main__':
    unittest.main()
