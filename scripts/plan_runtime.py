#!/usr/bin/env python3
"""
Plan a main or explicitly selected short-main film from researched narration and individually timed visual shots.

This script writes the timing budget. Imagegen creates stills; FFmpeg/NVENC
adds camera movement and transitions by default (Revideo optional).

  python scripts/plan_runtime.py <episode_dir> --minutes 15
  python scripts/plan_runtime.py <episode_dir> --profile main_short --minutes 9
"""
import json
import math
import os
import sys

from local_guard import refuse_out_dir

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PIPELINE_FILE = os.path.join(ROOT, "config", "pipeline.json")
CHANNELS_FILE = os.path.join(ROOT, "config", "channels.json")


def load_pipeline():
    with open(PIPELINE_FILE, encoding="utf-8-sig") as f:
        return json.load(f)


def load_channel(channel_id):
    with open(CHANNELS_FILE, encoding="utf-8-sig") as f:
        channels = json.load(f).get("channels", [])
    return next((channel for channel in channels if channel.get("id") == channel_id), None)


def estimate_narration_budget(target_seconds, channel, episode=None, pipeline=None):
    """Estimate speech units only from a matching provisional voice sample."""
    from cache_keys import file_fingerprint, stable_hash

    channel = channel or {}
    calibration = channel.get("narration_calibration") or {}
    episode = episode or {}
    try:
        rate = float(calibration.get("units_per_minute", 0))
        seconds = float(target_seconds)
        tempo = float(calibration.get("post_tts_tempo", 1.0))
        if not all(math.isfinite(n) and n > 0 for n in (rate, seconds, tempo)) or tempo != 1.0:
            return None
        if calibration.get("voice_id") and calibration["voice_id"] != channel.get("voice"):
            return None
        if calibration.get("language") and calibration["language"] != channel.get("language"):
            return None
        voice = episode.get("voice") or {}
        if not isinstance(voice, dict):
            return None
        if voice.get("voice_id") and voice["voice_id"] != channel.get("voice"):
            return None
        engine = channel.get("voice_engine")
        if calibration.get("engine") and calibration["engine"] != engine:
            return None
        if episode.get("voice_engine") and episode["voice_engine"] != engine:
            return None
        source_keys = {"audio": "reference_audio", "transcript": "reference_transcript",
                       "prompt": "clone_prompt", "vieneu_voice": "vieneu_voice"}
        for key, expected_hash in calibration.get("voice_source_sha256", {}).items():
            path = (channel.get("voice_reference") or {}).get(key)
            override = voice.get(source_keys[key])
            if override and os.path.normcase(os.path.abspath(override)) != os.path.normcase(os.path.abspath(path or "")):
                return None
            if file_fingerprint(path, include_content=True).get("sha256") != expected_hash:
                return None
        if pipeline is not None:
            cfg = pipeline.get("vieneu" if engine == "vieneu-v3-turbo" else "omnivoice") or {}
            recorded_config = calibration.get("engine_config_sha256")
            if recorded_config and recorded_config != stable_hash(cfg):
                return None
            if float(episode.get("tts_speed", cfg.get("default_speed", 1.0))) != float(calibration.get("tts_speed", cfg.get("default_speed", 1.0))):
                return None
            if float(episode.get("tts_pause_after_period_seconds", cfg.get("pause_after_period_seconds", 0))) != float(calibration.get("pause_after_period_seconds", cfg.get("pause_after_period_seconds", 0))):
                return None
            if engine == "omnivoice" and int(episode.get("tts_num_step", cfg.get("num_step", 32))) != int(calibration.get("num_step", cfg.get("num_step", 32))):
                return None
    except (TypeError, ValueError, OSError):
        return None
    method = calibration.get("count_method", "whitespace_units")
    if method not in ("whitespace_units", "non_whitespace_characters"):
        return None
    return {
        "method": "character_estimate" if method == "non_whitespace_characters" else "whitespace_unit_estimate",
        "count_method": method,
        "unit": calibration.get("unit", "space-delimited speech units"),
        "target_units": round(rate * seconds / 60),
        "calibrated_units_per_minute": rate,
        "sample_episode": calibration.get("sample_episode", ""),
        "sample_units": calibration.get("sample_units"),
        "sample_speech_seconds": calibration.get("sample_speech_seconds"),
        "post_tts_tempo": tempo,
        "calibration_settings_status": calibration.get("settings_status", ""),
        "status": "provisional first-draft budget from one episode; confirm approved native-speed TTS",
    }


def plan_visuals(fmt):
    """Set shot-duration bounds without fixing a shot count before narration approval."""
    shortest = int(fmt.get("scene_seconds_min", 3))
    cap = int(fmt.get("scene_seconds_max", 10))
    typical = int(fmt.get("scene_seconds_typical", 5))
    if shortest < 1 or not shortest <= typical <= cap:
        raise SystemExit(
            f"Invalid shot-duration settings: min={shortest}, typical={typical}, max={cap}."
        )
    return {
        "shot_seconds_min": shortest,
        "shot_seconds_typical": typical,
        "shot_seconds_max": cap,
        "planning_note": (
            "Shot count follows the approved narration and visual plan. Reuse related "
            "previously created full-frame stills with reuse_image_from and reuse_reason; "
            "no cropping or enlargement to make extra shots. Generate a new image for "
            "changed actions, expressions, settings or visible facts. Each shot lasts "
            f"{shortest} to {cap} seconds; FFmpeg adds camera movement and transitions. Sum shot durations "
            "to the target runtime."
        ),
    }


