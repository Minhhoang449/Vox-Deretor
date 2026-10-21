import contextlib
import io
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))
import channels
import export_youtube
import playlists
from test_tts_and_thumbnail_defaults import packaging_doc, test_workspace


class PlaylistCatalogTests(unittest.TestCase):
    def test_catalog_has_localized_copy_for_all_six_active_channels(self):
        catalog = playlists.load_catalog()
        self.assertEqual(len(catalog['channels']), 6)
        roster = {entry['id']: entry for entry in channels.load_channels()}
        for channel in catalog['channels']:
            self.assertEqual(len(channel['playlists']), 5)
            self.assertEqual(sum(entry['kind']=='core' for entry in channel['playlists']), 4)
            for entry in channel['playlists']:
                self.assertEqual(entry['language'], roster[channel['channel_id']]['language'])
                self.assertGreater(len(entry['description']), 50)
                self.assertEqual(entry['youtube_playlist_id'], '')

    def test_suggestions_are_not_saved_as_selections(self):
        doc = {'channel_id': 'moc-vy', 'topic': 'Giao thương Hội An và đời sống thương nhân'}
        bundle = playlists.episode_playlists(doc)
        self.assertEqual(bundle['status'], 'pending_selection')
        self.assertEqual(bundle['primary_id'], '')
        self.assertEqual(bundle['selected'], [])
        self.assertEqual(bundle['recommendations'][0]['id'], 'moc-vy-cho-giao-thuong')
        self.assertNotIn('youtube_metadata', doc)

    def test_war_priority_and_new_mission_scopes(self):
        war = playlists.episode_playlists({'channel_id':'levi-solace', 'topic':'Stalingrad campaign supply lines'})
        self.assertEqual(war['recommendations'][0]['id'], 'levi-solace-war-logistics')
        civilization = playlists.episode_playlists({'channel_id':'rei-asatsuki', 'topic':'明治の都市と文明を救う'})
        self.assertIn('rei-asatsuki-edo-life', [p['id'] for p in civilization['recommendations']])
        nature = playlists.episode_playlists({'channel_id':'moc-vy', 'topic':'Xanh hóa Sahara và hệ quả khí hậu'})
        self.assertEqual(nature['recommendations'][0]['id'], 'moc-vy-nghe-sinh-ke')
        substring = playlists.episode_playlists({'channel_id':'levi-solace', 'topic':'Why important inventions mattered'})
        self.assertNotIn('levi-solace-transport', [p['id'] for p in substring['recommendations']])

    def test_invalid_assignment_is_rejected(self):
        cases = [
            {'primary_id':'levi-solace-engineering'},
            {'primary_id':'moc-vy-doi-song', 'additional_ids':['moc-vy-doi-song']},
            {'additional_ids':['moc-vy-doi-song']},
            {'primary_id':'moc-vy-doi-song', 'additional_ids':['moc-vy-nghe-sinh-ke','moc-vy-cho-giao-thuong','moc-vy-phong-tuc-xa-hoi']},
            {'primary_id':'moc-vy-doi-song', 'additional_ids':'moc-vy-nghe-sinh-ke'},
            [],
        ]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                playlists.episode_playlists({'channel_id':'moc-vy', 'youtube_metadata':{'playlists':value}})

    def test_real_youtube_id_is_kept_separate_and_labeled_unverified(self):
        catalog = playlists.load_catalog(archived=True)
        selected = next(c for c in catalog['channels'] if c['channel_id']=='moc-vy')['playlists'][0]
        selected['youtube_playlist_id'] = 'PL_exampleProvidedId123'
        with patch.object(playlists, 'load_catalog', return_value=catalog):
            bundle = playlists.episode_playlists({'channel_id':'moc-vy', 'youtube_metadata':{
                'playlists':{'primary_id':'moc-vy-doi-song'}}})
        self.assertEqual(bundle['selected'][0]['platform_status'], 'id_recorded_unverified')
        self.assertEqual(bundle['selected'][0]['youtube_url'], 'https://www.youtube.com/playlist?list=PL_exampleProvidedId123')


