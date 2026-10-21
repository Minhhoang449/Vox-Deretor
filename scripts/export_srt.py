#!/usr/bin/env python3
"""
Write phrase-level final.srt beside the episode, timed to the assembled film.

Same idea as Vox-AI render.py: split each beat's canonical narration into
readable phrases, then align those cues to word timestamps from the beat's
WAV when available. Speech-envelope timing is retained as a fallback. Cue times are offset to the beat's start
on the final timeline, using the same shot-duration math as assemble.py.

Usage: python export_srt.py <episode_dir>
"""
import difflib
import ctypes
import gc
import hashlib
import json
import os
import re
import subprocess
import sys
import textwrap
import unicodedata

from local_guard import configure_console, refuse_out_dir
from cache_keys import file_fingerprint

TAIL = 0.5
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ALIGNMENT_ENGINES = {}


def available_physical_memory_bytes():
    """Return available Windows RAM without loading the alignment runtime."""
    if os.name != "nt":
        return None

    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return int(status.ullAvailPhys)
    return None


def srt_timestamp(seconds):
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, ms = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{ms:03}"


def split_caption_units(text, max_words=8, max_chars=64, language='en'):
    """Compatibility entry point; semantic boundaries replace the old word-count cut."""
    from caption_policy import resolve_policy, split_phrases
    policy = resolve_policy({}, language)
    policy['target_phrase_characters'] = max_chars
    return split_phrases(text, policy)


def caption_units_for_beat(beat, text, language='en'):
    """Use reviewed phrase boundaries when they reproduce the approved narration exactly."""
    custom = beat.get("caption_units")
    if isinstance(custom, list) and custom and all(isinstance(item, str) for item in custom):
        units = [item.strip() for item in custom if item.strip()]
        from caption_policy import normalized_text
        joiner = '' if language == 'ja' else ' '
        if normalized_text(joiner.join(units), language) == normalized_text(text, language):
            return units
        print(f"[captions] {beat.get('id', '?')}: custom units differ from narration; using automatic split")
    return split_caption_units(text, language=language)


def _split_unspaced(text, max_chars):
    """Japanese and other scripts that are not split on spaces."""
    chunks, buf = [], ""
    for char in text.strip():
        buf += char
        if char in "。！？、，" or len(buf) >= max_chars:
            chunks.append(buf.strip())
            buf = ""
    if buf.strip():
        chunks.append(buf.strip())
    return [chunk for chunk in chunks if chunk]