def resolve_seconds(minutes, pipeline, profile="main"):
    formats = pipeline.get("formats") or {}
    if profile not in formats:
        raise SystemExit(f"Unknown runtime profile {profile!r}; choose one of: {', '.join(formats)}.")
    fmt = formats[profile]
    low, high = int(fmt["target_seconds_min"]), int(fmt["target_seconds_max"])
    if minutes is None:
        seconds = int(fmt.get("target_seconds_default", 900))
    else:
        seconds = int(round(float(minutes) * 60))
    if seconds < low or seconds > high:
        raise SystemExit(
            f"{seconds}s is outside {low // 60}-{high // 60} minutes ({low}-{high}s)."
        )
    return seconds, low, high


def count_shots(doc, minimum, maximum):
    total_dur = 0.0
    count = 0
    problems = []
    for beat in doc.get("beats") or []:
        shots = beat.get("shots") or [beat]
        for shot in shots:
            if shot.get("kind") == "host":
                continue
            count += 1
            if shot.get("dur") is None:
                problems.append("missing dur")
                continue
            dur = float(shot["dur"])
            total_dur += dur
            if dur < minimum or dur > maximum:
                problems.append(dur)
    return count, total_dur, problems


def run(project_dir, minutes=None, profile="main"):
    refuse_out_dir(project_dir)
    path = os.path.join(project_dir, "beats.json")
    with open(path, encoding="utf-8-sig") as f:
        doc = json.load(f)
    if not doc.get("channel_id"):
        raise SystemExit("Bind a channel before planning runtime.")
    pipeline = load_pipeline()
    seconds, low, high = resolve_seconds(minutes, pipeline, profile)
    fmt = pipeline["formats"][profile]
    visual = plan_visuals(fmt)
    channel = load_channel(doc["channel_id"])
    narration_budget = estimate_narration_budget(seconds, channel, doc, pipeline)
    if narration_budget:
        doc["narration_budget"] = narration_budget
    else:
        doc.pop("narration_budget", None)
    tolerance = float(fmt.get("target_runtime_tolerance_percent", 5))
    doc["aspect"] = fmt["aspect_ratio"]
    doc.setdefault("visual_mode", "revideo_stills")
    doc["format"] = {
        "profile": profile,
        "aspect_ratio": fmt["aspect_ratio"],
        "width": fmt["width"],
        "height": fmt["height"],
        "fps": fmt["fps"],
        "target_seconds": seconds,
        "target_minutes": round(seconds / 60, 2),
        "target_seconds_min": low,
        "target_seconds_max": high,
        "scene_seconds_min": visual["shot_seconds_min"],
        "scene_seconds_max": visual["shot_seconds_max"],
        "scene_seconds_typical": visual["shot_seconds_typical"],
        "target_runtime_tolerance_percent": tolerance,
    }
    doc["visual_plan"] = visual
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    have, total_dur, problems = count_shots(
        doc, visual["shot_seconds_min"], visual["shot_seconds_max"])
    print(f"Runtime {seconds // 60}:{seconds % 60:02d} ({seconds}s) inside {low // 60}-{high // 60} min")
    print(f"Shot duration range: {visual['shot_seconds_min']}-{visual['shot_seconds_max']}s.")
    print("Set the number of shots from the approved narration and visual plan.")
    print(f"Set each shot duration within that range so the sum is {seconds}s.")
    if narration_budget:
        print(
            f"Draft narration budget: about {narration_budget['target_units']:,} "
            f"{narration_budget['unit']} at the measured "
            f"{narration_budget['calibrated_units_per_minute']:.2f}/min rate. "
            "This is a provisional draft estimate; measure approved native-speed TTS before image production."
        )
    else:
        print("No matching measured voice/settings calibration; use approved native-speed TTS to measure runtime.")
    if have:
        print(f"beats.json currently has {have} shots totaling {total_dur:.0f}s.")
    if problems:
        print(
            f"{len(problems)} shots are missing dur or are outside "
            f"{visual['shot_seconds_min']}-{visual['shot_seconds_max']}s."
        )
    print(f"updated {path}")
    return visual


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python plan_runtime.py <episode_dir> [--profile main|main_short] [--minutes N]")
    episode = os.path.abspath(sys.argv[1])
    minutes = None
    profile = "main"
    if "--minutes" in sys.argv:
        minutes = sys.argv[sys.argv.index("--minutes") + 1]
    if "--profile" in sys.argv:
        profile = sys.argv[sys.argv.index("--profile") + 1]
    run(episode, minutes, profile)
