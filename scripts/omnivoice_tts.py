#!/usr/bin/env python3
"""
Narration via the local OmniVoice checkout. VoiceStudio is not used.

The model is k2-fsa/OmniVoice (config/pipeline.json → omnivoice). Each channel
is cloned from voice_reference audio plus its transcript. narration_direction
stays an editorial note and is not sent as an instruct string.

The checkout defaults to D:\\Coder\\Omivoice. Override with OMNIVOICE_ROOT.
Weights download from Hugging Face on the first run.

Usage: python scripts/omnivoice_tts.py <episode_dir> [--redo]
"""
import json
import os
import subprocess
import sys

from cache_keys import file_fingerprint, stable_hash
from codex_prompts import load, save
from tts_settings import PAUSE_POLICY, effective_tts_settings, join_period_audio, split_period_pauses
from narration_lock import assert_approved, digest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PIPELINE_FILE = os.path.join(ROOT, "config", "pipeline.json")
DEFAULT_ROOT = r"D:\Coder\Omivoice"


def pipeline_doc():
    with open(PIPELINE_FILE, encoding="utf-8-sig") as handle:
        return json.load(handle)


def speech_config():
    return pipeline_doc()["omnivoice"]


def vieneu_languages():
    raw = (pipeline_doc().get("vieneu") or {}).get("languages") or ["vi"]
    return {str(item).lower() for item in raw}


def omnivoice_root():
    return os.environ.get("OMNIVOICE_ROOT", speech_config().get("root") or DEFAULT_ROOT)


