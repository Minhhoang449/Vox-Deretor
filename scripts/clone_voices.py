#!/usr/bin/env python3
"""Encode non-VieNeu channel reference clips into OmniVoice clone prompts.

Reads config/channels.json, loads D:\\Coder\\Omivoice\\weights once, and writes
voice.pt next to each reference audio. Later narration loads that file.

Usage: python scripts/clone_voices.py
"""
import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHANNELS = os.path.join(ROOT, "config", "channels.json")
PIPELINE = os.path.join(ROOT, "config", "pipeline.json")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=CHANNELS, help='Channel configuration to enroll and update')
    args = parser.parse_args()
    with open(PIPELINE, encoding="utf-8-sig") as handle:
        pipeline = json.load(handle)
    cfg = pipeline["omnivoice"]
    vieneu_languages = set(pipeline.get('vieneu', {}).get('languages', ['vi']))
    root = os.environ.get("OMNIVOICE_ROOT", cfg.get("root") or r"D:\Coder\Omivoice")
    if root not in sys.path:
        sys.path.insert(0, root)
    import torch
    from omnivoice import OmniVoice
    from omnivoice.utils.common import get_best_device

    with open(args.config, encoding="utf-8-sig") as handle:
        doc = json.load(handle)
    targets = [c for c in doc['channels'] if c.get('language') not in vieneu_languages]
    if not targets:
        raise SystemExit('No OmniVoice channels in the selected configuration')
    device = os.environ.get("OMNIVOICE_DEVICE") or get_best_device()
    dtype = torch.float16 if device != "cpu" else torch.float32
    model_id = cfg.get("model") or "k2-fsa/OmniVoice"
    print(f"loading {model_id} on {device}")
    model = OmniVoice.from_pretrained(model_id, device_map=device, dtype=dtype)
    for channel in targets:
        ref = channel.setdefault("voice_reference", {})
        audio = ref.get("audio") or ""
        transcript = ref.get("transcript") or ""
        if not os.path.isfile(audio) or not os.path.isfile(transcript):
            raise SystemExit(f"{channel['id']} is missing {audio} or {transcript}")
        with open(transcript, encoding="utf-8-sig") as handle:
            ref_text = handle.read().strip()
        if not ref_text:
            raise SystemExit(f"{channel['id']} transcript is empty")
        prompt_path = os.path.join(os.path.dirname(audio), "voice.pt")
        print(f"clone {channel['id']} -> {prompt_path}")
        prompt = model.create_voice_clone_prompt(ref_audio=audio, ref_text=ref_text)
        prompt.save(prompt_path)
        ref["prompt"] = prompt_path.replace("\\", "/")
    with open(args.config, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"cloned {len(targets)} OmniVoice voices")


if __name__ == "__main__":
    main()
