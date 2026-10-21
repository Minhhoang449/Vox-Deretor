"""Exercise the current authoring context, sample provenance and voice isolation."""
import contextlib
import copy
import io
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import channels
import animation_prompts


class ChannelDNAAuditTests(unittest.TestCase):
    def test_six_contracts_reach_real_authoring_context(self):
        for original in channels.load_channels():
            profile=copy.deepcopy(original)
            with self.subTest(channel=profile['id']), tempfile.TemporaryDirectory() as folder:
                profile['destination']=folder
                with patch.object(channels,'resolve',return_value=profile),contextlib.redirect_stdout(io.StringIO()):
                    channels.bind(profile['id'],'dna-audit',topic='Explicit non-production audit question')
                    context=channels.authoring_context(profile['id'],'dna-audit')
                self.assertEqual(context['writing_contract'], profile['writing_contract'])
                self.assertEqual(context['story_format'],profile['story_format'])
                self.assertEqual(context['research_basis'],profile['research_basis'])
                self.assertEqual(context['visual_grammar'],profile['visual_grammar'])
                self.assertEqual(context['image_text_policy'],'contextual')
                self.assertEqual(context['visual_text_direction'],profile['visual_text_direction'])
                self.assertEqual(context['avoid'],profile['avoid'])
                self.assertEqual(context['packaging_direction'],profile['packaging_direction'])
                episode=json.loads((Path(context['episode_dir'])/'beats.json').read_text(encoding='utf-8'))
                self.assertEqual(episode['image_text_policy'],'contextual')

    def test_all_six_channel_text_directions_reach_still_prompts(self):
        for channel in channels.load_channels():
            with self.subTest(channel=channel['id']):
                doc={
                    'animation_style':'chibi-2d',
                    'aspect':'16:9',
                    'channel':channel,
                    'image_text_policy':channel['image_text_policy'],
                }
                shot={
                    'id':'TEXT01',
                    'scene':'A researched explanatory map',
                    'people_policy':'none',
                    'in_scene_text':'EXACT LABEL',
                    'text_placement':'on the map legend',
                }
                prompt=animation_prompts.compose_animation_frame_prompt(doc,{},shot)
                self.assertIn(channel['visual_text_direction'],prompt)
                self.assertIn('Render this exact wording: "EXACT LABEL"',prompt)
                self.assertIn('Do not add other wording',prompt)

    def test_six_male_voices_are_isolated_and_have_clone_files(self):
        roster=channels.load_channels()
        self.assertEqual(len({c['voice'] for c in roster}),6)
        self.assertEqual(len({c['voice_reference']['audio'] for c in roster}),6)
        for c in roster:
            self.assertEqual(c['voice_gender'],'male')
            self.assertEqual(c['voice_engine'],'vieneu-v3-turbo' if c['language']=='vi' else 'omnivoice')
            key='vieneu_voice' if c['language']=='vi' else 'prompt'
            self.assertTrue(Path(c['voice_reference'][key]).is_file())
            self.assertTrue(Path(c['voice_reference']['original_audio']).is_file())
            self.assertEqual(len(c['voice_reference']['source_sha256']),64)
        vi=next(c for c in roster if c['language']=='vi')
        self.assertEqual(vi['narration_calibration']['voice_id'], vi['voice'])
        self.assertGreater(vi['narration_calibration']['sample_speech_seconds'], 0)

    def test_voice_overrides_preserve_live_profiles(self):
        overrides=json.loads((ROOT/'config/channel-voice-overrides.json').read_text(encoding='utf-8'))['channels']
        for c in channels.load_channels():
            self.assertEqual(overrides[c['id']]['voice_reference'],c['voice_reference'])
            self.assertTrue(c['writing_contract']['execution_check'])
            self.assertTrue(c['research_basis'])

    def test_reference_evidence_and_scores_are_explicit(self):
        audit=json.loads((ROOT/'reports/script-progression-fix-2026-10-16/review.json').read_text(encoding='utf-8'))
        self.assertEqual(len(audit['channels']),6)
        self.assertIn('unapproved',audit['scope'])
        for channel_id,row in audit['channels'].items():
            self.assertEqual(len(row['story']),8)
            self.assertEqual(len(row['retention']),5)
            self.assertTrue(all(score in (0,1,2) for score in row['story']+row['retention']))
            self.assertEqual(row['story'][5],2)
            self.assertTrue(row['sources'])
            self.assertTrue(row['limit'])
            sample=ROOT/'reports/script-quality-retest-2026-10-16/samples'/f'{channel_id}-v3-proposed.md'
            self.assertEqual(hashlib.sha256(sample.read_bytes()).hexdigest(),audit['hashes'][channel_id])
            self.assertIn(row['text'],sample.read_text(encoding='utf-8'))

    def test_prompt_probe_does_not_require_a_hypothetical(self):
        guard=animation_prompts.SCENARIO_CONTEXT_GUARD
        self.assertIn('Only if an explicitly',guard)
        self.assertIn('Do not introduce a mission',guard)
        probes=json.loads((ROOT/'reports/dna-audit-2026-10-16/visual-prompt-probes.json').read_text(encoding='utf-8'))
        self.assertEqual(len(probes),6)
        for row in probes:
            self.assertIn(row['shot']['in_scene_text'],row['prompt'])
            self.assertIn('prompt-only',row['status'])

    def test_active_guidance_has_no_former_intervention_imperatives(self):
        beat=(ROOT/'references/beat-layer.md').read_text(encoding='utf-8')
        fiction=(ROOT/'references/historical-fiction.md').read_text(encoding='utf-8')
        cast=(ROOT/'skills/agentara-video-character-design/SKILL.md').read_text(encoding='utf-8')
        review=(ROOT/'references/templates/post-publication-review.md').read_text(encoding='utf-8')
        self.assertNotIn('Follow approved subject exploration, later assignment, causal intervention',beat)
        self.assertNotIn('The active [mission DNA]',fiction)
        self.assertNotIn('Design the carrier this intervention needs',cast)
        self.assertNotIn('subject-opening and mission-introduction',review)


if __name__=='__main__':unittest.main()
