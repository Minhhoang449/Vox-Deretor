"""Narration approval, WAV integrity and review copies protect actual media."""
import copy
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import narration_lock as lock
from narration_review import build, caption_queue, concatenate_wavs
from omnivoice_tts import existing_audio, save_audio_cache


def wav(path, frames=b"\x01\x00"*800, rate=8000):
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(rate); out.writeframes(frames)


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.doc={"channel_id":"test", "episode_slug":"one", "language":"vi",
                  "narration_approval_required":True,
                  "beats":[{"id":"B01", "narration":"Sóng giảm. Bùn đâu?"}]}
        self.source=self.root/'speech.md'
        self.source.write_text('# Draft\n\n## Lời dẫn\nSóng giảm. Bùn đâu?\n\n## Notes\nDo not read.\n',encoding='utf-8')
        self.save()

    def save(self):
        (self.root/'beats.json').write_text(json.dumps(self.doc),encoding='utf-8')

    def record(self):
        return lock.record(self.root,self.source,'Fixture user approval, not production.',section='Lời dẫn')

    def test_missing_record_blocks_new_but_reports_unrecorded_legacy(self):
        self.assertEqual(lock.inspect(self.root)['status'],'blocked')
        self.doc.pop('narration_approval_required')
        self.assertEqual(lock.inspect(self.root,self.doc)['status'],'legacy_unrecorded')

    def test_bind_marks_only_new_projects_as_requiring_the_record(self):
        import channels
        folder=self.root/'binding'
        with patch.object(channels,'episode_dir',return_value=str(folder)), contextlib.redirect_stdout(io.StringIO()):
            channels.bind('vi-sao-noi-nay','binding',topic='Một câu hỏi thử nghiệm')
            path=folder/'beats.json'; doc=json.loads(path.read_text(encoding='utf-8'))
            self.assertTrue(doc['narration_approval_required'])
            doc.pop('narration_approval_required')
            path.write_text(json.dumps(doc),encoding='utf-8')
            channels.bind('vi-sao-noi-nay','binding',topic='Một câu hỏi thử nghiệm')
            self.assertNotIn('narration_approval_required',json.loads(path.read_text(encoding='utf-8')))

    def test_exact_speech_section_excludes_notes_and_ignores_only_whitespace(self):
        result=self.record()
        self.assertEqual(result['speech_sha256'],lock.digest('Sóng giảm. Bùn đâu?'))
        self.doc['beats']=[{'id':'one','narration':'Sóng giảm.'},{'id':'two','narration':' Bùn   đâu? '}]
        self.assertEqual(lock.inspect(self.root,self.doc)['status'],'matched')
        self.source.write_text(self.source.read_text(encoding='utf-8').replace('Do not read.','Changed production note.'),encoding='utf-8')
        self.assertEqual(lock.inspect(self.root,self.doc)['status'],'matched')

    def test_source_edit_or_punctuation_change_blocks_production(self):
        self.record()
        changed=copy.deepcopy(self.doc); changed['beats'][0]['narration']='Sóng giảm! Bùn đâu?'
        self.assertEqual(lock.inspect(self.root,changed)['status'],'blocked')
        self.source.write_text('## Lời dẫn\nSóng tăng.\n',encoding='utf-8')
        self.assertEqual(lock.inspect(self.root)['status'],'blocked')

    def test_wrong_episode_or_effective_language_cannot_reuse_approval(self):
        self.record()
        for change in ({'episode_slug':'two'}, {'channel_id':'other'}, {'voice':{'language':'en'}}):
            doc={**self.doc,**change}
            self.assertEqual(lock.inspect(self.root,doc)['status'],'blocked')

    def test_approval_can_precede_beats_but_empty_beats_cannot_produce_audio(self):
        self.doc['beats']=[]; self.save()
        self.record()
        self.assertEqual(lock.inspect(self.root)['status'],'blocked')
        self.doc['beats']=[{'id':'B01','narration':'Sóng giảm. Bùn đâu?'}]; self.save()
        self.assertEqual(lock.inspect(self.root)['status'],'matched')

    def test_mixed_document_and_mismatched_speech_cannot_be_recorded(self):
        with self.assertRaises(ValueError):
            lock.record(self.root,self.source,'User said yes')
        self.doc['beats'][0]['narration']='Different'; self.save()
        with self.assertRaises(ValueError):
            self.record()

    def test_tts_and_assembly_stop_before_expensive_work_when_approval_missing(self):
        import omnivoice_tts, vieneu_tts, assemble
        for module in (omnivoice_tts,vieneu_tts):
            with patch.object(module,'load_model') as model, self.assertRaises(SystemExit):
                module.run(str(self.root))
            model.assert_not_called()
        self.doc['pipeline']='local'; self.save()
        with patch.object(assemble,'probe_dur') as probe, self.assertRaises(SystemExit):
            assemble.run(str(self.root))
        probe.assert_not_called()

    def test_receipt_detects_changed_text_and_audio_content_even_with_same_mtime(self):
        audio_dir=self.root/'audio'; audio_dir.mkdir()
        path=audio_dir/'narr_B01.wav'; wav(path)
        self.doc['beats'][0]['narration_audio']=str(path)
        save_audio_cache(str(audio_dir),'B01','fp',str(path),text=self.doc['beats'][0]['narration'])
        self.assertFalse(lock.inspect_audio(self.root,self.doc)['errors'])
        other=copy.deepcopy(self.doc); other['beats'][0]['narration']='Changed.'
        self.assertTrue(lock.inspect_audio(self.root,other)['errors'])
        import os
        stat=path.stat(); data=path.read_bytes(); path.write_bytes(data[:-2]+b'\x02\x00')
        os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
        self.assertTrue(lock.inspect_audio(self.root,self.doc)['errors'])
        self.assertIsNone(existing_audio(str(audio_dir),'B01','fp'))