def probe_dur(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def resolve_background_music(project_dir, doc):
    """Keep an explicitly selected library track, or reuse audio/bgm.mp3."""
    configured = doc.get("bgm_path")
    if configured:
        path = configured if os.path.isabs(configured) else os.path.join(project_dir, configured)
        if os.path.isfile(path):
            return os.path.abspath(path)
    local = os.path.join(project_dir, "audio", "bgm.mp3")
    return os.path.abspath(local) if os.path.isfile(local) else None


def tts_cache_fingerprint(engine, text, language, settings, voice=None, voice_files=()):
    voice = voice or {}
    scalar_voice = {
        key: value for key, value in voice.items()
        if isinstance(value, (str, int, float, bool)) or value is None
    }
    sources = {}
    candidates = list(voice_files)
    candidates.extend(
        voice.get(key) for key in (
            "reference_audio", "reference_transcript", "clone_prompt", "vieneu_voice"
        )
    )
    reference_audio = voice.get("reference_audio")
    if engine == "omnivoice" and reference_audio and not voice.get("clone_prompt"):
        candidates.append(os.path.join(os.path.dirname(reference_audio), "voice.pt"))
    seen = set()
    for path in candidates:
        if not isinstance(path, str) or not path:
            continue
        normalized = os.path.normcase(os.path.abspath(path))
        if normalized in seen:
            continue
        seen.add(normalized)
        sources[normalized] = file_fingerprint(path, include_content=True)
    return stable_hash({
        "schema": 1,
        "engine": engine,
        "text": text,
        "language": language,
        "settings": settings,
        "voice": scalar_voice,
        "voice_sources": sources,
    })


def _audio_cache_path(adir, beat_id):
    return os.path.join(adir, f"narr_{beat_id}.cache.json")


def existing_audio(adir, beat_id, fingerprint):
    cache_path = _audio_cache_path(adir, beat_id)
    try:
        with open(cache_path, encoding="utf-8-sig") as handle:
            cache = json.load(handle)
    except (OSError, ValueError, TypeError):
        return None
    if cache.get("fingerprint") != fingerprint:
        return None

    for ext in (".wav", ".mp3"):
        path = os.path.join(adir, f"narr_{beat_id}{ext}")
        if os.path.isfile(path) and cache.get("audio_file") == file_fingerprint(path):
            if cache.get("audio_sha256") and cache["audio_sha256"] != file_fingerprint(path, True).get("sha256"):
                continue
            return path
    return None


def save_audio_cache(adir, beat_id, fingerprint, audio_path, text=None):
    cache_path = _audio_cache_path(adir, beat_id)
    temporary = cache_path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump({
            "fingerprint": fingerprint,
            "audio_file": file_fingerprint(audio_path),
            **({"narration_sha256": digest(text),
                "audio_sha256": file_fingerprint(audio_path, True)["sha256"]}
               if text is not None else {}),
        }, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, cache_path)


def save_sentence_segments(audio_path, segments):
    path = os.path.splitext(audio_path)[0] + '.sentences.json'
    with open(path + '.tmp', 'w', encoding='utf-8') as handle:
        json.dump({'schema_version': 1, 'audio_file': file_fingerprint(audio_path),
                   'segments': segments}, handle, ensure_ascii=False, indent=2)
    os.replace(path + '.tmp', path)


def generate_with_period_pauses(model, text, language, prompt, num_step, speed, rate, pause_seconds, return_segments=False):
    """Generate sentence audio and join it with exact silence after each period."""
    chunks = split_period_pauses(text) if pause_seconds else [(text, False)]
    audios = model.generate(
        text=[chunk for chunk, _ in chunks],
        language=language,
        voice_clone_prompt=prompt,
        num_step=num_step,
        speed=speed,
    )
    return join_period_audio(audios, chunks, rate, pause_seconds, return_segments)


def read_text(path):
    with open(path, encoding="utf-8-sig") as handle:
        return handle.read().strip()


def load_model(cfg):
    root = omnivoice_root()
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        import torch
        from omnivoice import OmniVoice
        from omnivoice.utils.common import get_best_device
    except ImportError as exc:
        raise SystemExit(
            "OmniVoice is not importable from this Python.\n"
            f"Checkout: {root}\n"
            "Install its dependencies in this interpreter, then run again.\n"
            f"Missing: {exc}"
        ) from exc
    device = os.environ.get("OMNIVOICE_DEVICE") or get_best_device()
    dtype_name = (cfg.get("dtype") or "float16").lower()
    dtype = torch.float16 if dtype_name == "float16" and device != "cpu" else torch.float32
    model_id = os.environ.get("OMNIVOICE_MODEL") or cfg.get("model") or "k2-fsa/OmniVoice"
    print(f"[omnivoice] {model_id} on {device}, {dtype}")
    model = OmniVoice.from_pretrained(model_id, device_map=device, dtype=dtype)
    return model


def voice_prompt(model, voice):
    audio = voice.get("reference_audio") or ""
    saved = voice.get("clone_prompt") or ""
    if not saved and audio:
        saved = os.path.join(os.path.dirname(audio), "voice.pt")
    if saved and os.path.isfile(saved):
        from omnivoice import VoiceClonePrompt
        print(f"[voice] saved clone {saved}")
        return VoiceClonePrompt.load(saved)
    transcript = voice.get("reference_transcript") or ""
    if not audio or not os.path.isfile(audio):
        raise SystemExit(f"Reference audio is missing: {audio or '(empty)'}")
    if not transcript or not os.path.isfile(transcript):
        raise SystemExit(f"Reference transcript is missing: {transcript or '(empty)'}")
    ref_text = read_text(transcript)
    if not ref_text:
        raise SystemExit(f"Reference transcript is empty: {transcript}")
    return model.create_voice_clone_prompt(ref_audio=audio, ref_text=ref_text)


def run(project_dir, redo=False):
    bpath, doc = load(project_dir)
    assert_approved(project_dir, doc)
    if not doc.get("channel_id"):
        raise SystemExit(
            "No channel bound. Run: python scripts/channels.py bind <channel-id> <slug>"
        )
    doc["pipeline"] = "local"
    cfg = speech_config()
    voice = doc.get("voice") or {}
    channel = doc.get("channel") or {}
    if not voice.get("reference_audio"):
        ref = channel.get("voice_reference") or {}
        voice["reference_audio"] = ref.get("audio", "")
        voice["reference_transcript"] = ref.get("transcript", "")
    language = voice.get("language") or channel.get("language") or doc.get("language")
    if (language or "").lower() in vieneu_languages():
        from vieneu_tts import run as run_vieneu
        return run_vieneu(project_dir, redo)
    # Episode overrides remain explicit; all other episodes use pipeline defaults.
    speed, pause_after_period = effective_tts_settings(doc, cfg)
    num_step = int(cfg.get("num_step", 32))
    profile = voice.get("profile_name") or channel.get("voice_profile_name") or doc["channel_id"]
    print(
        f"[voice] {doc['channel_id']} -> {profile}, {language}, clone from reference, "
        f"speed {speed}, pause after period {pause_after_period}s"
    )

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
            "omnivoice",
            text,
            language,
            {
                **cfg,
                "effective_model": os.environ.get("OMNIVOICE_MODEL") or cfg.get("model"),
                "effective_speed": speed,
                "effective_num_step": num_step,
                "effective_dtype": cfg.get("dtype", "float16"),
                "effective_pause_after_period_seconds": pause_after_period,
                "pause_policy": PAUSE_POLICY,
            },
            voice,
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
        prompt = voice_prompt(model, voice)
        rate = int(getattr(model, "sampling_rate", cfg.get("sample_rate", 24000)))
        for beat, text, fingerprint in pending:
            audio, segments = generate_with_period_pauses(
                model=model,
                text=text,
                language=language,
                prompt=prompt,
                num_step=num_step,
                speed=speed,
                rate=rate,
                pause_seconds=pause_after_period,
                return_segments=True,
            )
            dest = os.path.join(adir, f"narr_{beat['id']}.wav")
            sf.write(dest, audio, rate)
            save_sentence_segments(dest, segments)
            save_audio_cache(adir, beat["id"], fingerprint, dest, text=text)
            beat["narration_audio"] = dest
            beat["narration_dur"] = round(probe_dur(dest), 2)
            print(f"[narr {beat['id']}] {beat['narration_dur']}s -> {dest}")

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
        raise SystemExit("usage: python scripts/omnivoice_tts.py <episode_dir> [--redo]")
    run(os.path.abspath(sys.argv[1]), redo="--redo" in sys.argv[2:])
