"""One accepted phrase timeline for SRT, static ASS and caption QA."""
import gc
import importlib.metadata
import json
import math
import os
import re

from cache_keys import file_fingerprint, stable_hash
from caption_policy import (CaptionLayoutError, character_count, measured_font,
                            normalized_text, resolve_policy, split_phrases, wrap_lines)
import export_srt as alignment

REVISION = 1


def union_intervals(intervals):
    result = []
    for start, end in sorted(intervals):
        if end <= start:
            continue
        if result and start <= result[-1][1]:
            result[-1][1] = max(end, result[-1][1])
        else:
            result.append([start, end])
    return result


def temporal_metrics(intervals, regions, duration, tolerance=0.15):
    bounds = [(float(item[1]), float(item[2])) for item in intervals]
    padded = union_intervals([(max(0, a-tolerance), min(duration, b+tolerance)) for a, b in bounds])
    raw = union_intervals(bounds)
    total = sum(b-a for a, b in regions)
    covered = 0.0
    gaps = []
    for a, b in regions:
        covered += sum(max(0, min(b, d)-max(a, c)) for c, d in padded)
        cursor = a
        for c, d in raw:
            if d <= a or c >= b:
                continue
            if c > cursor:
                gaps.append(min(b, c)-cursor)
            cursor = max(cursor, min(b, d))
        if cursor < b:
            gaps.append(b-cursor)
    return {'speech_seconds': round(total, 3),
            'speech_coverage': round(covered / total, 4) if total else 0,
            'maximum_uncovered_speech_seconds': round(max(gaps, default=0), 3)}


def estimate_intervals(units, regions, duration, segments=(), language='en'):
    """Reported estimate distributed over speech, with optional TTS sentence anchors."""
    joiner = '' if language == 'ja' else ' '
    if segments:
        result, cursor = [], 0
        for segment in segments:
            grouped = []
            while cursor < len(units):
                grouped.append(units[cursor])
                cursor += 1
                if normalized_text(joiner.join(grouped), language) == normalized_text(segment['text'], language):
                    break
            else:
                return estimate_intervals(units, regions, duration, (), language)
            local = [(max(a, segment['start']), min(b, segment['end'])) for a, b in regions
                     if min(b, segment['end']) > max(a, segment['start'])]
            if not local:
                local = [(segment['start'], segment['end'])]
            result.extend(estimate_intervals(grouped, local, duration, (), language))
        if cursor == len(units):
            return result
    if not regions:
        return []
    weights = [max(1, len(re.sub(r'\W', '', unit))) for unit in units]
    total_weight = sum(weights)
    speech_length = sum(b-a for a, b in regions)

    def at(offset, end=False):
        for i, (a, b) in enumerate(regions):
            length = b-a
            if offset < length - 1e-8 or (end and offset <= length + 1e-8) or i == len(regions)-1:
                return min(b, a+offset)
            offset -= length
        return regions[-1][1]

    result, accumulated = [], 0
    for unit, weight in zip(units, weights):
        start = at(speech_length * accumulated / total_weight)
        accumulated += weight
        end = at(speech_length * accumulated / total_weight, True)
        result.append([unit, start, end])
    return result


def prepare_intervals(intervals, duration, policy, terms=()):
    """Merge only short fragments of the same sentence, then add bounded reading holds."""
    cues = [[str(text), float(start), float(end)] for text, start, end in intervals]
    index = 0
    while index < len(cues)-1:
        text, start, end = cues[index]
        following, next_start, next_end = cues[index+1]
        short = end-start < policy['min_duration_seconds'] or next_end-next_start < policy['min_duration_seconds']
        same_sentence = not re.search(r'[.!?。！？]["\'”’」』)]*$', text)
        combined = text + ('' if policy['language'] == 'ja' else ' ') + following
        if short and same_sentence and next_start-end <= 0.2 and next_end-start <= policy['max_duration_seconds']:
            try:
                wrap_lines(combined, policy, terms)
            except CaptionLayoutError:
                pass
            else:
                cues[index:index+2] = [[combined, start, next_end]]
                continue
        index += 1
    result = []
    gap = policy['minimum_gap_frames'] / policy['fps']
    for i, (text, start, spoken_end) in enumerate(cues):
        next_start = cues[i+1][1] if i+1 < len(cues) else duration
        requested_end = max(spoken_end + policy['linger_seconds'],
                            start + policy['min_duration_seconds'],
                            start + character_count(text, policy) / policy['target_cps'])
        end = min(requested_end, spoken_end + policy['max_hold_after_speech_seconds'],
                  next_start-gap if i+1 < len(cues) else duration)
        # Never move a cue's start before its aligned speech to fix reading speed.
        result.append({'text': text, 'start': start, 'end': max(start, end),
                       'speech_start': start, 'speech_end': spoken_end,
                       'lines': wrap_lines(text, policy, terms)})
    return result


