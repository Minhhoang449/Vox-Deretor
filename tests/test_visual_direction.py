"""Visible-cast scoping and subject-led scenes through production prompt paths."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import animation_prompts as prompts
from cache_keys import stable_hash
import channels
import codex_prompts
from image_reuse import image_sources
import muse_pack

FIXTURE=json.loads((ROOT/'tests/fixtures/sahara-visuals/sequence.json').read_text(encoding='utf-8'))


class VisualDirectionTests(unittest.TestCase):
    def doc(self):
        return {'channel_id':'vi-sao-noi-nay','animation_style':'chibi-2d','aspect':'16:9',
                'visual_bible':{'style':'coherent Q-Version 2D world',
                'characters':[{'id':'lead','description':'Unique violet-cape protagonist',
                               'reference_image':'characters/lead.png'},
                              {'id':'other','description':'Unseen orange-haired operator',
                               'reference_image':'characters/other.png'}]}}

    def shot(self):
        return {'id':'A','scene':'Groundwater feeding a lake in a schematic cutaway',
                'characters':[],'people_policy':'none','image_text_policy':'none','dur':6,
                'animation':{'start':'Connected aquifer and lake','action':'Hold on the relationship',
                             'end':'Supply connection remains visible','camera':'hold'}}

    def test_absent_cast_edits_do_not_affect_either_prompt_or_fingerprint(self):
        doc,shot=self.doc(),self.shot()
        changed=copy.deepcopy(doc)
        changed['visual_bible']['characters'][0]['description']='Completely different absent identity'
        for builder in (prompts.compose_animation_frame_prompt,prompts.compose_animation_motion_prompt):
            with self.subTest(builder=builder.__name__):
                original=builder(doc,{},shot)
                self.assertEqual(stable_hash(original),stable_hash(builder(changed,{},shot)))
                self.assertNotIn('Unique violet-cape',original)
                self.assertNotIn('Unseen orange-haired',original)
                self.assertNotIn(prompts.CHIBI_FRAME_GUARD,original)
                self.assertNotIn(prompts.CHIBI_MOTION_GUARD,original)
                self.assertEqual(codex_prompts.reference_images(doc,shot),[])

    def test_visible_cast_only_scopes_specs_and_references(self):
        doc,shot=self.doc(),self.shot()
        shot.update(characters=['lead'],people_policy='listed')
        self.assertEqual(codex_prompts.reference_images(doc,shot),['characters/lead.png'])
        for builder in (prompts.compose_animation_frame_prompt,prompts.compose_animation_motion_prompt):
            prompt=builder(doc,{},shot)
            self.assertIn('Unique violet-cape',prompt)
            self.assertNotIn('Unseen orange-haired',prompt)
        changed=copy.deepcopy(doc)
        changed['visual_bible']['characters'][0]['description']='Changed visible identity'
        self.assertNotEqual(stable_hash(prompts.compose_animation_frame_prompt(doc,{},shot)),
                            stable_hash(prompts.compose_animation_frame_prompt(changed,{},shot)))

    def test_shared_style_is_identical_across_people_free_and_character_scenes(self):
        doc,shot=self.doc(),self.shot()
        character=copy.deepcopy(shot)
        character.update(characters=['lead'],people_policy='listed')
        style=prompts.ANIMATION_STYLES['chibi-2d']
        for sample in (shot,character):
            self.assertIn(style,prompts.compose_animation_frame_prompt(doc,{},sample))
            self.assertIn(style,prompts.compose_animation_motion_prompt(doc,{},sample))

    def test_contextual_people_do_not_import_the_named_protagonist(self):
        doc,shot=self.doc(),self.shot()
        shot['people_policy']='contextual'
        shot['scene']='A few anonymous workers are small inhabitants beside a wide waterworks'
        self.assertEqual(codex_prompts.reference_images(doc,shot),[])
        prompt=prompts.compose_animation_frame_prompt(doc,{},shot)
        self.assertNotIn('Unique violet-cape',prompt)
        self.assertIn(prompts.CHIBI_FRAME_GUARD,prompt)
        self.assertEqual(prompts.resolve_people_policy(shot),'contextual')

    def test_contradictory_or_invalid_people_rules_are_rejected(self):
        for fields in ({'characters':['lead'],'people_policy':'none'},
                       {'characters':[],'people_policy':'listed'},
                       {'people_policy':'every_scene'}, {'characters':123}):
            shot=dict(self.shot(),**fields)
            with self.subTest(fields=fields),self.assertRaises(SystemExit):
                prompts.compose_animation_frame_prompt(self.doc(),{},shot)

    def test_legacy_cast_defaults_and_open_representation_remain_supported(self):
        shot=self.shot()
        shot.pop('people_policy')
        self.assertEqual(prompts.resolve_people_policy(shot),'none')
        shot['characters']='lead'
        self.assertEqual(prompts.resolve_people_policy(shot),'listed')
        shot['visual_intent']={'representation':'custom ecological transect comparison',
                               'detail_density':'sparse where a mechanism must read'}
        prompt=prompts.compose_animation_frame_prompt(self.doc(),{},shot)
        self.assertIn('custom ecological transect comparison',prompt)
        self.assertIn('sparse where a mechanism must read',prompt)

    def test_character_free_original_exports_with_no_reference_stage(self):
        with tempfile.TemporaryDirectory() as folder:
            doc=dict(self.doc(),project='visual-unit-test',visual_plan={'unit_test':True},
                     format={'target_seconds':6,'scene_seconds_min':3,'scene_seconds_max':10},
                     beats=[{'id':'B','shots':[self.shot()]}])
            path=Path(folder)/'beats.json'
            path.write_text(json.dumps(doc),encoding='utf-8')
            # Explicit synthetic unit fixture; do not forge a YouTube discovery report.
            with patch.object(codex_prompts,'require_research'),contextlib.redirect_stdout(io.StringIO()):
                codex_prompts.write_prompts(folder)
            manifest=json.loads((Path(folder)/'imagegen/manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['assets'][0]['people_policy'],'none')
            self.assertEqual(manifest['assets'][0]['reference_images'],[])
            self.assertFalse((Path(folder)/'characters').exists())
            self.assertEqual(manifest['image_summary']['unique_images'],1)

    def test_muse_environment_export_ignores_unused_unavailable_character_references(self):
        with tempfile.TemporaryDirectory() as folder:
            doc=dict(self.doc(),project='visual-unit-test',
                     beats=[{'id':'B','shots':[self.shot()]}])
            (Path(folder)/'beats.json').write_text(json.dumps(doc),encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                muse_pack.export(folder)
            metadata=json.loads((Path(folder)/'muse/001/meta.json').read_text(encoding='utf-8'))
            self.assertEqual(metadata['character_references'],[])
            self.assertEqual(metadata['generation_mode'],'text_to_video')
            self.assertFalse((Path(folder)/'muse/characters').exists())

    def test_full_image_reuse_cannot_remove_anonymous_people(self):
        source=dict(self.shot(),people_policy='contextual')
        alias={'id':'B','people_policy':'none','reuse_image_from':'BA','reuse_reason':'same site'}
        doc={'beats':[{'id':'B','shots':[source,alias]}]}
        with self.assertRaisesRegex(SystemExit,'people policy'):
            image_sources(doc)

    def test_show_and_context_use_live_visual_dna_without_rewriting_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            current=dict(channels.resolve('vi-sao-noi-nay'),destination=folder)
            with patch.object(channels,'resolve',return_value=current),contextlib.redirect_stdout(io.StringIO()):
                channels.bind('vi-sao-noi-nay','visual','Selected mission')
                path=Path(folder)/'visual/beats.json'
                doc=json.loads(path.read_text(encoding='utf-8'))
                self.assertEqual(doc['visual_dna'],channels.load_visual_dna())
                doc['visual_dna']={'revision':'obsolete-character-everywhere'}
                path.write_text(json.dumps(doc),encoding='utf-8')
                before=path.read_bytes()
                context=channels.authoring_context('vi-sao-noi-nay','visual')
                self.assertEqual(context['visual_dna'],channels.load_visual_dna())
                self.assertEqual(path.read_bytes(),before)

    def test_sahara_sequence_uses_real_primary_subjects_and_filtered_cast(self):
        for beat in FIXTURE['beats']:
            shot=beat['shots'][0]
            with self.subTest(scene=beat['id']):
                prompt=prompts.compose_animation_frame_prompt(FIXTURE,beat,shot)
                self.assertIn(shot['visual_intent']['primary_subject'],prompt)
                self.assertIn(shot['visual_intent']['representation'],prompt)
                self.assertTrue(beat['narration_span'])
                if shot['people_policy']=='none':
                    self.assertNotIn('fictional one-off operator',prompt)
                    self.assertNotIn(prompts.CHIBI_FRAME_GUARD,prompt)
                    self.assertEqual(codex_prompts.reference_images(FIXTURE,shot),[])


if __name__=='__main__':
    unittest.main()