def probe_dur(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def detect_speech_regions(audio, duration):
    """Measure every active speech region, excluding inserted/internal silence."""
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", audio, "-af", "silencedetect=noise=-50dB:d=0.12",
         "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = result.stderr or ""
    if result.returncode:
        raise RuntimeError(f'Could not measure speech timing: {audio}')
    starts = [float(value) for value in re.findall(r"silence_start:\s*([0-9.]+)", log)]
    ends = [float(value) for value in re.findall(r"silence_end:\s*([0-9.]+)", log)]
    silences = []
    end_index = 0
    for silence_start in starts:
        while end_index < len(ends) and ends[end_index] <= silence_start:
            end_index += 1
        if end_index < len(ends):
            silence_end = ends[end_index]
            end_index += 1
        else:
            silence_end = duration
        silence_start = max(0.0, min(duration, silence_start))
        silence_end = max(silence_start, min(duration, silence_end))
        silences.append((silence_start, silence_end))
    regions, cursor = [], 0.0
    for start, end in sorted(silences):
        if start > cursor + 0.02:
            regions.append((cursor, start))
        cursor = max(cursor, end)
    if duration > cursor + 0.02:
        regions.append((cursor, duration))
    return regions


def detect_speech_timing(audio, duration):
    regions = detect_speech_regions(audio, duration)
    if not regions:
        return 0.0, duration, []
    pauses = [(left[1], right[0]) for left, right in zip(regions, regions[1:])]
    return regions[0][0], regions[-1][1], pauses


def caption_intervals(units, duration, speech_start, speech_end, pauses):
    """Place phrase cues over measured speech, snapping phrase edges to pauses."""
    if not units:
        return []
    weights = [max(1, len(re.sub(r"[^\w]", "", unit, flags=re.UNICODE))) for unit in units]
    total_weight = sum(weights)
    span = max(0.0, speech_end - speech_start)
    if span <= 0.05:
        speech_start, speech_end, span = 0.0, duration, duration
    boundaries = [speech_start]
    accumulated = 0
    for weight in weights[:-1]:
        accumulated += weight
        target = speech_start + span * accumulated / total_weight
        candidates = [((a + b) / 2, b - a) for a, b in pauses]
        candidates = [(mid, gap) for mid, gap in candidates if abs(mid - target) <= min(1.0, span * 0.15)]
        if candidates:
            target = min(candidates, key=lambda item: abs(item[0] - target))[0]
        target = max(boundaries[-1] + 0.25, min(speech_end - 0.25 * (len(units) - len(boundaries)), target))
        boundaries.append(target)
    boundaries.append(speech_end)
    return [(unit, boundaries[i], boundaries[i + 1]) for i, unit in enumerate(units)]


def stabilize_caption_intervals(intervals, language="en", minimum_seconds=0.8):
    """Merge punctuation and very brief cues so captions remain readable on screen."""
    compact_scripts = str(language).lower().startswith(("ja", "zh", "th", "lo", "km"))
    cues = [[str(text).strip(), float(start), float(end)] for text, start, end in intervals if str(text).strip()]

    def join_text(left, right):
        if not left:
            return right
        if not right:
            return left
        if compact_scripts or re.match(r"^[,.;:!?，。！？、…\)\]»”’]", right):
            return left.rstrip() + right.lstrip()
        return left.rstrip() + " " + right.lstrip()

    index = 0
    while index < len(cues):
        text, start, end = cues[index]
        too_short = end - start < float(minimum_seconds)
        punctuation_only = not re.search(r"\w", text, re.UNICODE)
        if not too_short and not punctuation_only:
            index += 1
            continue

        if len(cues) == 1:
            break
        if index == 0:
            neighbor = 1
        elif index == len(cues) - 1 or punctuation_only:
            neighbor = index - 1
        else:
            previous_gap = max(0.0, start - cues[index - 1][2])
            next_gap = max(0.0, cues[index + 1][1] - end)
            neighbor = index - 1 if previous_gap <= next_gap else index + 1

        if neighbor < index:
            previous = cues[neighbor]
            cues[neighbor] = [join_text(previous[0], text), previous[1], max(previous[2], end)]
            cues.pop(index)
            index = max(0, neighbor)
        else:
            following = cues[neighbor]
            cues[index] = [join_text(text, following[0]), min(start, following[1]), max(end, following[2])]
            cues.pop(neighbor)
            index = max(0, index - 1)
    return [tuple(cue) for cue in cues]


def wrap_caption_text(text, width=42, language="en"):
    """Wrap scripts with and without word spaces into readable subtitle lines."""
    value = str(text).strip()
    if not value:
        return ""
    compact_scripts = str(language).lower().startswith(("ja", "zh", "th", "lo", "km"))
    if compact_scripts and not re.search(r"\s", value) and len(value) > width:
        return "\n".join(value[offset:offset + width] for offset in range(0, len(value), width))
    return textwrap.fill(value, width=width)


def alignment_settings(doc):
    settings = {"enabled": True, "backend": "whisperx_forced_alignment", "device": "cuda",
                "align_model": None, "min_exact_match_ratio": 0.95}
    path = os.path.join(ROOT, "config", "pipeline.json")
    try:
        with open(path, encoding="utf-8-sig") as handle:
            settings.update(json.load(handle).get("caption_alignment") or {})
    except (OSError, ValueError, TypeError):
        pass
    settings.update(doc.get("caption_alignment") or {})
    return settings


def language_code(doc):
    voice = doc.get("voice") or {}
    channel = doc.get("channel") or {}
    return str(voice.get("language") or channel.get("language") or doc.get("language") or "en").lower()


def load_alignment_model(settings, language):
    if not settings.get("enabled", True):
        return None, "disabled in caption_alignment settings"
    try:
        import torch
        import whisperx
        requested_device = str(settings.get("device") or "auto").lower()
        device = ("cuda" if torch.cuda.is_available() else "cpu") if requested_device == "auto" else requested_device
        align_model = settings.get("align_model") or None
        model_dir = settings.get("model_dir") or None
        cache_key = (language, device, align_model, model_dir)
        if cache_key in _ALIGNMENT_ENGINES:
            return _ALIGNMENT_ENGINES[cache_key], ""
        model, metadata = whisperx.load_align_model(
            language_code=language,
            device=device,
            model_name=align_model,
            model_dir=model_dir,
        )
        engine = {
            "whisperx": whisperx,
            "model": model,
            "metadata": metadata,
            "device": device,
            "model_name": align_model or f"whisperx-default:{language}",
            "version": str(getattr(whisperx, "__version__", "unknown")),
        }
        _ALIGNMENT_ENGINES[cache_key] = engine
        return engine, ""
    except Exception as exc:
        return None, f"could not load WhisperX for {language} ({exc}); using estimated phrase timing"


def _safe_cache_id(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("._") or "beat"


def align_transcript(model, audio, project_dir, beat_id, language, transcript):
    """Force-align the approved transcript to one beat WAV and cache its word times."""
    stat = os.stat(audio)
    segments = sentence_segments(audio, transcript, language)
    fingerprint = {
        "audio": os.path.abspath(audio),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "language": language,
        "model": f"{model['model_name']}@{model['version']}" if model else None,
        "transcript_sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
        "sentence_segments": segments,
    }
    cache_dir = os.path.join(project_dir, "audio")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"caption_alignment_{_safe_cache_id(beat_id)}.json")
    try:
        with open(cache_path, encoding="utf-8-sig") as handle:
            cached = json.load(handle)
        if cached.get("fingerprint") == fingerprint:
            words = cached.get("words") or []
            if segments and not any(word.get("sentence_anchor_calibrated") for word in words):
                words, calibration = calibrate_words_to_sentence_anchors(words, segments, language)
                if calibration.get("applied"):
                    cached["words"] = words
                    cached["sentence_anchor_calibration"] = calibration
                    with open(cache_path, "w", encoding="utf-8") as handle:
                        json.dump(cached, handle, ensure_ascii=False, indent=2)
            return words, True
    except (OSError, ValueError, TypeError):
        pass

    if model is None:
        raise RuntimeError("WhisperX alignment model is unavailable")
    duration = probe_dur(audio)
    if duration <= 0:
        raise RuntimeError("could not read narration WAV duration")
    aligned = model["whisperx"].align(
        segments or [{"start": 0.0, "end": duration, "text": transcript}],
        model["model"],
        model["metadata"],
        audio,
        model["device"],
        return_char_alignments=False,
        print_progress=False,
    )
    words = []
    for word in aligned.get("word_segments") or []:
        start, end = word.get("start"), word.get("end")
        text = str(word.get("word") or "").strip()
        if start is None or end is None or not text:
            continue
        words.append({"text": text, "start": float(start), "end": float(end)})
    if not words:
        raise RuntimeError("WhisperX returned no aligned word timestamps")
    calibration = None
    if segments:
        words, calibration = calibrate_words_to_sentence_anchors(words, segments, language)
    payload = {"fingerprint": fingerprint, "words": words}
    if calibration and calibration.get("applied"):
        payload["sentence_anchor_calibration"] = calibration
    with open(cache_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return words, False


def sentence_segments(audio, transcript, language):
    """Accept synthesis sentence anchors only when they match this WAV and script."""
    from caption_policy import normalized_text
    path = os.path.splitext(audio)[0] + '.sentences.json'
    try:
        with open(path, encoding='utf-8-sig') as handle:
            data = json.load(handle)
        if data.get('audio_file') != file_fingerprint(audio):
            return []
        segments = data.get('segments') or []
        joiner = '' if language == 'ja' else ' '
        if normalized_text(joiner.join(s['text'] for s in segments), language) != normalized_text(transcript, language):
            return []
        previous = 0.0
        duration = probe_dur(audio)
        for item in segments:
            start, end = float(item['start']), float(item['end'])
            import math
            if not math.isfinite(start+end) or start < previous - 0.001 or end <= start or end > duration + 0.01:
                return []
            previous = end
        return [{'start': float(s['start']), 'end': float(s['end']), 'text': s['text']} for s in segments]
    except (OSError, ValueError, TypeError, KeyError):
        return []


def _normal_token(value):
    text = unicodedata.normalize("NFKD", str(value)).casefold()
    return "".join(char for char in text if char.isalnum() and unicodedata.category(char) != "Mn")


def _caption_tokens(text, language):
    if language in {"ja", "zh", "yue"}:
        return [token for token in (_normal_token(char) for char in text) if token]
    return [token for token in (_normal_token(word) for word in text.split()) if token]


def calibrate_words_to_sentence_anchors(words, segments, language):
    """Repair uniformly compressed word times using verified TTS sentence anchors.

    The anchors are accepted only when their audio fingerprint and joined text
    match the current WAV and approved narration. Apply the repair only when all
    sentence spans show the same large compression pattern, word counts match,
    and each aligned sentence starts close to its recorded TTS start.
    """
    if not words or not segments:
        return words, {"applied": False, "reason": "verified sentence anchors are unavailable"}

    cursor = 0
    groups = []
    ratios = []
    start_offsets = []
    for segment in segments:
        expected = len(_caption_tokens(segment.get("text", ""), language))
        group = []
        token_count = 0
        while cursor < len(words) and token_count < expected:
            word = words[cursor]
            group.append(word)
            cursor += 1
            token_count += len(_caption_tokens(word.get("text", ""), language))
        if token_count != expected or not group:
            return words, {"applied": False, "reason": "sentence and aligned word counts differ"}

        aligned_start = min(float(word["start"]) for word in group)
        aligned_end = max(float(word["end"]) for word in group)
        anchor_start = float(segment["start"])
        anchor_end = float(segment["end"])
        aligned_span = aligned_end - aligned_start
        anchor_span = anchor_end - anchor_start
        if aligned_span <= 0 or anchor_span <= 0:
            return words, {"applied": False, "reason": "sentence has a nonpositive timing span"}
        ratios.append(anchor_span / aligned_span)
        start_offsets.append(abs(aligned_start - anchor_start))
        groups.append((group, anchor_start, anchor_end, aligned_start, aligned_span))

    if cursor != len(words):
        return words, {"applied": False, "reason": "aligned words remain after the final sentence"}

    # A single global clock/unit mistake produces a large, consistent scale
    # difference. Leave ordinary alignment variation to WhisperX unchanged.
    ratio_min, ratio_max = min(ratios), max(ratios)
    if (ratio_min < 1.5 or ratio_max > 5.0 or ratio_max / ratio_min > 2.0 or
            max(start_offsets) > 0.12):
        return words, {
            "applied": False,
            "reason": "sentence timing does not show a consistent compressed scale",
            "scale_min": round(ratio_min, 3),
            "scale_max": round(ratio_max, 3),
        }

    corrected = []
    for group, anchor_start, _anchor_end, aligned_start, aligned_span in groups:
        anchor_span = _anchor_end - anchor_start
        scale = anchor_span / aligned_span
        for word in group:
            item = dict(word)
            item["start"] = anchor_start + (float(word["start"]) - aligned_start) * scale
            item["end"] = anchor_start + (float(word["end"]) - aligned_start) * scale
            item["sentence_anchor_calibrated"] = True
            corrected.append(item)
    return corrected, {
        "applied": True,
        "method": "linear per-sentence scale from verified TTS anchors",
        "sentence_count": len(segments),
        "scale_min": round(ratio_min, 3),
        "scale_max": round(ratio_max, 3),
    }


def align_units_to_words(units, words, language, min_exact_match_ratio=0.95, min_event_duration=0.12):
    """Map approved caption text onto aligned tokens without changing its wording."""
    canonical = []
    for unit in units:
        tokens = _caption_tokens(unit, language)
        canonical.extend(tokens)

    spoken, spans = [], []
    char_based = language in {"ja", "zh", "yue"}
    for word in words:
        tokens = _caption_tokens(word.get("text", ""), language)
        if not tokens:
            continue
        start, end = float(word["start"]), float(word["end"])
        width = max(0.0, end - start)
        for index, token in enumerate(tokens):
            spoken.append(token)
            if char_based:
                spans.append((start + width * index / len(tokens), start + width * (index + 1) / len(tokens)))
            else:
                spans.append((start, end))

    if not canonical or not spoken:
        return None, {"exact_match_ratio": 0.0, "coverage": 0.0, "reason": "no alignable words"}

    mapped = {}
    exact_matches = 0
    matcher = difflib.SequenceMatcher(a=canonical, b=spoken, autojunk=False)
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(a1 - a0):
                mapped[a0 + offset] = spans[b0 + offset]
            exact_matches += a1 - a0
        elif tag == "replace" and b1 > b0:
            # Preserve the script text, but use nearby aligned spans if model
            # tokenization differs around punctuation, digits, or names.
            target_count, source_count = a1 - a0, b1 - b0
            for offset in range(target_count):
                source_offset = min(source_count - 1, int((offset + 0.5) * source_count / target_count))
                mapped[a0 + offset] = spans[b0 + source_offset]

    exact_ratio = exact_matches / len(canonical)
    coverage = len(mapped) / len(canonical)
    metrics = {
        "exact_match_ratio": round(exact_ratio, 3),
        "coverage": round(coverage, 3),
        "canonical_tokens": len(canonical),
        "aligned_tokens": len(spoken),
    }
    if exact_ratio < float(min_exact_match_ratio) or coverage < 0.75:
        metrics["reason"] = "aligned tokens differ too much from the approved narration"
        return None, metrics

    intervals = []
    token_index = 0
    for unit in units:
        unit_tokens = _caption_tokens(unit, language)
        unit_spans = [mapped[i] for i in range(token_index, token_index + len(unit_tokens)) if i in mapped]
        token_index += len(unit_tokens)
        if not unit_spans:
            metrics["reason"] = "a caption phrase has no matched word timestamps"
            return None, metrics
        intervals.append([unit, min(span[0] for span in unit_spans), max(span[1] for span in unit_spans)])

    # Whisper word boundaries can overlap slightly. Split overlaps at their midpoint
    # so subtitle cues remain ordered and do not cover one another.
    for index in range(len(intervals) - 1):
        if intervals[index][2] > intervals[index + 1][1]:
            midpoint = (intervals[index][2] + intervals[index + 1][1]) / 2
            intervals[index][2] = midpoint
            intervals[index + 1][1] = midpoint
    if any(end - start < float(min_event_duration) for _, start, end in intervals):
        metrics["reason"] = "word alignment produced a near-zero caption interval"
        return None, metrics
    return intervals, metrics


def validate_alignment_timing(intervals, audio, duration, regions=None, quality=None):
    """Reject textually valid alignments whose timestamps cover only part of the speech."""
    if not intervals:
        return False, {"timing_coverage": 0.0, "timing_reason": "no aligned intervals"}

    starts = [float(item[1]) for item in intervals]
    ends = [float(item[2]) for item in intervals]
    aligned_start, aligned_end = min(starts), max(ends)
    aligned_span = max(0.0, aligned_end - aligned_start)
    duration = max(0.01, float(duration))
    duration_coverage = aligned_span / duration
    metrics = {
        "aligned_span_seconds": round(aligned_span, 2),
        "audio_duration_seconds": round(duration, 2),
        "timing_coverage": round(duration_coverage, 3),
    }

    from caption_timeline import temporal_metrics
    if quality is None:
        with open(os.path.join(ROOT, 'config', 'pipeline.json'), encoding='utf-8-sig') as handle:
            quality = json.load(handle).get('caption_quality') or {}
    regions = detect_speech_regions(audio, duration) if regions is None else regions
    timing = temporal_metrics(intervals, regions, duration, quality.get('speech_edge_tolerance_seconds', 0.15))
    metrics.update(timing)
    plausible = (timing['speech_seconds'] > 0.05 and
                 timing['speech_coverage'] >= quality.get('minimum_speech_coverage', 0.95) and
                 timing['maximum_uncovered_speech_seconds'] <= quality.get('maximum_uncovered_speech_seconds', 0.4))
    if not plausible:
        metrics["timing_reason"] = "aligned timestamps do not cover the measured speech"
    return plausible, metrics


def shots_of(beat):
    if beat.get("shots"):
        return list(beat["shots"])
    return [beat]


def beat_spans(doc, project_dir):
    """Match assemble.py: narration is delayed to each beat's visual start."""
    spans = []
    t = 0.0
    for beat in doc["beats"]:
        start = t
        shot_list = shots_of(beat)
        durs = [float(s.get("dur", 10)) for s in shot_list]
        audio = beat.get("narration_audio")
        if audio and not os.path.isabs(audio):
            audio = os.path.abspath(os.path.join(project_dir, audio))
            beat["narration_audio"] = audio
        narr = float(beat.get("narration_dur") or 0)
        if audio and os.path.exists(audio):
            measured = probe_dur(audio)
            if measured > 0:
                narr = measured
        need = (narr or sum(durs)) + TAIL
        if shot_list and sum(durs) < need and shot_list[-1].get("kind") != "host":
            durs[-1] += need - sum(durs)
        t += sum(durs) if durs else need
        spans.append({"start": start, "beat": beat, "audio_dur": narr})
    return spans


def write_timeline_srt(project_dir, timeline):
    """Serialize the already accepted text and millisecond times without rewrapping."""
    from caption_timeline import assert_quality
    assert_quality(timeline)
    blocks = []
    for index, cue in enumerate(timeline['cues'], 1):
        blocks.append(str(index) + "\n" + srt_timestamp(cue['start']) + " --> " +
                      srt_timestamp(cue['end']) + "\n" + "\n".join(cue['lines']))
    dest = os.path.join(project_dir, 'final.srt')
    with open(dest, 'w', encoding='utf-8') as handle:
        handle.write("\n\n".join(blocks) + ("\n" if blocks else ''))
    print(f"SRT: {dest} ({len(blocks)} shared phrase cues)")
    return dest


def run(project_dir, beat_spans=None, width=None, height=None, force=False, timeline=None):
    configure_console()
    refuse_out_dir(project_dir)
    if timeline is None:
        from caption_timeline import build
        timeline = build(project_dir, beat_spans, width, height, force)
    return write_timeline_srt(project_dir, timeline)


if __name__ == "__main__":
    configure_console()
    if len(sys.argv) < 2:
        raise SystemExit("usage: python export_srt.py <episode_dir>")
    run(os.path.abspath(sys.argv[1]), force='--redo' in sys.argv[2:])