def assess_cues(cues, policy):
    errors, warnings = [], []
    previous_end = -1
    for index, cue in enumerate(cues, 1):
        label = f'cue {index}'
        start, end = cue['start'], cue['end']
        if not math.isfinite(start+end) or start < 0 or end <= start:
            errors.append(f'{label}: invalid interval')
            continue
        if start < previous_end-0.001:
            errors.append(f'{label}: overlap')
        previous_end = end
        if len(cue['lines']) > policy['max_lines']:
            errors.append(f'{label}: too many lines')
        for line in cue['lines']:
            from caption_policy import fits_line
            if not fits_line(line, policy):
                errors.append(f'{label}: line exceeds character/pixel width')
        length = end-start
        cps = character_count(cue['text'], policy) / length
        cue['cps'] = round(cps, 2)
        if length < policy['min_duration_seconds']-0.011:
            warnings.append(f'{label}: short duration {length:.2f}s')
        if length > policy['max_duration_seconds']+0.011:
            errors.append(f'{label}: duration exceeds {policy["max_duration_seconds"]}s')
        if cps > policy['max_cps']+0.01:
            warnings.append(f'{label}: {cps:.1f} CPS exceeds {policy["max_cps"]}')
        elif cps > policy['target_cps']+0.01:
            warnings.append(f'{label}: {cps:.1f} CPS above comfort target {policy["target_cps"]}')
        if end-cue.get('speech_end', end) > policy['max_hold_after_speech_seconds']+0.011:
            errors.append(f'{label}: caption hangs too long after speech')
    return errors, warnings


def assert_quality(timeline):
    qa = timeline['qa']
    if qa['errors'] and timeline['policy']['quality'].get('fail_on_errors', True):
        raise SystemExit('Caption QA failed; see captions-qa.json: ' + '; '.join(qa['errors'][:4]))
    if qa['status'] == 'needs_review':
        print(f'[captions] QA needs review: {len(qa["warnings"])} warning(s); see captions-qa.json')


