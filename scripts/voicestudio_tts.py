#!/usr/bin/env python3
"""
Narration via the local VoiceStudio API (OpenAI-compatible speech endpoint).

VoiceStudio must be open. The per-channel profile id lives on each entry in
config/channels.json (`voice`). Shared engine settings live in
config/pipeline.json (`voice_studio`): omnivoice, speed 0.8, wav, 32 steps.
narration_direction stays an editorial note for the writer. It is not sent
as an OmniVoice instruct string, because the saved profile already holds
the voice design.

Override the base URL with VOICESTUDIO_BASE_URL. On localhost any non-empty
VOICESTUDIO_API_KEY works; the default is "local".

Each beat is written to audio/narr_<id>.txt even if the API is down, so the
line can be pasted into the VoiceStudio window. Existing mp3/wav files are
kept unless --redo is passed. Music is not generated; drop audio/bgm.mp3
yourself if you want a bed under the voice.

Usage: python voicestudio_tts.py <project_dir> [--redo]
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

from codex_prompts import load, save

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PIPELINE_FILE = os.path.join(ROOT, "config", "pipeline.json")


def voice_studio():
    with open(PIPELINE_FILE, encoding="utf-8-sig") as f:
        return json.load(f)["voice_studio"]


def probe_dur(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def api_base():
    override = os.environ.get("VOICESTUDIO_BASE_URL")
    if override:
        return override.rstrip("/")
    base = voice_studio()["base_url"].rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    return base


def api_key():
    return os.environ.get("VOICESTUDIO_API_KEY", "local")


def origin():
    base = api_base()
    if base.endswith("/v1"):
        return base[:-3]
    return base


def health():
    url = origin() + "/health"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def synthesize(text, dest_stem, voice, language, speed, model, num_step, response_format):
    body = {
        "model": model,
        "voice": voice,
        "input": text,
        "response_format": response_format,
        "speed": speed,
        "num_step": num_step,
        "language": language,
    }
    req = urllib.request.Request(
        api_base() + "/audio/speech",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = resp.read()
            ctype = (resp.headers.get("Content-Type") or "").lower()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"VoiceStudio {e.code} for {os.path.basename(dest_stem)}: {detail}")
    ext = ".wav" if ("wav" in ctype or data[:4] == b"RIFF") else ".mp3"
    dest = dest_stem + ext
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def existing_audio(adir, beat_id):
    for ext in (".mp3", ".wav"):
        path = os.path.join(adir, f"narr_{beat_id}{ext}")
        if os.path.exists(path):
            return path
    return None


def run(project_dir, redo=False):
    bpath, doc = load(project_dir)
    if not doc.get("channel_id"):
        raise SystemExit(
            "No channel bound. Run: python scripts/channels.py bind <channel-id> <slug>"
        )
    doc["pipeline"] = "local"
    speech = voice_studio()
    voice = doc.get("voice") or {}
    channel = doc.get("channel") or {}
    voice_id = voice.get("voice_id") or channel.get("voice")
    if not voice_id:
        raise SystemExit(f"Channel {doc.get('channel_id')} has no VoiceStudio profile id.")
    language = voice.get("language") or channel.get("language") or doc.get("language")
    speed = float(speech.get("default_speed", 0.8))
    model = speech.get("model", "omnivoice")
    num_step = int(speech.get("num_step", 32))
    response_format = speech.get("response_format", "wav")
    profile = voice.get("profile_name") or channel.get("voice_profile_name") or voice_id
    print(f"[voice] {doc['channel_id']} -> {profile} ({voice_id}), {language}, {model}, speed {speed}")

    adir = os.path.join(project_dir, "audio")
    os.makedirs(adir, exist_ok=True)
    for beat in doc["beats"]:
        text = (beat.get("narration") or "").strip()
        with open(os.path.join(adir, f"narr_{beat['id']}.txt"), "w", encoding="utf-8") as f:
            f.write(text + "\n")

    if not health():
        save(bpath, doc)
        raise SystemExit(
            "VoiceStudio is not running. Open the app (API on "
            f"{origin()}) and run this again. Narration text is already in {adir}."
        )

    for beat in doc["beats"]:
        text = (beat.get("narration") or "").strip()
        if not text:
            print(f"[narr {beat['id']}] empty — skipped")
            continue
        prior = existing_audio(adir, beat["id"])
        if prior and not redo:
            beat["narration_audio"] = prior
            beat["narration_dur"] = round(probe_dur(prior), 2)
            print(f"[narr {beat['id']}] reuse {prior} ({beat['narration_dur']}s)")
            continue
        dest = synthesize(
            text, os.path.join(adir, f"narr_{beat['id']}"),
            voice_id, language, speed, model, num_step, response_format)
        beat["narration_audio"] = dest
        beat["narration_dur"] = round(probe_dur(dest), 2)
        print(f"[narr {beat['id']}] {beat['narration_dur']}s -> {dest}")

    bgm = os.path.join(adir, "bgm.mp3")
    if os.path.exists(bgm):
        doc["bgm_path"] = bgm
        doc["bgm_dur"] = round(probe_dur(bgm), 2)
        print(f"[bgm] reuse {bgm}")
    else:
        doc.pop("bgm_path", None)
        print("[bgm] none — drop audio/bgm.mp3 if you want music under the voice")

    save(bpath, doc)
    print("updated", bpath)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python voicestudio_tts.py <project_dir> [--redo]")
    proj = os.path.abspath(sys.argv[1])
    run(proj, redo="--redo" in sys.argv[2:])