class PlaylistExportTests(unittest.TestCase):
    def test_selected_upload_package_includes_title_description_and_roles(self):
        for channel in channels.load_channels():
            with self.subTest(channel=channel['id']), test_workspace() as folder:
                catalog = playlists.channel_playlists(channel['id'])
                doc = packaging_doc(channel['id'], {'en':'BREAD WAS PAY', 'vi':'BÁNH LÀ LƯƠNG',
                                                   'es':'PAN COMO PAGA', 'ja':'パンが給料', 'ko':'빵이 월급'}[channel['language']])
                doc['youtube_metadata']['playlists'] = {'primary_id':catalog[0]['id'],
                    'additional_ids':[catalog[1]['id']], 'selection_reason':'The central story fits these scopes.'}
                doc['youtube_metadata']['selected_candidate_id'] = 'scene'
                os.makedirs(os.path.join(folder,'thumbnails'))
                with open(os.path.join(folder,'thumbnails','scene.png'),'wb') as handle:
                    handle.write(b'Existing reviewed image placeholder')
                os.makedirs(os.path.join(folder,'research'))
                with open(os.path.join(folder,'research','packaging-test.md'),'w') as handle:
                    handle.write('Dated discovery snapshot')
                with open(os.path.join(folder,'beats.json'),'w',encoding='utf-8') as handle:
                    json.dump(doc,handle,ensure_ascii=False)
                with contextlib.redirect_stdout(io.StringIO()):
                    export_youtube.run(folder)
                with open(os.path.join(folder,'youtube-upload.txt'),encoding='utf-8') as handle:
                    upload = handle.read()
                self.assertIn('7. PLAYLISTS',upload)
                self.assertIn('PRIMARY: '+catalog[0]['title'],upload)
                self.assertIn('ADDITIONAL: '+catalog[1]['title'],upload)
                self.assertIn(catalog[0]['description'],upload)
                with open(os.path.join(folder,'youtube-playlists.json'),encoding='utf-8') as handle:
                    data = json.load(handle)
                self.assertEqual(data['status'],'selected')
                self.assertEqual(data['selected'][0]['platform_status'],'create_or_link_in_studio')

    def test_playlist_export_is_available_while_thumbnail_is_pending(self):
        with test_workspace() as folder:
            doc = packaging_doc('moc-vy','ĐỦ TIỀN KHÔNG?')
            doc['topic'] = 'Chợ Hội An và giao thương Việt Nam'
            os.makedirs(os.path.join(folder,'research'))
            with open(os.path.join(folder,'research','packaging-test.md'),'w') as handle:
                handle.write('Dated discovery snapshot')
            with open(os.path.join(folder,'beats.json'),'w',encoding='utf-8') as handle:
                json.dump(doc,handle,ensure_ascii=False)
            with contextlib.redirect_stdout(io.StringIO()):
                export_youtube.run(folder)
            self.assertFalse(os.path.exists(os.path.join(folder,'youtube-upload.txt')))
            self.assertTrue(os.path.isfile(os.path.join(folder,'youtube-playlists.txt')))
            with open(os.path.join(folder,'youtube-playlists.json'),encoding='utf-8') as handle:
                self.assertEqual(json.load(handle)['status'],'pending_selection')

    def test_new_bind_seeds_empty_playlist_choice_and_show_lists_current_catalog(self):
        with test_workspace() as folder:
            channel = dict(channels.resolve('vi-sao-noi-nay'), destination=folder)
            with patch.object(channels,'resolve',return_value=channel), contextlib.redirect_stdout(io.StringIO()):
                channels.bind('vi-sao-noi-nay','playlist-test')
            with open(os.path.join(folder,'playlist-test','beats.json'),encoding='utf-8') as handle:
                data = json.load(handle)
            self.assertEqual(data['youtube_metadata']['playlists']['primary_id'],'')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                channels.show('vi-sao-noi-nay')
            self.assertEqual(len(json.loads(output.getvalue())['playlists']),5)


if __name__ == '__main__':
    unittest.main()
