import contextlib
import io
import json
import os
import sys
import unittest
from unittest.mock import Mock, patch

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))
import caption_policy as policy
import caption_timeline as timeline
import export_srt
import export_ass
import omnivoice_tts
from test_tts_and_thumbnail_defaults import test_workspace


TEXTS = {
    'vi': 'Bạn có đủ tiền mua gạo. Tiền thuê nhà vẫn đang chờ.',
    'en': 'You can buy bread. The rent is still due.',
    'es': 'Puedes comprar pan. El alquiler sigue pendiente.',
    'ja': '米を買えます。家賃はまだ払っていません。',
    'ko': '쌀을 살 수 있어요. 집세는 아직 내지 않았어요.',
}


def fixture(folder, language='vi'):
    rate = 24000
    def speech(seconds):
        return 0.2 * np.sin(2*np.pi*180*np.arange(round(seconds*rate))/rate)
    waveform = np.r_[speech(2), np.zeros(round(0.8*rate)), speech(3), np.zeros(round(0.8*rate))]
    os.makedirs(os.path.join(folder, 'audio'))
    audio = os.path.join(folder, 'audio', 'narr_a.wav')
    sf.write(audio, waveform, rate)
    beat = {'id': 'a', 'narration': TEXTS[language], 'narration_audio': audio,
            'narration_dur': 6.6, 'shots': [{'id': '1', 'dur': 7}]}
    doc = {'language': language, 'beats': [beat], 'format': {'fps': 30}}
    with open(os.path.join(folder, 'beats.json'), 'w', encoding='utf-8') as handle:
        json.dump(doc, handle, ensure_ascii=False)
    cfg = policy.resolve_policy(doc, language)
    sentences = policy.split_phrases(TEXTS[language], cfg)
    words = []
    for sentence, start, duration in zip(sentences, [0, 2.8], [2, 3]):
        tokens = list(sentence) if language == 'ja' else sentence.split()
        for i, token in enumerate(tokens):
            words.append({'text': token, 'start': start+duration*i/len(tokens),
                          'end': start+duration*(i+1)/len(tokens)})
    return doc, [{'start': 0.013, 'audio_dur': 6.6, 'beat': beat}], words


