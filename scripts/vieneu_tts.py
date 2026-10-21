#!/usr/bin/env python3
"""Vietnamese narration via the local VieNeu-TTS checkout.

OmniVoice stays the reader for every other language. Vietnamese uses the saved
channel clone (speaker embedding + reference codes), not a fresh encode, and
not an OmniVoice instruct string.

Usage: python scripts/omnivoice_tts.py <episode_dir> [--redo]
"""
import json
import os
import subprocess
import sys

from codex_prompts import load, save
from narration_lock import assert_approved
from tts_settings import PAUSE_POLICY, effective_tts_settings, join_period_audio, split_period_pauses
from omnivoice_tts import (
    existing_audio,
    pipeline_doc,
    probe_dur,
    resolve_background_music,
    save_audio_cache,
    save_sentence_segments,
    tts_cache_fingerprint,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHANNELS = os.path.join(ROOT, "config", "channels.json")


def vieneu_config():
    cfg = pipeline_doc().get("vieneu") or {}
    if not cfg:
        raise SystemExit("config/pipeline.json has no vieneu block.")
    return cfg


def ensure_python(cfg):
    py = cfg.get("python") or ""
    if not py or not os.path.isfile(py):
        raise SystemExit(
            "VieNeu's Python is missing.\n"
            "In D:\\Coder\\VieNeu-TTS run: uv sync --extra cuda"
        )
    if os.path.normcase(os.path.abspath(sys.executable)) == os.path.normcase(os.path.abspath(py)):
        return
    cmd = [py, os.path.abspath(sys.argv[0]), *sys.argv[1:]]
    raise SystemExit(subprocess.call(cmd))


def saved_voice_path(doc):
    voice = doc.get("voice") or {}
    channel = doc.get("channel") or {}
    ref = channel.get("voice_reference") or {}
    for candidate in (voice.get("vieneu_voice"), ref.get("vieneu_voice")):
        if candidate and os.path.isfile(candidate):
            return candidate
    channel_id = doc.get("channel_id") or ""
    if os.path.isfile(CHANNELS):
        with open(CHANNELS, encoding="utf-8-sig") as handle:
            roster = json.load(handle)
        for item in roster.get("channels") or []:
            if item.get("id") != channel_id:
                continue
            path = ((item.get("voice_reference") or {}).get("vieneu_voice")) or ""
            if path and os.path.isfile(path):
                return path
    audio = voice.get("reference_audio") or ref.get("audio") or ""
    if audio:
        sibling = os.path.join(os.path.dirname(audio), "vieneu-voice.json")
        if os.path.isfile(sibling):
            return sibling
    raise SystemExit(
        "No VieNeu clone for this channel. Run: python scripts/clone_vieneu_voice.py"
    )


def load_saved_voice(path):
    import numpy as np
    from vieneu_utils.core_utils import strip_encoder_pad_frame

    with open(path, encoding="utf-8-sig") as handle:
        data = json.load(handle)
    presets = data.get("presets") or {}
    name = data.get("default_voice") or ""
    entry = presets.get(name) if name in presets else None
    if entry is None and presets:
        name, entry = next(iter(presets.items()))
    if not entry or entry.get("speaker_emb") is None:
        raise SystemExit(f"VieNeu voice file has no speaker embedding: {path}")
    codes = entry.get("codes")
    return name, {
        "speaker_emb": np.asarray(entry["speaker_emb"], dtype=np.float32),
        "codes": None if codes is None else strip_encoder_pad_frame(np.asarray(codes, dtype=np.int64)),
    }


def load_model(cfg):
    root = cfg.get("root") or r"D:\Coder\VieNeu-TTS"
    src = os.path.join(root, "src")
    if os.path.isdir(src) and src not in sys.path:
        sys.path.insert(0, src)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    try:
        from vieneu import Vieneu
    except ImportError as exc:
        raise SystemExit(
            "VieNeu is not importable from this Python.\n"
            f"Checkout: {root}\n"
            "Use its venv: D:\\Coder\\VieNeu-TTS\\.venv\\Scripts\\python.exe\n"
            f"Missing: {exc}"
        ) from exc
    model_dir = cfg.get("model") or ""
    moss = cfg.get("moss_tokenizer") or ""
    print(f"[vieneu] {model_dir}", flush=True)
    return Vieneu(
        mode="v3turbo",
        backbone_repo=model_dir,
        model_subfolder=cfg.get("model_subfolder") or "update",
        moss_tokenizer=moss,
        backend="pytorch",
    )


def generate_with_period_pauses(model, text, voice_data, rate, pause_seconds, return_segments=False):
    chunks = split_period_pauses(text) if pause_seconds else [(text, False)]
    audios = [model.infer(chunk, voice=voice_data, apply_watermark=False) for chunk, _ in chunks]
    return join_period_audio(audios, chunks, rate, pause_seconds, return_segments)


def run(project_dir, redo=False):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = vieneu_config()
    bpath, doc = load(project_dir)
    assert_approved(project_dir, doc)
    ensure_python(cfg)
    if not doc.get("channel_id"):
        raise SystemExit(
            "No channel bound. Run: python scripts/channels.py bind <channel-id> <slug>"
        )
    doc["pipeline"] = "local"
    speed, pause_after_period = effective_tts_settings(doc, cfg)
    # v3 Turbo accepts unknown kwargs but does not implement a speed control.
    # Never silently ignore a requested speed or stretch approved narration.
    if speed != 1.0:
        raise SystemExit("VieNeu v3 Turbo supports native tts_speed 1.0 only; no audio time-stretch is applied.")
    voice_file = saved_voice_path(doc)
    name, voice_data = load_saved_voice(voice_file)
    print(f"[voice] {doc['channel_id']} -> VieNeu {name}, clone {voice_file}, "
          f"speed {speed}, pause after period {pause_after_period}s", flush=True)

    adir = os.path.join(project_dir, "audio")
    os.makedirs(adir, exist_ok=True)
    pending = []
    for beat in doc["beats"]:
        text = (beat.get("narration") or "").strip()
        with open(os.path.join(adir, f"narr_{beat['id']}.txt"), "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        if not text:
            print(f"[narr {beat['id']}] empty — skipped")
            continue
        fingerprint = tts_cache_fingerprint(
            "vieneu-v3-turbo",
            text,
            "vi",
            {**cfg, "mode": "v3turbo", "backend": "pytorch",
             "effective_speed": speed,
             "effective_pause_after_period_seconds": pause_after_period,
             "pause_policy": PAUSE_POLICY},
            {"profile_name": name},
            voice_files=(voice_file,),
        )
        prior = existing_audio(adir, beat["id"], fingerprint)
        if prior and not redo:
            save_audio_cache(adir, beat["id"], fingerprint, prior, text=text)
            beat["narration_audio"] = prior
            beat["narration_dur"] = round(probe_dur(prior), 2)
            print(f"[narr {beat['id']}] reuse {prior} ({beat['narration_dur']}s)")
            continue
        pending.append((beat, text, fingerprint))

    if pending:
        import soundfile as sf
        model = load_model(cfg)
        rate = int(getattr(model, "sample_rate", cfg.get("sample_rate", 48000)))
        for beat, text, fingerprint in pending:
            audio, segments = generate_with_period_pauses(model, text, voice_data, rate, pause_after_period, True)
            dest = os.path.join(adir, f"narr_{beat['id']}.wav")
            sf.write(dest, audio, rate)
            save_sentence_segments(dest, segments)
            save_audio_cache(adir, beat["id"], fingerprint, dest, text=text)
            beat["narration_audio"] = dest
            beat["narration_dur"] = round(probe_dur(dest), 2)
            print(f"[narr {beat['id']}] {beat['narration_dur']}s -> {dest}", flush=True)

    bgm = resolve_background_music(project_dir, doc)
    if bgm:
        doc["bgm_path"] = bgm
        doc["bgm_dur"] = round(probe_dur(bgm), 2)
        print(f"[bgm] selected track {bgm}")
    else:
        doc.pop("bgm_path", None)
        music_dir = (pipeline_doc().get("music_library") or {}).get("path") or r"D:\Music"
        print(f"[bgm] none — choose a track from {music_dir} and set bgm_path in beats.json")

    save(bpath, doc)
    print("updated", bpath)
    if doc.get("beats"):
        from narration_review import build as build_review
        build_review(project_dir, os.path.join(project_dir, "review", "narration"), with_audio=True)
        print("Listen before images:", os.path.join(project_dir, "review", "narration", "review.html"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python scripts/vieneu_tts.py <episode_dir> [--redo]")
    run(os.path.abspath(sys.argv[1]), redo="--redo" in sys.argv[2:])
