#!/usr/bin/env python3
"""Narration moved to OmniVoice. This name still runs the new script."""
import os
import sys

from omnivoice_tts import run

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python scripts/omnivoice_tts.py <episode_dir> [--redo]")
    print("Narration uses OmniVoice. VoiceStudio is not called.")
    run(os.path.abspath(sys.argv[1]), redo="--redo" in sys.argv[2:])