class CaptionPolicyTests(unittest.TestCase):
    def test_language_profiles_use_native_readability_limits(self):
        expected = {'en': (42, 20), 'vi': (42, 20), 'es': (42, 17), 'ja': (16, 7), 'ko': (16, 14)}
        for lang, limits in expected.items():
            cfg = policy.resolve_policy({}, lang)
            self.assertEqual((cfg['max_chars_per_line'], cfg['max_cps']), limits)
            self.assertEqual(cfg['max_lines'], 2)
            self.assertEqual(cfg['primary_color'], '&H00FFFFFF')
            self.assertIsNotNone(policy.measured_font(cfg['font_file'], cfg['font_size']))

    def test_sentence_breaks_across_all_languages_preserve_original(self):
        for lang, text in TEXTS.items():
            with self.subTest(language=lang):
                units = policy.split_phrases(text, policy.resolve_policy({}, lang))
                self.assertEqual(len(units), 2)
                joiner = '' if lang == 'ja' else ' '
                self.assertEqual(policy.normalized_text(joiner.join(units), lang), text)
        self.assertEqual(export_srt.split_caption_units(TEXTS['vi'], language='vi'),
                         ['Bạn có đủ tiền mua gạo.', 'Tiền thuê nhà vẫn đang chờ.'])

    def test_names_numbers_and_decimals_stay_intact(self):
        cfg = policy.resolve_policy({}, 'vi')
        text = 'Ở Hội An, người bán hàng phải trả 2,5 triệu đồng trước khi nhận chuyến hàng tiếp theo.'
        units = policy.split_phrases(text, cfg, ['Hội An'])
        self.assertEqual(' '.join(units), text)
        self.assertTrue(any('2,5 triệu đồng' in unit for unit in units))
        for unit in units:
            lines = policy.wrap_lines(unit, cfg, ['Hội An'])
            self.assertLessEqual(len(lines), 2)
            self.assertTrue(any('Hội An' in line for line in lines) if 'Hội An' in unit else True)

    def test_weighted_counting_and_unicode_combining_marks(self):
        self.assertEqual(policy.character_count('東京 ABC', policy.resolve_policy({}, 'ja')), 4)
        self.assertEqual(policy.character_count('한글 ABC.', policy.resolve_policy({}, 'ko')), 4.5)
        self.assertEqual(policy.character_count('a\u0301', policy.resolve_policy({}, 'vi')), 1)

    def test_japanese_preserves_embedded_latin_name_and_number(self):
        cfg = policy.resolve_policy({}, 'ja')
        text = 'New Yorkでは２０２６年に家賃を支払いました。'
        units = policy.split_phrases(text, cfg, ['New York'])
        self.assertTrue(any('New York' in unit for unit in units))
        self.assertTrue(any('２０２６' in unit for unit in units))
        for unit in units:
            lines = policy.wrap_lines(unit, cfg, ['New York'])
            if 'New York' in unit:
                self.assertTrue(any('New York' in line for line in lines))

    def test_pixel_width_and_two_line_enforcement(self):
        cfg = policy.resolve_policy({}, 'en')
        with self.assertRaises(policy.CaptionLayoutError):
            policy.wrap_lines('W'*40, cfg)
        text = ' '.join(['historical']*18)
        units = policy.split_phrases(text, cfg)
        self.assertGreater(len(units), 1)
        self.assertEqual(' '.join(units), text)
        for unit in units:
            self.assertLessEqual(len(policy.wrap_lines(unit, cfg)), 2)

    def test_short_sentences_do_not_merge_across_full_stop(self):
        cfg = policy.resolve_policy({}, 'en')
        result = timeline.prepare_intervals([['Yes.', 0, 0.3], ['The rent is due.', 1.1, 3.1]], 4, cfg)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1]['start'], 1.1)
        self.assertAlmostEqual(result[0]['end'], 5/6, places=6)

    def test_pause_hold_does_not_show_next_sentence_early(self):
        cfg = policy.resolve_policy({}, 'vi')
        result = timeline.prepare_intervals([['Câu đầu.', 0, 2], ['Câu sau.', 2.8, 4.8]], 5.6, cfg)
        self.assertAlmostEqual(result[0]['end'], 2.2)
        self.assertEqual(result[1]['start'], 2.8)

    def test_internal_speech_hole_is_rejected_even_with_full_total_span(self):
        intervals = [['Opening', 0, 0.2], ['Ending', 9.8, 10]]
        ok, metrics = export_srt.validate_alignment_timing(intervals, '', 10, [(0, 10)])
        self.assertFalse(ok)
        self.assertLess(metrics['speech_coverage'], 0.1)
        self.assertGreater(metrics['maximum_uncovered_speech_seconds'], 9)

    def test_silence_is_excluded_from_speech_coverage(self):
        ok, _ = export_srt.validate_alignment_timing([['A.', 0, 2], ['B.', 2.8, 5.8]], '', 6.6,
                                                   [(0, 2), (2.8, 5.8)])
        self.assertTrue(ok)

    def test_compressed_whisperx_times_expand_to_verified_sentence_anchors(self):
        segments = [
            {'text': 'Bạn có đủ tiền mua gạo.', 'start': 0.0, 'end': 2.0},
            {'text': 'Tiền thuê nhà vẫn đang chờ.', 'start': 2.8, 'end': 5.8},
        ]
        words = []
        for segment in segments:
            tokens = segment['text'].split()
            compressed_span = (segment['end'] - segment['start']) / 3
            step = compressed_span / len(tokens)
            for index, token in enumerate(tokens):
                start = segment['start'] + index * step
                words.append({'text': token, 'start': start, 'end': start + step})

        corrected, report = export_srt.calibrate_words_to_sentence_anchors(words, segments, 'vi')

        self.assertTrue(report['applied'])
        self.assertAlmostEqual(corrected[0]['start'], 0.0)
        self.assertAlmostEqual(corrected[5]['end'], 2.0)
        self.assertAlmostEqual(corrected[6]['start'], 2.8)
        self.assertAlmostEqual(corrected[-1]['end'], 5.8)
        self.assertTrue(all(word['sentence_anchor_calibrated'] for word in corrected))

    def test_sentence_anchor_calibration_leaves_mismatched_text_untouched(self):
        words = [{'text': 'Khác', 'start': 0.0, 'end': 0.3}]
        segments = [{'text': 'Bạn có đủ tiền mua gạo.', 'start': 0.0, 'end': 2.0}]

        corrected, report = export_srt.calibrate_words_to_sentence_anchors(words, segments, 'vi')

        self.assertFalse(report['applied'])
        self.assertEqual(corrected, words)

    def test_quality_detects_overlaps_long_cues_and_fast_reading(self):
        cfg = policy.resolve_policy({}, 'en')
        cues = [{'text': 'A long line to read.', 'lines': ['A long line to read.'],
                 'start': 0, 'end': 0.1, 'speech_end': 0.1},
                {'text': 'Another line.', 'lines': ['Another', 'line', 'third line'],
                 'start': 0.05, 'end': 8, 'speech_end': 7.9}]
        errors, warnings = timeline.assess_cues(cues, cfg)
        self.assertTrue(any('overlap' in error for error in errors))
        self.assertTrue(any('too many lines' in error for error in errors))
        self.assertTrue(any('duration exceeds' in error for error in errors))
        self.assertTrue(any('CPS exceeds' in warning for warning in warnings))


