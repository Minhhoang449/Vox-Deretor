#!/usr/bin/env python3
"""
Write phrase-level final.srt beside the episode, timed to the assembled film.

Same idea as Vox-AI render.py: split each beat's canonical narration into
readable phrases, then place those cues on the real speech in that beat's
WAV (silence bounds and pauses). Cue times are offset to the beat's start
on the final timeline, using the same shot-duration math as assemble.py.

Usage: python export_srt.py <episode_dir>
"""
import os
import re
import subprocess
import sys
import textwrap

from local_guard import refuse_out_dir

TAIL = 0.5


def srt_timestamp(seconds):
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, ms = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{ms:03}"


def split_caption_units(text, max_words=8, max_chars=64):
    """Split narration into readable spoken phrases, not one caption per beat."""
    stripped = text.strip()
    if stripped and " " not in stripped and "\u3000" not in stripped and len(stripped) > 18:
        return _split_unspaced(stripped, min(max_chars, 22))
    words = stripped.split()
    if not words:
        return []
    units, current = [], []
    for word in words:
        if current and (len(current) >= max_words or len(" ".join([*current, word])) > max_chars):
            units.append(" ".join(current))
            current = []
        current.append(word)
        if len(current) >= 4 and re.search(r"[,;:!?。！？]$", word):
            units.append(" ".join(current))
            current = []
    if current:
        units.append(" ".join(current))
    return units


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


def detect_speech_timing(audio, duration):
    """Find speech bounds and usable pauses from the WAV envelope."""
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", audio, "-af", "silencedetect=noise=-45dB:d=0.16",
         "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = result.stderr or ""
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
    leading_end = silences[0][1] if silences and silences[0][0] <= 0.03 else 0.0
    trailing_start = silences[-1][0] if silences and silences[-1][1] >= duration - 0.03 else duration
    pauses = [
        (start, end) for start, end in silences
        if end - start >= 0.18 and start > leading_end + 0.02 and end < trailing_start - 0.02
    ]
    if leading_end >= trailing_start or result.returncode:
        return 0.0, duration, []
    return leading_end, trailing_start, pauses


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


def shots_of(beat):
    if beat.get("shots"):
        return list(beat["shots"])
    return [beat]


def beat_spans(doc):
    """Match assemble.py: narration is delayed to each beat's visual start."""
    spans = []
    t = 0.0
    for beat in doc["beats"]:
        start = t
        shot_list = shots_of(beat)
        durs = [float(s.get("dur", 10)) for s in shot_list]
        audio = beat.get("narration_audio")
        narr = float(beat.get("narration_dur") or 0)
        if narr <= 0 and audio and os.path.exists(audio):
            narr = probe_dur(audio)
        need = (narr or sum(durs)) + TAIL
        if shot_list and sum(durs) < need and shot_list[-1].get("kind") != "host":
            durs[-1] += need - sum(durs)
        t += sum(durs) if durs else need
        spans.append({"start": start, "beat": beat, "audio_dur": narr})
    return spans


def run(project_dir):
    refuse_out_dir(project_dir)
    import json
    with open(os.path.join(project_dir, "beats.json"), encoding="utf-8-sig") as f:
        doc = json.load(f)
    blocks = []
    cue = 0
    for span in beat_spans(doc):
        beat = span["beat"]
        text = (beat.get("narration") or "").strip()
        audio = beat.get("narration_audio")
        if not text or not audio or not os.path.exists(audio):
            continue
        duration = span["audio_dur"] or probe_dur(audio)
        units = split_caption_units(text)
        speech_start, speech_end, pauses = detect_speech_timing(audio, duration)
        for phrase, start, end in caption_intervals(units, duration, speech_start, speech_end, pauses):
            cue += 1
            blocks.append(
                f"{cue}\n{srt_timestamp(span['start'] + start)} --> "
                f"{srt_timestamp(span['start'] + end)}\n{textwrap.fill(phrase, width=42)}"
            )
    dest = os.path.join(project_dir, "final.srt")
    with open(dest, "w", encoding="utf-8") as f:
        f.write("\n\n".join(blocks) + ("\n" if blocks else ""))
    print(f"SRT: {dest} ({cue} cues)")
    return dest


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python export_srt.py <episode_dir>")
    run(os.path.abspath(sys.argv[1]))
