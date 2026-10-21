#!/usr/bin/env python3
"""Encode the Vietnamese reference clip into a VieNeu voice file.

This pipeline routes Vietnamese to VieNeu. This enrolls each language=vi
channel once: denoise the reference clip, extract the speaker embedding and
reference codes, and write vieneu-voice.json beside the clip.

Usage: python scripts/clone_vieneu_voice.py
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHANNELS = os.path.join(ROOT, "config", "channels.json")
PIPELINE = os.path.join(ROOT, "config", "pipeline.json")


def to_wav(src):
    folder = os.path.dirname(src)
    fd, dest = tempfile.mkstemp(suffix=".wav", dir=folder)
    os.close(fd)
    subprocess.check_call(
        ["ffmpeg", "-y", "-i", src, "-ac", "1", "-ar", "44100", dest],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return dest


def write_voice(path, name, entry):
    import numpy as np

    emb = entry.get("speaker_emb")
    codes = entry.get("codes")
    data = {
        "meta": {"note": "VieNeu v3 Turbo clone: speaker embedding + reference codes"},
        "default_voice": name,
        "presets": {
            name: {
                "description": entry.get("description", ""),
                "gender": entry.get("gender", ""),
                "style": entry.get("style") or "tu_nhien",
                "speaker_emb": [round(float(x), 6) for x in np.asarray(emb).reshape(-1)],
                "codes": None if codes is None else np.asarray(codes, dtype=int).tolist(),
            }
        },
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False)
        handle.write("\n")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=CHANNELS, help='Channel configuration to enroll and update')
    args = parser.parse_args()
    with open(PIPELINE, encoding="utf-8-sig") as handle:
        cfg = json.load(handle)["vieneu"]
    root = cfg.get("root") or r"D:\Coder\VieNeu-TTS"
    src = os.path.join(root, "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from vieneu import Vieneu

    with open(args.config, encoding="utf-8-sig") as handle:
        doc = json.load(handle)
    targets = [c for c in doc["channels"] if (c.get("language") or "").lower() == "vi"]
    if not targets:
        raise SystemExit("No Vietnamese channel in config/channels.json")
    model_dir = cfg.get("model")
    print(f"loading {model_dir}", flush=True)
    model = Vieneu(
        mode="v3turbo",
        backbone_repo=model_dir,
        model_subfolder=cfg.get("model_subfolder") or "update",
        moss_tokenizer=cfg.get("moss_tokenizer"),
        backend="pytorch",
    )
    for channel in targets:
        ref = channel.setdefault("voice_reference", {})
        audio = ref.get("audio") or ""
        if not os.path.isfile(audio):
            raise SystemExit(f"{channel['id']} is missing {audio}")
        name = channel.get("voice_profile_name") or channel.get("display_name") or channel["id"]
        out = os.path.join(os.path.dirname(audio), "vieneu-voice.json")
        wav = to_wav(audio)
        print(f"clone {channel['id']} -> {out}", flush=True)
        try:
            model.add_voice(
                name,
                wav,
                denoise=True,
                description=channel.get("display_name") or name,
                gender=channel.get("voice_gender") or "",
            )
        finally:
            try:
                os.remove(wav)
            except OSError:
                pass
        write_voice(out, name, model.get_preset_voice(name))
        ref["vieneu_voice"] = out.replace("\\", "/")
        print(f"saved {out}", flush=True)
    with open(args.config, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"cloned {len(targets)} Vietnamese voice(s)")


if __name__ == "__main__":
    main()
