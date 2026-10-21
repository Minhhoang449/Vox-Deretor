"""Shared synthesis defaults and full-stop boundaries for local narration."""
import math
import re

import numpy as np

PAUSE_POLICY = "full-stop-silence-v2"
_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc",
    "e.g", "i.e", "ts", "ths", "pgs", "gs", "tp", "srta", "sra",
}


def effective_tts_settings(doc, cfg):
    speed = float(doc.get("tts_speed", cfg["default_speed"]))
    pause = float(doc.get("tts_pause_after_period_seconds", cfg["pause_after_period_seconds"]))
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError("tts_speed must be finite and greater than zero.")
    if not math.isfinite(pause) or pause < 0:
        raise ValueError("tts_pause_after_period_seconds must be finite and nonnegative.")
    return speed, pause


def split_period_pauses(text):
    """Recognize Western/Japanese full stops without splitting decimals or titles."""
    chunks = []
    start = 0
    for match in re.finditer(r'[.。．]["\'”’»）)\]」』]*', text):
        pos = match.start()
        if text[pos] == ".":
            if match.end() < len(text) and not text[match.end()].isspace():
                continue
            # An ellipsis is hesitation, not a sentence-ending period.
            if pos > 0 and text[pos - 1] == ".":
                continue
            word = re.search(r"([\w.]+)$", text[:pos])
            token = word.group(1) if word else ""
            has_more = bool(text[match.end():].strip())
            if has_more and (token.casefold() in _ABBREVIATIONS or
                             re.fullmatch(r"(?:[A-Za-z]\.)*[A-Za-z]", token)):
                continue
        chunk = text[start:match.end()].strip()
        if chunk:
            chunks.append((chunk, True))
        start = match.end()
    remainder = text[start:].strip()
    if remainder:
        chunks.append((remainder, False))
    return chunks or [(text.strip(), False)]


def join_period_audio(audios, chunks, rate, pause_seconds, return_segments=False):
    """Insert sample-counted full-stop silence, including after a final full stop.

    Remove only negligible model edge silence at an inserted boundary; preserve
    a 5 ms guard around speech. Other punctuation keeps the engine's rhythm.
    """
    audios = list(audios)
    if len(audios) != len(chunks):
        raise ValueError("TTS returned a different number of waveforms than sentences.")
    pieces = []
    segments = []
    cursor = 0
    pause_samples = int(round(rate * pause_seconds))
    guard = int(round(rate * 0.005))
    previous_period = False
    for audio, (text, ends_with_period) in zip(audios, chunks):
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        if pause_samples and audio.size and (previous_period or ends_with_period):
            threshold = max(1e-6, float(np.max(np.abs(audio))) * 0.001)
            active = np.flatnonzero(np.abs(audio) > threshold)
            if active.size:
                left = max(0, int(active[0]) - guard) if previous_period else 0
                right = min(audio.size, int(active[-1]) + guard + 1) if ends_with_period else audio.size
                audio = audio[left:right]
        pieces.append(audio)
        segments.append({'text': text, 'start': cursor / rate, 'end': (cursor + audio.size) / rate})
        cursor += audio.size
        if ends_with_period and pause_samples:
            pieces.append(np.zeros(pause_samples, dtype=np.float32))
            cursor += pause_samples
        previous_period = ends_with_period
    result = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
    return (result, segments) if return_segments else result