class ListeningTests(unittest.TestCase):
    def test_join_preserves_all_pcm_frames_and_inserts_no_silence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); a=root/'a.wav'; b=root/'b.wav'; out=root/'out.wav'
            first=b'\x01\x00'*800; second=b'\x02\x00'*1600
            wav(a,first); wav(b,second)
            offsets=concatenate_wavs([a,b],out)
            with wave.open(str(out),'rb') as audio:
                self.assertEqual(audio.readframes(9999),first+second)
            self.assertAlmostEqual(offsets[1]['start'],0.1)
            self.assertAlmostEqual(offsets[-1]['end'],0.3)
            with self.assertRaises(ValueError): concatenate_wavs([a],a)
            wav(b,rate=16000)
            with self.assertRaises(ValueError): concatenate_wavs([a,b],out)

    def test_queue_uses_final_video_times_and_preserves_estimate_status(self):
        timeline={'qa':{'estimated_beats':['B02']},'policy':{'target_cps':17,'max_cps':20},
                  'beats':[{'beat_id':'B02','reason':'alignment disabled'}],
                  'cues':[{'beat_id':'B02','text':'One','start':52.0,'end':54.0,'cps':18.0}]}
        queue=caption_queue(timeline)
        self.assertEqual(queue[0]['start'],52)
        self.assertEqual({r['kind'] for r in queue},{'estimated_alignment','reading_speed'})
        self.assertEqual(timeline['qa']['estimated_beats'],['B02'])

    def test_review_copy_does_not_modify_production_or_accept_qa(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); project=root/'episode'; project.mkdir(); audio=project/'a.wav'; wav(audio)
            doc={'channel_id':'test','language':'en','beats':[{'id':'B01','narration':'One.','narration_audio':str(audio)}]}
            beats=project/'beats.json'; beats.write_text(json.dumps(doc),encoding='utf-8')
            before=beats.read_bytes(),audio.read_bytes()
            result=build(project,root/'review',with_audio=True)
            self.assertEqual(result['listening_review_status'],'pending')
            self.assertEqual(result['approval']['status'],'legacy_unrecorded')
            self.assertEqual(before,(beats.read_bytes(),audio.read_bytes()))
            self.assertTrue((root/'review'/'review.html').is_file())

    def test_alignment_copy_replaces_disabled_device_and_preserves_original(self):
        import stage_caption_alignment as staging
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); project=root/'episode'; project.mkdir()
            audio=project/'a.wav'; wav(audio)
            doc={'channel_id':'test','language':'en',
                 'caption_alignment':{'enabled':False,'device':'none'},
                 'beats':[{'id':'B01','narration':'One.','narration_audio':'a.wav'}]}
            path=project/'beats.json'; path.write_text(json.dumps(doc),encoding='utf-8')
            qa={'status':'needs_review','errors':[],'warnings':['estimated'],'estimated_beats':['B01']}
            (project/'captions-qa.json').write_text(json.dumps(qa),encoding='utf-8')
            before=path.read_bytes(),audio.read_bytes()
            out=root/'alignment-copy'
            with patch.object(staging,'build',return_value={'qa':qa}), \
                 patch.object(staging,'write_timeline_srt'),patch.object(staging,'write_static_ass'):
                result=staging.stage(project,out)
            staged=json.loads((out/'beats.json').read_text(encoding='utf-8'))
            self.assertTrue(staged['caption_alignment']['enabled'])
            self.assertEqual(staged['caption_alignment']['device'],'auto')
            self.assertEqual(staged['beats'][0]['narration_audio'],str(audio))
            self.assertTrue(result['production_video_still_has_old_burned_captions'])
            self.assertEqual(before,(path.read_bytes(),audio.read_bytes()))
            with self.assertRaises(ValueError): staging.stage(project,out)


if __name__=='__main__': unittest.main()
