"""Regression coverage for final reuse gating and purpose-led camera behavior."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import assemble
import animation_prompts
import ffmpeg_stills
from image_reuse import apply_image_reuse, image_sources
from image_reuse_qa import build_report
from stills_camera import plan_cameras, shot_camera_metadata


class PurposeCameraTests(unittest.TestCase):
    def shot(self, **fields):
        return dict({'image': 'one.png', 'dur': 6, 'camera': 'auto'}, **fields)

    def plan(self, shots):
        return plan_cameras(shots, {'camera_policy': 'balanced'})

    def test_pan_zoom_remain_enabled_without_a_shot_index_cycle(self):
        shots = [self.shot(scene='Wide coastal landscape', camera_direction='right'),
                 self.shot(image='two.png', scene='Wide coastal landscape'),
                 self.shot(image='three.png', scene='Close-up of a mechanical joint')]
        self.assertEqual([s['camera'] for s in self.plan(shots)], ['pan right', 'gentle zoom-out', 'gentle zoom-in'])
        inserted = self.plan([self.shot(image='prefix.png', camera_intent='read')] + shots)[1:]
        self.assertEqual([s['camera'] for s in self.plan(shots)], [s['camera'] for s in inserted])

    def test_readable_relationships_do_not_move_to_force_variety(self):
        shots = [self.shot(image=str(i)+'.png', scene=scene) for i,scene in enumerate(
            ['A labeled map', 'A cross-section of the reservoir', 'A comparison chart', 'Bản đồ và sơ đồ', '地図と断面図'])]
        self.assertEqual({s['camera'] for s in self.plan(shots)}, {'locked-off'})
        self.assertEqual(ffmpeg_stills.camera_parameters('locked-off', 1920), (1,1,0,0))

    def test_text_requires_authored_crop_safety_for_automatic_motion(self):
        shot = self.shot(camera_intent='follow', camera_direction='right', in_scene_text='WATER')
        self.assertEqual(self.plan([shot])[0]['camera'], 'locked-off')
        shot['camera_motion_safe'] = True
        self.assertEqual(self.plan([shot])[0]['camera'], 'pan right')

    def test_unknown_direction_is_not_guessed(self):
        self.assertEqual(self.plan([self.shot(camera_intent='follow')])[0]['camera'], 'locked-off')
        with self.assertRaises(ValueError):
            self.plan([self.shot(camera_intent='follow', camera_direction='sideways')])
        with self.assertRaises(ValueError):
            self.plan([self.shot(camera_motion_safe='yes')])

    def test_authored_moves_are_preserved_even_with_labels(self):
        shot = self.shot(camera='pan left', in_scene_text='WATER')
        self.assertEqual(self.plan([shot])[0]['camera'], 'pan left')
        shot.update(camera='gentle zoom-in', camera_policy='preserve')
        self.assertEqual(self.plan([shot])[0]['camera'], 'gentle zoom-in')

    def test_short_and_reused_auto_shots_hold(self):
        self.assertEqual(self.plan([self.shot(dur=3, scene='Coastal landscape')])[0]['camera'], 'locked-off')
        shots = [self.shot(scene='Coastal landscape'), self.shot(scene='Coastal landscape')]
        self.assertEqual(self.plan(shots)[1]['camera'], 'locked-off')
        self.assertEqual(self.plan([self.shot(reuse_image_from='B01A', camera_intent='reveal')])[0]['camera'], 'locked-off')

    def test_baked_source_labels_are_inherited_and_planning_is_idempotent(self):
        shot = {'reuse_image_from':'B01A', 'animation':{'camera_intent':'follow', 'camera_direction':'right'}}
        metadata = shot_camera_metadata(shot, {'in_scene_text':'河川'})
        self.assertEqual(metadata['in_scene_text'], '河川')
        planned = self.plan([self.shot(scene='Coastal landscape'), self.shot(image='two.png', camera_intent='read')])
        self.assertEqual(planned, self.plan(planned))


class FinalReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def image(self, i):
        path = self.folder / f'{i}.png'
        Image.new('RGB',(32,18),(i % 256, i // 256, 32)).save(path)
        return str(path)

    def segments(self, original_count, repeat_sources, original_seconds=3, repeat_seconds=6):
        images = [self.image(i) for i in range(original_count)]
        originals = [{'image':p,'dur':original_seconds,'beat_id':'B','shot_id':str(i)} for i,p in enumerate(images)]
        reused = [{'image':images[i],'dur':repeat_seconds,'beat_id':'B','shot_id':'R'+str(n), 'reuse_image_from':'B'+str(i)} for n,i in enumerate(repeat_sources)]
        return originals + reused

    def test_assembly_rechecks_declared_caps_before_audio_or_render(self):
        doc={'pipeline':'local','visual_mode':'revideo_stills','beats':[{'id':'B01','shots':[
            {'id':'A'}, {'id':'B','reuse_image_from':'B01A','reuse_reason':'same'},
            {'id':'C','reuse_image_from':'B01A','reuse_reason':'same'}, {'id':'D'}]}]}
        (self.folder/'beats.json').write_text(json.dumps(doc),encoding='utf-8')
        with patch.object(assemble,'refuse_out_dir'), patch.object(assemble,'probe_dur') as audio, patch.object(ffmpeg_stills,'render') as render:
            with self.assertRaisesRegex(SystemExit,'35% limit'):
                assemble.run(str(self.folder))
            audio.assert_not_called()
            render.assert_not_called()

    def test_duration_share_is_reviewed_without_becoming_a_new_hard_cap(self):
        report=build_report(self.segments(65,list(range(35)),repeat_seconds=10))
        self.assertEqual(report['reused_shots'],35)
        self.assertEqual(report['reused_duration_percent'],64.22)
        self.assertTrue(any(w['code']=='duration_share_above_shot_cap' and w['blocking'] is False for w in report['warnings']))

    def test_renamed_identical_images_cannot_bypass_limits(self):
        segs=self.segments(2,[0,0])
        for i,seg in enumerate(segs[2:]):
            copied=self.folder/f'copy{i}.png'
            shutil.copy2(seg['image'],copied)
            seg['image']=str(copied)
            seg.pop('reuse_image_from')
        with self.assertRaisesRegex(SystemExit,'35% limit'):
            build_report(segs)

    def test_original_appearance_cap_uses_effective_image_content(self):
        with self.assertRaisesRegex(SystemExit,'maximum is 2'):
            build_report(self.segments(7,[0,0,0]))

    def test_nearby_returns_report_actual_duration(self):
        segs=self.segments(4,[0,1])
        segs=[segs[0],segs[4],segs[1],segs[2],segs[5],segs[3]]
        segs[1]['dur']=7.5
        report=build_report(segs)
        self.assertTrue(report['nearby_returns'])
        self.assertEqual(report['reused_seconds'],13.5)

    def test_changed_visual_state_blocks_chained_reuse(self):
        shots=[{'id':'A','visual_state':{'tank':'full'}},
               {'id':'B','reuse_image_from':'BA','reuse_reason':'same'},
               {'id':'C','reuse_image_from':'BB','reuse_reason':'same','visual_state':{'tank':'empty'}}]
        doc={'beats':[{'id':'B','shots':shots}]}
        with self.assertRaisesRegex(SystemExit,'visual_state'):
            image_sources(doc)
        shots[2]['visual_state']={'tank':'full'}
        self.assertEqual(image_sources(doc)['BC'],'BA')

    def test_changed_source_state_changes_the_generation_prompt(self):
        doc={'animation_style':'chibi-2d','image_text_policy':'none'}
        shot={'scene':'A tank in a cross-section','visual_state':{'tank':'full'},'image_text_policy':'none'}
        first=animation_prompts.compose_animation_frame_prompt(doc,{},shot)
        shot['visual_state']={'tank':'empty'}
        second=animation_prompts.compose_animation_frame_prompt(doc,{},shot)
        self.assertNotEqual(first,second)
        self.assertIn('"tank": "empty"',second)

    def test_camera_change_invalidates_visual_cache(self):
        image=self.image(42)
        cfg=ffmpeg_stills.settings()
        original=[{'image':image,'dur':6,'camera':'auto','scene':'Coastal landscape'}]
        changed=copy.deepcopy(original)
        changed[0]['camera_intent']='read'
        before=ffmpeg_stills.jobs_for(original,192,108,30,cfg)
        after=ffmpeg_stills.jobs_for(changed,192,108,30,cfg)
        self.assertNotEqual(before[0]['fingerprint'],after[0]['fingerprint'])


if __name__=='__main__':
    unittest.main()
