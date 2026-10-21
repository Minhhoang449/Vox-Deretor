"""Regression checks for the actual WAV/cache and thumbnail export paths."""
import contextlib
import io
import json
import os
import sys
import shutil
import unittest
import uuid
from unittest.mock import Mock, patch

import numpy as np
import soundfile as sf

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, SCRIPTS)

import omnivoice_tts
import tts_settings
import vieneu_tts


@contextlib.contextmanager
def test_workspace():
    # Python 3.12's Windows mode-0700 temp ACL can exclude the restricted runner.
    # Use a normal directory under the writable checkout instead.
    root = os.path.abspath(os.path.join(SCRIPTS, '..', 'tmp', 'tts-thumbnail-tests'))
    folder = os.path.join(root, uuid.uuid4().hex)
    os.makedirs(folder)
    try:
        yield folder
    finally:
        if os.path.commonpath([root, os.path.abspath(folder)]) != root:
            raise ValueError('Test cleanup path escaped its workspace.')
        shutil.rmtree(folder)


class TtsDefaultsTests(unittest.TestCase):
    def test_real_defaults_and_explicit_episode_override(self):
        cfg = omnivoice_tts.pipeline_doc()
        self.assertEqual(tts_settings.effective_tts_settings({}, cfg['omnivoice']), (0.9, 0.8))
        self.assertEqual(tts_settings.effective_tts_settings({}, cfg['vieneu']), (1.0, 0.8))
        self.assertEqual(cfg['omnivoice']['num_step'], 32)
        self.assertEqual(tts_settings.effective_tts_settings(
            {'tts_speed': 1.1, 'tts_pause_after_period_seconds': 0}, cfg['omnivoice']), (1.1, 0))

    def test_boundaries_preserve_decimal_title_initials_and_japanese(self):
        self.assertEqual(tts_settings.split_period_pauses('Dr. A. Reed paid 1.25 coins. Then left.'),
                         [('Dr. A. Reed paid 1.25 coins.', True), ('Then left.', True)])
        self.assertEqual(tts_settings.split_period_pauses('水がない。「困った。」次へ。'),
                         [('水がない。', True), ('「困った。」', True), ('次へ。', True)])
        self.assertEqual(tts_settings.split_period_pauses('Wait... still thinking'),
                         [('Wait... still thinking', False)])

    def test_exact_inserted_samples_with_edge_silence_and_tail(self):
        rate = 1000
        signal = np.r_[np.zeros(100), np.ones(100), np.zeros(100)]
        audio = tts_settings.join_period_audio([signal, signal], [('A.', True), ('B.', True)], rate, 0.8)
        # Edge guards remain 5 ms; the inserted silence itself is exactly 800 samples.
        self.assertEqual(len(audio), 100 + 100 + 5 + 800 + 5 + 100 + 5 + 800)
        self.assertTrue(np.all(audio[205:1005] == 0))
        self.assertTrue(np.all(audio[-800:] == 0))

    def test_invalid_settings_stop(self):
        cfg = {'default_speed': 0.9, 'pause_after_period_seconds': 0.8}
        for overrides in ({'tts_speed': 0}, {'tts_speed': float('nan')},
                          {'tts_pause_after_period_seconds': -1}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                tts_settings.effective_tts_settings(overrides, cfg)

    def test_runners_write_pauses_reuse_cache_and_invalidate_changed_pause(self):
        for engine, module, language in [('omnivoice', omnivoice_tts, 'en'),
                                         ('vieneu', vieneu_tts, 'vi')]:
            with self.subTest(engine=engine), test_workspace() as folder:
                cfg = dict(omnivoice_tts.pipeline_doc()[engine])
                cfg['sample_rate'] = 1000
                doc = {'channel_id': 'moc-vy' if language == 'vi' else 'hollis-ridge',
                       'language': language, 'voice': {'language': language},
                       'beats': [{'id': 'a', 'narration': 'First sentence. Second sentence.'}]}
                with open(os.path.join(folder, 'beats.json'), 'w', encoding='utf-8') as handle:
                    json.dump(doc, handle)
                model = Mock(sampling_rate=1000, sample_rate=1000)
                model.generate.return_value = [np.ones(1000), np.ones(1000)]
                model.infer.return_value = np.ones(1000)
                with contextlib.ExitStack() as stack:
                    stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                    stack.enter_context(patch.object(module, 'load_model', return_value=model))
                    stack.enter_context(patch.object(module, 'probe_dur', side_effect=lambda p: sf.info(p).duration))
                    if engine == 'omnivoice':
                        stack.enter_context(patch.object(module, 'speech_config', return_value=cfg))
                        stack.enter_context(patch.object(module, 'voice_prompt', return_value='clone'))
                    else:
                        stack.enter_context(patch.object(module, 'vieneu_config', return_value=cfg))
                        stack.enter_context(patch.object(module, 'ensure_python'))
                        stack.enter_context(patch.object(module, 'saved_voice_path', return_value='missing-test-voice.json'))
                        stack.enter_context(patch.object(module, 'load_saved_voice', return_value=('clone', {})))
                    module.run(folder)
                    waveform, rate = sf.read(os.path.join(folder, 'audio', 'narr_a.wav'))
                    self.assertEqual(rate, 1000)
                    self.assertEqual(len(waveform), 3600)
                    self.assertTrue(np.all(waveform[1000:1800] == 0))
                    self.assertTrue(np.all(waveform[-800:] == 0))
                    if engine == 'omnivoice':
                        self.assertEqual(model.generate.call_args.kwargs['speed'], 0.9)
                        self.assertEqual(model.generate.call_args.kwargs['num_step'], 32)
                        self.assertEqual(model.generate.call_count, 1)
                    else:
                        self.assertEqual(model.infer.call_count, 2)
                    model.reset_mock()
                    module.run(folder)
                    model.generate.assert_not_called()
                    model.infer.assert_not_called()
                    cfg['pause_after_period_seconds'] = 0.6
                    module.run(folder)
                    waveform, _ = sf.read(os.path.join(folder, 'audio', 'narr_a.wav'))
                    self.assertEqual(len(waveform), 3200)
                    if engine == 'omnivoice':
                        model.generate.assert_called_once()
                    else:
                        self.assertEqual(model.infer.call_count, 2)

    def test_vieneu_rejects_unsupported_speed_before_model_load(self):
        with test_workspace() as folder:
            with open(os.path.join(folder, 'beats.json'), 'w', encoding='utf-8') as handle:
                json.dump({'channel_id': 'moc-vy', 'tts_speed': 0.9}, handle)
            with patch.object(vieneu_tts, 'ensure_python'), patch.object(vieneu_tts, 'load_model') as model:
                with self.assertRaisesRegex(SystemExit, 'native tts_speed 1.0 only'):
                    vieneu_tts.run(folder)
                model.assert_not_called()


def packaging_doc(channel_id, phrase):
    return {
        'channel_id': channel_id, 'aspect': '9:16', 'language': 'stale',
        'channel': {'thumbnail_brand': {'primary_color': '#BADBAD'}},
        'youtube_metadata': {
            'packaging_research': [{'observation': 'An episode-specific question.'}],
            'description': 'The researched historical question and sources.',
            'search_phrases': ['historical household'],
            'candidates': [{'id': 'scene', 'title': 'One historical question',
                            'thumbnail_concept': 'A practical obstacle.',
                            'thumbnail_prompt': 'An illustrated map shows a river and supply bottleneck without characters.',
                            'thumbnail_file': 'thumbnails/scene.png', 'thumbnail_text': phrase}],
        },
    }


if __name__ == '__main__':
    unittest.main()
