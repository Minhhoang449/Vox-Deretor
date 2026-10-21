import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from export_youtube import check_early_phrase

P = ["what did ancient egyptians eat"]

def test_phrase_in_opening_passes():
    assert check_early_phrase([{"narration": "So what did ancient Egyptians eat at work?"}], P) == []

def test_phrase_after_60s_warns():
    beats = [{"narration": "x", "start": 0, "duration": 70},
             {"narration": "What did ancient Egyptians eat?", "start": 70, "duration": 5}]
    assert check_early_phrase(beats, P)

def test_estimated_timing_warns_when_late():
    beats = [{"narration": "word " * 200}, {"narration": "What did ancient Egyptians eat?"}]
    assert check_early_phrase(beats, P)

def test_no_phrases_warns():
    assert check_early_phrase([{"narration": "hi"}], [])

def test_japanese_phrase():
    assert check_early_phrase([{"narration": "栃の実はなぜ苦い？栃の実のアク抜きを見ます。"}], ["栃の実 アク抜き".replace(" ", "の")]) == []