def write_reports(project_dir, timeline):
    # Accepted-cache contents are checked as well as input fingerprints. Manual
    # review edits belong in caption_units/protected_terms, not an unchecked cache.
    payload = {key: value for key, value in timeline.items() if key != 'content_hash'}
    timeline['content_hash'] = stable_hash(payload)
    documents = {'captions-timeline.json': timeline, 'captions-qa.json': timeline['qa'],
                 'captions-alignment.json': {'backend': 'shared caption timeline',
                    'language': timeline['language'], 'beats': timeline['beats']}}
    for name, data in documents.items():
        path = os.path.join(project_dir, name)
        with open(path+'.tmp', 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(path+'.tmp', path)


def build(project_dir, beat_spans=None, width=None, height=None, force=False):
    with open(os.path.join(project_dir, 'beats.json'), encoding='utf-8-sig') as handle:
        doc = json.load(handle)
    from narration_lock import assert_approved, assert_audio
    assert_approved(project_dir, doc)
    assert_audio(project_dir, doc)
    language = alignment.language_code(doc)
    dimensions = {'16:9': (1920, 1080), '9:16': (1080, 1920), '1:1': (1080, 1080)}
    default_width, default_height = dimensions.get(doc.get('aspect', '16:9'), (1920, 1080))
    width = width or (doc.get('format') or {}).get('width') or default_width
    height = height or (doc.get('format') or {}).get('height') or default_height
    policy = resolve_policy(doc, language, width, height)
    spans = beat_spans if beat_spans is not None else alignment.beat_spans(doc, project_dir)
    settings = alignment.alignment_settings(doc)
    try:
        installed_version = importlib.metadata.version('whisperx')
    except importlib.metadata.PackageNotFoundError:
        installed_version = 'unavailable'
    fingerprint_beats = []
    for span in spans:
        beat = span['beat']
        audio = beat.get('narration_audio') or ''
        audio = audio if os.path.isabs(audio) else os.path.join(project_dir, audio)
        span['_audio'] = audio
        fingerprint_beats.append({'start': span['start'], 'audio_dur': span.get('audio_dur'),
            'beat': {key: beat.get(key) for key in ('id', 'narration', 'caption_units', 'caption_protected_terms')},
            'audio': file_fingerprint(audio),
            'sentences': file_fingerprint(os.path.splitext(audio)[0]+'.sentences.json', True)})
    fingerprint = stable_hash({'revision': REVISION, 'policy': policy, 'alignment': settings,
                               'font_file': file_fingerprint(policy.get('font_file')),
                               'whisperx_version': installed_version, 'beats': fingerprint_beats,
                               'protected_terms': doc.get('caption_protected_terms') or []})
    cache_path = os.path.join(project_dir, 'captions-timeline.json')
    if not force:
        try:
            with open(cache_path, encoding='utf-8-sig') as handle:
                cached = json.load(handle)
            intact = cached.get('content_hash') == stable_hash({key: value for key, value in cached.items() if key != 'content_hash'})
            if cached.get('fingerprint') == fingerprint and intact:
                # Reports can be regenerated if an external tool removed them.
                write_reports(project_dir, cached)
                assert_quality(cached)
                return cached
        except (OSError, ValueError, KeyError):
            pass
    if settings.get('enabled', True):
        available = alignment.available_physical_memory_bytes()
        minimum = float(settings.get('minimum_available_memory_gb', 3)) * 1024**3
        if available is not None and available < minimum:
            raise SystemExit('WhisperX needs at least 3 GB free RAM; close other applications and retry.')
    engine, model_error = alignment.load_alignment_model(settings, language)
    timeline = {'schema_version': REVISION, 'fingerprint': fingerprint, 'language': language,
                'policy': policy, 'cues': [], 'beats': [],
                'qa': {'status': 'pass', 'errors': [], 'warnings': [], 'estimated_beats': []}}
    if measured_font(policy.get('font_file'), policy['font_size']) is None:
        timeline['qa']['warnings'].append('Font metrics unavailable; pixel fit needs visual review.')
    try:
        for span in spans:
            beat, audio = span['beat'], span['_audio']
            text = (beat.get('narration') or '').strip()
            if not text:
                continue
            beat_id = str(beat.get('id', 'beat'))
            if not os.path.isfile(audio):
                timeline['qa']['errors'].append(f'{beat_id}: narration WAV missing')
                continue
            duration = float(span.get('audio_dur') or alignment.probe_dur(audio))
            terms = [*(doc.get('caption_protected_terms') or []), *(beat.get('caption_protected_terms') or [])]
            try:
                units = split_phrases(text, policy, terms)
            except CaptionLayoutError as exc:
                timeline['qa']['errors'].append(f'{beat_id}: {exc}')
                continue
            custom = beat.get('caption_units')
            if custom:
                joiner = '' if language == 'ja' else ' '
                if not isinstance(custom, list) or not all(isinstance(u, str) for u in custom) or normalized_text(joiner.join(custom), language) != normalized_text(text, language):
                    timeline['qa']['errors'].append(f'{beat_id}: reviewed caption_units differ from approved narration')
                    continue
                # Refine oversized reviewed units without rewriting their contents.
                try:
                    units = [phrase for unit in custom for phrase in split_phrases(unit, policy, terms)]
                except CaptionLayoutError as exc:
                    timeline['qa']['errors'].append(f'{beat_id}: {exc}')
                    continue
            regions = alignment.detect_speech_regions(audio, duration)
            if not regions:
                timeline['qa']['errors'].append(f'{beat_id}: no measured speech in narration WAV')
                continue
            intervals, metrics, cached = None, {}, False
            method, reason = 'speech-envelope estimate', model_error
            if engine:
                try:
                    words, cached = alignment.align_transcript(engine, audio, project_dir, beat_id, language, text)
                    intervals, metrics = alignment.align_units_to_words(units, words, language, settings.get('min_exact_match_ratio', 0.95))
                    if intervals:
                        ok, timing = alignment.validate_alignment_timing(intervals, audio, duration, regions, policy['quality'])
                        metrics.update(timing)
                        if ok:
                            calibrated = any(word.get('sentence_anchor_calibrated') for word in words)
                            qualifier = ' (sentence-anchor calibrated)' if calibrated else ''
                            method = ('WhisperX forced alignment (cache)' if cached else 'WhisperX forced alignment') + qualifier
                        else:
                            intervals, reason = None, timing.get('timing_reason')
                    else:
                        reason = metrics.get('reason')
                except Exception as exc:
                    reason = str(exc)
            if intervals is None:
                segments = alignment.sentence_segments(audio, text, language)
                intervals = estimate_intervals(units, regions, duration, segments, language)
                timeline['qa']['estimated_beats'].append(beat_id)
                if policy['quality'].get('fallback_requires_review', True):
                    timeline['qa']['warnings'].append(f'{beat_id}: estimated timing requires listening review ({reason})')
            # Long cues are resegmented and aligned again, never truncated to seven seconds.
            if any(end-start > policy['max_duration_seconds'] for _, start, end in intervals):
                smaller = {**policy, 'target_phrase_characters': max(8, policy['target_phrase_characters']/2)}
                smaller_units = [part for unit in units for part in split_phrases(unit, smaller, terms)]
                if method.startswith('WhisperX'):
                    refined, _ = alignment.align_units_to_words(smaller_units, words, language, settings.get('min_exact_match_ratio', 0.95))
                    if refined:
                        intervals = refined
                else:
                    intervals = estimate_intervals(smaller_units, regions, duration, alignment.sentence_segments(audio, text, language), language)
            try:
                cues = prepare_intervals(intervals, duration, policy, terms)
            except CaptionLayoutError as exc:
                timeline['qa']['errors'].append(f'{beat_id}: {exc}')
                continue
            errors, warnings = assess_cues(cues, policy)
            coverage = temporal_metrics([(c['text'], c['start'], c['end']) for c in cues], regions, duration,
                                        policy['quality']['speech_edge_tolerance_seconds'])
            if coverage['speech_coverage'] < policy['quality']['minimum_speech_coverage'] or coverage['maximum_uncovered_speech_seconds'] > policy['quality']['maximum_uncovered_speech_seconds']:
                errors.append('captions do not cover measured speech')
            joiner = '' if language == 'ja' else ' '
            if normalized_text(joiner.join(c['text'] for c in cues), language) != normalized_text(text, language):
                errors.append('caption content differs from approved narration')
            timeline['qa']['errors'].extend(f'{beat_id}: {e}' for e in errors)
            timeline['qa']['warnings'].extend(f'{beat_id}: {w}' for w in warnings)
            for cue in cues:
                cue['beat_id'] = beat_id
                for key in ('start', 'end', 'speech_start', 'speech_end'):
                    cue[key] = round(cue[key] + float(span['start']), 2)
                timeline['cues'].append(cue)
            timeline['beats'].append({'beat_id': beat_id, 'method': method, 'cached': cached,
                                     'reason': reason if not method.startswith('WhisperX') else None,
                                     **metrics, 'final_timing': coverage})
    finally:
        if engine:
            device = engine['device']
            alignment._ALIGNMENT_ENGINES.clear()
            del engine
            gc.collect()
            if device == 'cuda':
                try:
                    import torch
                    torch.cuda.empty_cache()
                except ImportError:
                    pass
    timeline['cues'].sort(key=lambda cue: (cue['start'], cue['end']))
    for left, right in zip(timeline['cues'], timeline['cues'][1:]):
        if left['end'] > right['start'] + 0.001:
            timeline['qa']['errors'].append('caption overlap across beat boundaries')
    timeline['qa']['status'] = 'fail' if timeline['qa']['errors'] else 'needs_review' if timeline['qa']['warnings'] else 'pass'
    timeline['qa']['cue_count'] = len(timeline['cues'])
    timeline['qa']['fingerprint'] = fingerprint
    write_reports(project_dir, timeline)
    assert_quality(timeline)
    return timeline
