#!/usr/bin/env python3
"""Build static phrase captions by default, with optional progressive word reveal."""
import json
import os
import re
import sys

from local_guard import configure_console, refuse_out_dir
from export_srt import (
    alignment_settings,
    beat_spans as calculate_beat_spans,
    caption_intervals,
    caption_units_for_beat,
    detect_speech_timing,
    language_code,
    load_alignment_model,
    stabilize_caption_intervals,
    probe_dur,
    align_transcript,
    align_units_to_words,
    validate_alignment_timing,
)


def ass_time(seconds):
    centiseconds = max(0, round(float(seconds) * 100))
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, cs = divmod(remainder, 100)
    return f"{hours}:{minutes:02}:{whole_seconds:02}.{cs:02}"


def _escape_ass(text):
    return str(text).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _wrapped_prefix(tokens, visible_count, max_chars, active_index, pop_scale, pop_ms):
    lines = [[]]
    for index, token in enumerate(tokens[:visible_count]):
        current = lines[-1]
        if current and len(" ".join([*current, token])) > max_chars:
            lines.append([])
        escaped = _escape_ass(token)
        if index == active_index:
            escaped = (
                rf"{{\fscx{pop_scale}\fscy{pop_scale}\c&H0057C8FF&"
                rf"\t(0,{pop_ms},\fscx100\fscy100)}}" + escaped + r"{\rDefault}"
            )
        lines[-1].append(escaped)
    return r"\N".join(" ".join(line) for line in lines)


def _spread_phrase_words(phrases, phrase_intervals):
    """Fallback only: distribute each phrase duration across its spoken tokens."""
    result = []
    for phrase, start, end in phrase_intervals:
        tokens = phrase.split()
        if not tokens:
            continue
        weights = [max(1, len(re.sub(r"[^\w]", "", word, flags=re.UNICODE))) for word in tokens]
        total = sum(weights)
        cursor = float(start)
        for index, (word, weight) in enumerate(zip(tokens, weights)):
            next_cursor = float(end) if index == len(tokens) - 1 else cursor + (end - start) * weight / total
            result.append([word, cursor, next_cursor])
            cursor = next_cursor
    return result


def _wrap_static_phrase(text, max_chars):
    """Wrap one stable, fully visible phrase without word-reveal effects."""
    value = str(text).strip()
    if not value:
        return ""
    if not re.search(r"\s", value):
        if len(value) > max_chars:
            return r"\N".join(_escape_ass(value[offset:offset + max_chars])
                               for offset in range(0, len(value), max_chars))
        return _escape_ass(value)
    words = value.split()
    if not words:
        return ""
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if current and len(candidate) > max_chars:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return r"\N".join(_escape_ass(line) for line in lines)


def _read_or_align_words(engine, audio, project_dir, beat_id, language, narration):
    if engine is None:
        return [], "unavailable"
    try:
        words, cached = align_transcript(engine, audio, project_dir, beat_id, language, narration)
        return words, "cache" if cached else "WhisperX"
    except Exception as exc:
        return [], f"WhisperX alignment failed: {exc}"


def write_static_ass(project_dir, timeline):
    from caption_timeline import assert_quality
    from export_srt import write_timeline_srt
    assert_quality(timeline)
    write_timeline_srt(project_dir, timeline)
    cfg = timeline['policy']
    alignment = 8 if cfg['position'] == 'top' else 2
    header = [
        '[Script Info]', 'ScriptType: v4.00+',
        f"PlayResX: {cfg['width']}", f"PlayResY: {cfg['height']}",
        'WrapStyle: 2', 'ScaledBorderAndShadow: yes', 'YCbCr Matrix: TV.709', '',
        '[V4+ Styles]',
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
        f"Style: Default,{cfg['font']},{cfg['font_size']},{cfg['primary_color']},&H000000FF,{cfg['outline_color']},&H80000000,0,0,0,0,100,100,0,0,1,{cfg['outline']},{cfg['shadow']},{alignment},{cfg['margin_h']},{cfg['margin_h']},{cfg['margin_v']},1",
        '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
    ]
    lines = list(header)
    for cue in timeline['cues']:
        # Quantize both formats to the same ASS centisecond precision.
        text = r'\N'.join(_escape_ass(line) for line in cue['lines'])
        lines.append(f"Dialogue: 0,{ass_time(cue['start'])},{ass_time(cue['end'])},Default,,0,0,0,,{text}")
    dest = os.path.join(project_dir, 'final-captions.ass')
    with open(dest, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(lines)+'\n')
    with open(os.path.join(project_dir, 'captions-display.json'), 'w', encoding='utf-8') as handle:
        json.dump({'renderer': 'ASS/libass', 'display_mode': 'static phrase',
                   'timeline_fingerprint': timeline['fingerprint'],
                   'play_resolution': {'width': cfg['width'], 'height': cfg['height']},
                   'font': {'name': cfg['font'], 'size': cfg['font_size']},
                   'max_chars_per_line': cfg['max_chars_per_line'], 'max_lines': cfg['max_lines'],
                   'events': len(timeline['cues']), 'qa_status': timeline['qa']['status'],
                   'beats': timeline['beats']}, handle, ensure_ascii=False, indent=2)
    print(f"ASS: {dest} ({len(timeline['cues'])} shared phrase cues)")
    return dest