class CaptionTimelineIntegrationTests(unittest.TestCase):
    def test_caption_error_stops_assembly_before_visual_render(self):
        import assemble
        import ffmpeg_stills
        with test_workspace() as folder:
            doc, spans, words = fixture(folder)
            doc.update(pipeline='local', visual_mode='revideo_stills')
            doc['format'].update(target_seconds_min=0, target_seconds_max=100)
            doc['beats'][0]['caption_units'] = ['Words not spoken.']
            image = os.path.join(folder, 'placeholder.png')
            with open(image, 'wb') as handle:
                handle.write(b'placeholder image not used by renderer')
            doc['beats'][0]['shots'][0]['keyframe_path'] = image
            with open(os.path.join(folder, 'beats.json'), 'w', encoding='utf-8') as handle:
                json.dump(doc, handle)
            with contextlib.redirect_stdout(io.StringIO()), \
                 patch.object(export_srt, 'load_alignment_model', return_value=(None, 'test unavailable')), \
                 patch.object(ffmpeg_stills, 'render') as render:
                with self.assertRaisesRegex(SystemExit, 'Caption QA failed'):
                    assemble.run(folder)
                render.assert_not_called()

    def test_all_languages_share_exact_text_times_and_one_alignment_build(self):
        for lang in TEXTS:
            with self.subTest(language=lang), test_workspace() as folder:
                doc, spans, words = fixture(folder, lang)
                with contextlib.redirect_stdout(io.StringIO()), \
                     patch.object(export_srt, 'load_alignment_model', return_value=({'device': 'cpu'}, '')) as load, \
                     patch.object(export_srt, 'align_transcript', return_value=(words, False)) as align:
                    accepted = timeline.build(folder, spans)
                    export_srt.run(folder, spans, timeline=accepted)
                    export_ass.run(folder, spans)
                    self.assertEqual(load.call_count, 1)
                    self.assertEqual(align.call_count, 1)
                self.assertEqual(accepted['qa']['status'], 'pass')
                with open(os.path.join(folder, 'final.srt'), encoding='utf-8') as handle:
                    srt = handle.read()
                with open(os.path.join(folder, 'final-captions.ass'), encoding='utf-8') as handle:
                    ass = handle.read()
                self.assertNotIn('\\t(', ass)
                for cue in accepted['cues']:
                    self.assertIn(export_srt.srt_timestamp(cue['start'])+' --> '+export_srt.srt_timestamp(cue['end']), srt)
                    self.assertIn(export_ass.ass_time(cue['start'])+','+export_ass.ass_time(cue['end']), ass)
                    self.assertIn('\n'.join(cue['lines']), srt)
                    self.assertIn(r'\N'.join(cue['lines']), ass)
                    self.assertEqual(round(cue['start']*100), cue['start']*100)

    def test_estimate_is_explicitly_flagged_and_preserves_content(self):
        with test_workspace() as folder:
            doc, spans, words = fixture(folder)
            with contextlib.redirect_stdout(io.StringIO()), patch.object(export_srt, 'load_alignment_model', return_value=(None, 'test unavailable')):
                accepted = timeline.build(folder, spans)
            self.assertEqual(accepted['qa']['status'], 'needs_review')
            self.assertEqual(accepted['qa']['estimated_beats'], ['a'])
            self.assertEqual(' '.join(c['text'] for c in accepted['cues']), TEXTS['vi'])

    def test_reviewed_text_mismatch_writes_failed_report_and_stops(self):
        with test_workspace() as folder:
            doc, spans, words = fixture(folder)
            doc['beats'][0]['caption_units'] = ['Words not spoken.']
            with open(os.path.join(folder, 'beats.json'), 'w', encoding='utf-8') as handle:
                json.dump(doc, handle)
            with patch.object(export_srt, 'load_alignment_model', return_value=(None, 'test unavailable')):
                with self.assertRaisesRegex(SystemExit, 'Caption QA failed'):
                    timeline.build(folder, spans)
            with open(os.path.join(folder, 'captions-qa.json'), encoding='utf-8') as handle:
                self.assertEqual(json.load(handle)['status'], 'fail')

    def test_changed_audio_or_settings_invalidates_accepted_timeline(self):
        with test_workspace() as folder:
            doc, spans, words = fixture(folder)
            with contextlib.redirect_stdout(io.StringIO()), \
                 patch.object(export_srt, 'load_alignment_model', return_value=({'device': 'cpu'}, '')) as load, \
                 patch.object(export_srt, 'align_transcript', return_value=(words, False)):
                first = timeline.build(folder, spans)
                timeline.build(folder, spans)
                self.assertEqual(load.call_count, 1)
                doc['caption_render'] = {'font_size': 58}
                with open(os.path.join(folder, 'beats.json'), 'w', encoding='utf-8') as handle:
                    json.dump(doc, handle)
                second = timeline.build(folder, spans)
                self.assertNotEqual(first['fingerprint'], second['fingerprint'])
                audio = spans[0]['beat']['narration_audio']
                os.utime(audio, ns=(os.stat(audio).st_atime_ns, os.stat(audio).st_mtime_ns+1_000_000))
                third = timeline.build(folder, spans)
                self.assertNotEqual(second['fingerprint'], third['fingerprint'])
                self.assertEqual(load.call_count, 3)

    def test_edited_cache_cannot_override_approved_narration(self):
        with test_workspace() as folder:
            doc, spans, words = fixture(folder)
            with contextlib.redirect_stdout(io.StringIO()), \
                 patch.object(export_srt, 'load_alignment_model', return_value=({'device': 'cpu'}, '')) as load, \
                 patch.object(export_srt, 'align_transcript', return_value=(words, False)):
                first = timeline.build(folder, spans)
                first['cues'][0]['text'] = 'A claim never approved.'
                with open(os.path.join(folder, 'captions-timeline.json'), 'w', encoding='utf-8') as handle:
                    json.dump(first, handle)
                corrected = timeline.build(folder, spans)
                self.assertEqual(load.call_count, 2)
                self.assertEqual(corrected['cues'][0]['text'], 'Bạn có đủ tiền mua gạo.')

    def test_synthesis_sentence_metadata_controls_whisperx_segments(self):
        with test_workspace() as folder:
            doc, spans, words = fixture(folder)
            audio = spans[0]['beat']['narration_audio']
            segments = [{'text': 'Bạn có đủ tiền mua gạo.', 'start': 0, 'end': 2},
                        {'text': 'Tiền thuê nhà vẫn đang chờ.', 'start': 2.8, 'end': 5.8}]
            omnivoice_tts.save_sentence_segments(audio, segments)
            engine = {'device': 'cpu', 'model_name': 'test', 'version': '1',
                      'model': None, 'metadata': None, 'whisperx': Mock()}
            engine['whisperx'].align.return_value = {'word_segments': [{'word': 'Bạn', 'start': 0, 'end': 0.3}]}
            export_srt.align_transcript(engine, audio, folder, 'a', 'vi', TEXTS['vi'])
            self.assertEqual(engine['whisperx'].align.call_args.args[0], segments)
            self.assertEqual(export_srt.sentence_segments(audio, 'Different words.', 'vi'), [])


if __name__ == '__main__':
    unittest.main()
