"""Check new routing and style defaults while preserving recorded episode styles."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import channels
import thumbnail_visual_direction as thumbnails
from animation_prompts import ANIMATION_STYLES

class HumanHistoryPortfolioTests(unittest.TestCase):
    def test_new_defaults_and_saved_style_are_separate(self):
        for c in channels.load_channels():
            with self.subTest(channel=c['id']):
                self.assertEqual(channels.load_channel_visual_dna(c)['default_style'],'chibi-2d')
                self.assertEqual(channels.load_channel_visual_workflow(c)['generated_still_style'],'chibi-2d')
                self.assertEqual(thumbnails.resolve_thumbnail_profile(c['id'])['style'],ANIMATION_STYLES['chibi-2d'])
                saved={'animation_style':'documentary-realistic'}
                self.assertEqual(thumbnails.resolve_thumbnail_profile(c['id'],saved)['style'],ANIMATION_STYLES['documentary-realistic'])

    def test_old_names_do_not_restore_old_story_formats(self):
        expected={'last-safe-minute':'food_origin_process_history','terra-rewired':'invention_material_process_history',
                  'battlefield-bearings':'past_daily_life_task_reconstruction','status-and-systems':'social_rule_origin_case_history',
                  'vi-sao-noi-nay':'human_geography_adaptation_explainer','chikyu-shikumi':'evidence_led_human_history_explainer'}
        for key,fmt in expected.items():
            c=channels.resolve(key)
            self.assertEqual(channels._new_story_premise(c)['format'],fmt)
            self.assertEqual(c['metadata_direction']['public_sources_section'],'omit_by_default')
            self.assertTrue(c['metadata_direction']['internal_claim_ledger_required'])

if __name__=='__main__': unittest.main()
