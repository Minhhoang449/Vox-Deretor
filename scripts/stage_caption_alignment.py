"""Realign captions in a separate review copy, preserving production WAV/video.

This explicitly enables WhisperX in the copy. It does not change the source
episode's alignment override, SRT/ASS, QA acceptance or burned-in captions.
"""
import argparse
import json
from pathlib import Path
import shutil

from caption_timeline import build
from export_srt import write_timeline_srt
from export_ass import write_static_ass
from narration_lock import FILENAME, assert_approved, assert_audio, load_doc


def stage(project_dir, output_dir):
    source, output = Path(project_dir).resolve(), Path(output_dir).resolve()
    if output == source or output in source.parents:
        raise ValueError("Use a separate review directory, not the production root or its parent.")
    if (output/'beats.json').exists():
        raise ValueError("Review copy already exists; choose a fresh output directory.")
    doc = load_doc(source)
    assert_approved(source, doc)
    assert_audio(source, doc)
    for beat in doc['beats']:
        audio = Path(beat.get('narration_audio') or '')
        if not audio.is_absolute():
            audio = source/audio
        beat['narration_audio'] = str(audio)
    # Disabled legacy episodes may explicitly store device='none'; enabling the
    # backend must also select a usable device instead of preserving that value.
    doc['caption_alignment'] = {**(doc.get('caption_alignment') or {}),
                                'enabled': True, 'device': 'auto'}
    output.mkdir(parents=True, exist_ok=True)
    # Receipts remain local lookups, while audio paths still reference untouched WAVs.
    (output/'audio').mkdir(exist_ok=True)
    for beat in doc['beats']:
        cache = source/'audio'/f"narr_{beat['id']}.cache.json"
        if cache.is_file():
            shutil.copyfile(cache, output/'audio'/cache.name)
    if (source/FILENAME).is_file():
        shutil.copyfile(source/FILENAME, output/FILENAME)
    (output/'beats.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    timeline = build(str(output), force=True)
    write_timeline_srt(str(output), timeline)
    write_static_ass(str(output), timeline)
    summary = {'source_episode': str(source), 'source_changed': False,
               'old_qa': json.loads((source/'captions-qa.json').read_text(encoding='utf-8-sig')),
               'new_qa': timeline['qa'], 'production_video_still_has_old_burned_captions': True}
    (output/'comparison.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return summary


if __name__ == '__main__':
    from local_guard import configure_console
    configure_console()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project_dir'); parser.add_argument('--output-dir',required=True)
    args=parser.parse_args()
    result=stage(args.project_dir,args.output_dir)
    print(json.dumps({'old_estimated_beats':result['old_qa'].get('estimated_beats'),
                      'new_estimated_beats':result['new_qa'].get('estimated_beats'),
                      'new_status':result['new_qa']['status']},ensure_ascii=False))