def run(project_dir, beat_spans=None, width=None, height=None, timeline=None, force=False):
    configure_console()
    refuse_out_dir(project_dir)
    with open(os.path.join(project_dir, "beats.json"), encoding="utf-8-sig") as handle:
        doc = json.load(handle)

    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'pipeline.json'), encoding='utf-8-sig') as handle:
        default_display = (json.load(handle).get('caption_render') or {}).get('display_mode', 'static')
    display = str(doc.get('caption_display') or (doc.get('caption_render') or {}).get('display_mode') or default_display).lower()
    if display in {'static', 'phrase', 'phrase_static'}:
        if timeline is None:
            from caption_timeline import build
            timeline = build(project_dir, beat_spans, width, height, force)
        return write_static_ass(project_dir, timeline)

    dimensions = {'16:9': (1920, 1080), '9:16': (1080, 1920), '1:1': (1080, 1080)}
    default_width, default_height = dimensions.get(doc.get('aspect', '16:9'), (1920, 1080))
    width, height = width or default_width, height or default_height

    settings = alignment_settings(doc)
    language = language_code(doc)
    engine, alignment_error = load_alignment_model(settings, language)
    if alignment_error:
        print(f"[captions] {alignment_error}")
    spans = beat_spans or calculate_beat_spans(doc, project_dir)
    caption_cfg = {}
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "pipeline.json")
    try:
        with open(config_path, encoding="utf-8-sig") as handle:
            caption_cfg.update(json.load(handle).get("caption_render") or {})
    except (OSError, ValueError, TypeError):
        pass
    caption_cfg.update(doc.get("caption_render") or {})
    display_mode = str(doc.get("caption_display") or caption_cfg.get("display_mode") or "static").lower()
    static_display = display_mode in {"static", "phrase", "phrase_static"}
    font_name = str(caption_cfg.get("font", "Arial"))
    font_size = int(caption_cfg.get("font_size", 44))
    max_chars = int(caption_cfg.get("max_chars_per_line", 42))
    margin_v = int(caption_cfg.get("margin_v", 74))
    pop_scale = int(caption_cfg.get("pop_scale", 116))
    pop_ms = int(caption_cfg.get("pop_ms", 135))
    # Preserve a user's configured pop strength while using fixed 1080p PlayRes.
    pop_scale = max(100, min(130, pop_scale))
    pop_ms = max(60, min(300, pop_ms))

    events = []
    reports = []
    for span in spans:
        beat = span["beat"]
        beat_id = beat.get("id", "beat")
        narration = (beat.get("narration") or "").strip()
        audio = beat.get("narration_audio")
        if audio and not os.path.isabs(audio):
            audio = os.path.abspath(os.path.join(project_dir, audio))
        if not narration or not audio or not os.path.isfile(audio):
            continue

        phrases = caption_units_for_beat(beat, narration, language)
        tokens_by_phrase = [phrase.split() for phrase in phrases]
        all_tokens = [token for phrase_tokens in tokens_by_phrase for token in phrase_tokens]
        if not all_tokens:
            continue

        words, source = _read_or_align_words(engine, audio, project_dir, beat_id, language, narration)
        duration = float(span.get("audio_dur") or beat.get("narration_dur") or probe_dur(audio))

        if static_display:
            phrase_intervals = None
            metrics = {"exact_match_ratio": 0.0, "coverage": 0.0}
            method = "speech-envelope estimate"
            if words:
                phrase_intervals, metrics = align_units_to_words(
                    phrases, words, language,
                    settings.get("min_exact_match_ratio", 0.95),
                )
                if phrase_intervals:
                    timing_ok, timing_metrics = validate_alignment_timing(phrase_intervals, audio, duration)
                    metrics.update(timing_metrics)
                    if timing_ok:
                        method = f"WhisperX phrase alignment ({source})"
                    else:
                        phrase_intervals = None
                        metrics["reason"] = metrics.get("timing_reason")
            if not phrase_intervals:
                speech_start, speech_end, pauses = detect_speech_timing(audio, duration)
                phrase_intervals = caption_intervals(phrases, duration, speech_start, speech_end, pauses)
            phrase_intervals = stabilize_caption_intervals(phrase_intervals, language)
            for phrase, phrase_start, phrase_end in phrase_intervals:
                phrase_start = max(0.0, min(duration, float(phrase_start)))
                phrase_end = max(phrase_start + 0.02, min(duration, float(phrase_end)))
                if phrase_end <= phrase_start:
                    continue
                text = _wrap_static_phrase(phrase, max_chars)
                if text:
                    events.append((span["start"] + phrase_start, span["start"] + phrase_end, text))
            reports.append({
                "beat_id": beat_id,
                "method": method,
                "spoken_tokens": len(all_tokens),
                **metrics,
            })
            continue

        word_intervals = None
        phrase_intervals = None
        metrics = {"exact_match_ratio": 0.0, "coverage": 0.0}
        if words:
            word_intervals, metrics = align_units_to_words(
                all_tokens, words, language,
                settings.get("min_exact_match_ratio", 0.95),
                min_event_duration=0.025,
            )
            phrase_intervals, _ = align_units_to_words(
                phrases, words, language,
                settings.get("min_exact_match_ratio", 0.95),
                min_event_duration=0.025,
            )
            if word_intervals:
                timing_ok, timing_metrics = validate_alignment_timing(word_intervals, audio, duration)
                metrics.update(timing_metrics)
                if not timing_ok:
                    word_intervals = None
                    phrase_intervals = None
                    source = "speech-envelope fallback"
                    metrics["reason"] = metrics.get("timing_reason")

        if word_intervals:
            timed_tokens = word_intervals
            method = f"word timestamps ({source})"
        else:
            if not phrase_intervals:
                speech_start, speech_end, pauses = detect_speech_timing(audio, duration)
                phrase_intervals = caption_intervals(phrases, duration, speech_start, speech_end, pauses)
                method = "speech-envelope estimate"
            else:
                method = "phrase timestamps interpolated"
            timed_tokens = _spread_phrase_words(phrases, phrase_intervals)

        phrase_token_offset = 0
        for phrase_index, phrase_tokens in enumerate(tokens_by_phrase):
            if not phrase_tokens:
                continue
            timed = timed_tokens[phrase_token_offset:phrase_token_offset + len(phrase_tokens)]
            phrase_token_offset += len(phrase_tokens)
            if len(timed) != len(phrase_tokens):
                continue

            phrase_start = min(float(item[1]) for item in timed)
            phrase_end = max(float(item[2]) for item in timed)
            next_phrase_start = None
            if phrase_index + 1 < len(tokens_by_phrase):
                next_phrase_tokens = sum(len(items) for items in tokens_by_phrase[:phrase_index + 1])
                next_timed = timed_tokens[next_phrase_tokens:next_phrase_tokens + 1]
                if next_timed:
                    next_phrase_start = float(next_timed[0][1])
            if next_phrase_start is not None:
                phrase_end = min(phrase_end, next_phrase_start)
            phrase_start = max(0.0, min(duration, phrase_start))
            phrase_end = max(phrase_start + 0.02, min(duration, phrase_end))

            for word_index, timed_word in enumerate(timed):
                word_start = max(phrase_start, float(timed_word[1]))
                if word_index + 1 < len(timed):
                    word_end = max(word_start + 0.02, float(timed[word_index + 1][1]))
                else:
                    word_end = phrase_end
                word_end = min(phrase_end, word_end)
                if word_end <= word_start:
                    word_end = min(duration, word_start + 0.03)
                if word_end <= word_start:
                    continue
                text = _wrapped_prefix(
                    phrase_tokens, word_index + 1, max_chars, word_index, pop_scale, pop_ms,
                )
                events.append((span["start"] + word_start, span["start"] + word_end, text))

        reports.append({
            "beat_id": beat_id,
            "method": method,
            **metrics,
            "spoken_tokens": len(all_tokens),
        })

    events.sort(key=lambda item: (item[0], item[1]))
    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {int(width)}",
        f"PlayResY: {int(height)}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&HCC000000,&H64000000,0,0,0,0,100,100,0,0,1,2,1.2,2,80,80,{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    lines = list(header)
    for start, end, text in events:
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{text}")

    dest_name = "final-captions.ass" if static_display else "final-word-reveal.ass"
    dest = os.path.join(project_dir, dest_name)
    with open(dest, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    report_name = "captions-display.json" if static_display else "captions-word-reveal.json"
    report_path = os.path.join(project_dir, report_name)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump({
            "renderer": "ASS/libass",
            "display_mode": "static phrase" if static_display else "progressive word reveal",
            "play_resolution": {"width": int(width), "height": int(height)},
            "font": {"name": font_name, "size": font_size},
            "max_chars_per_line": max_chars,
            "max_lines": 2,
            "events": len(events),
            "beats": reports,
        }, handle, ensure_ascii=False, indent=2)
    label = "static phrase cues" if static_display else "progressive word events"
    print(f"ASS: {dest} ({len(events)} {label})")
    print(f"Caption display report: {report_path}")
    return dest


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python export_ass.py <episode_dir>")
    run(os.path.abspath(sys.argv[1]), force='--redo' in sys.argv[2:])
