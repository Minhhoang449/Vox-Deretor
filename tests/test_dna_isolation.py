"""Exercise legacy-plot leakage and setup reruns without changing production."""
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


class DNAIsolationTests(unittest.TestCase):
    def test_retired_mission_plot_is_not_relabelled_as_documentary(self):
        old = {'format':'mission_simulation', 'dna_revision':'mission-simulation-v1',
               'period':'1963', 'place':'Italy', 'subject':'Old mission',
               'opening':'Fictional coalition receives a mission',
               'baseline':'Unlimited granted resources', 'sequence':['Intervene'],
               'mechanisms':['Invented mechanism'], 'answer':'Mission succeeds',
               'consequences':['Invented future'], 'optional_scenario':{'grant':'unlimited'}}
        for profile in channels.load_channels():
            with self.subTest(channel=profile['id']):
                saved = copy.deepcopy(old)
                current = channels._authoring_premise({'story_premise':saved}, profile)
                empty = channels._new_story_premise(profile)
                for field in ('subject','opening','baseline','sequence','mechanisms','answer','consequences','optional_scenario'):
                    self.assertEqual(current[field], empty[field])
                self.assertEqual(current['period'], old['period'])
                self.assertEqual(current['place'], old['place'])
                self.assertEqual(saved, old)

    def test_current_documentary_draft_retains_its_actual_plot(self):
        for profile in channels.load_channels():
            with self.subTest(channel=profile['id']):
                saved=channels._new_story_premise(profile)
                saved.update(opening='Current researched opening', sequence=['A','B'],
                             answer='Supported answer', mechanisms=['Verified mechanism'])
                self.assertEqual(channels._authoring_premise({'story_premise':saved},profile),saved)

    def test_mismatched_revision_or_format_and_unversioned_premises_are_isolated(self):
        profile=channels.load_channels()[0]
        compatible=channels._new_story_premise(profile)
        compatible.update(opening='Old opening', answer='Old answer')
        for changes in ({'dna_revision':'old'}, {'format':'mission_simulation'}, {'dna_revision':''}):
            with self.subTest(changes=changes):
                current=channels._authoring_premise({'story_premise':{**compatible,**changes}},profile)
                self.assertEqual(current['opening'],'')
                self.assertEqual(current['answer'],'')

    def test_explicit_selected_scenario_exception_is_preserved(self):
        profile=channels.load_channels()[0]
        saved={'format':'mission_simulation','exception_reason':'User explicitly selected this hypothetical',
               'opening':'Selected scenario', 'objective':'Specific authorized objective'}
        current=channels._authoring_premise({'story_premise':saved},profile)
        self.assertEqual(current['opening'],saved['opening'])
        self.assertEqual(current['objective'],saved['objective'])

    def test_actual_context_preserves_disk_but_separates_recorded_plot_on_all_six_channels(self):
        for original in channels.load_channels():
            with self.subTest(channel=original['id']), tempfile.TemporaryDirectory() as folder:
                profile={**original,'destination':folder}
                with patch.object(channels,'resolve',return_value=profile),contextlib.redirect_stdout(io.StringIO()):
                    channels.bind(profile['id'],'isolation-probe',topic='Explicit audit topic')
                    path=Path(folder)/'isolation-probe/beats.json'
                    doc=json.loads(path.read_text(encoding='utf-8'))
                    old={'format':'mission_simulation','dna_revision':'mission-simulation-v1',
                         'opening':'Granted mission', 'answer':'Hypothetical success'}
                    doc['story_premise']=old
                    doc['beats']=[{'narration':'Existing approved production words'}]
                    path.write_text(json.dumps(doc),encoding='utf-8')
                    before=path.read_bytes()
                    ctx=channels.authoring_context(profile['id'],'isolation-probe')
                self.assertEqual(ctx['story_premise']['opening'],'')
                self.assertEqual(ctx['story_premise']['answer'],'')
                self.assertEqual(ctx['recorded_story_premise'],old)
                self.assertIn('production history',ctx['recorded_context_policy'])
                self.assertEqual(path.read_bytes(),before)

    def test_documentary_reconstruction_remains_evidence_bounded(self):
        reconstruction=(ROOT/'references/history-scene-reconstruction.md').read_text(encoding='utf-8')
        self.assertTrue(reconstruction.startswith('# Reconstructing documented scenes'))
        self.assertIn('Only when the episode explicitly selects a counterfactual',reconstruction)


if __name__=='__main__':
    unittest.main()
