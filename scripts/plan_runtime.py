#!/usr/bin/env python3
"""
Plan a 7–20 minute film whose Muse clips are at most 10 seconds each.

Duration is per shot, as in clips.py: the API received shot.dur and did not
force every scene to one length. Muse can generate at most 10 seconds, so a
shot that needs longer is split. This script only writes the budget.

  python scripts/plan_runtime.py <episode_dir> --minutes 12
"""
import json
import os
import sys

from local_guard import refuse_out_dir

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PIPELINE_FILE = os.path.join(ROOT, "config", "pipeline.json")


def load_pipeline():
    with open(PIPELINE_FILE, encoding="utf-8-sig") as f:
        return json.load(f)


def plan_visuals(target_seconds, muse):
    """Budget for variable-length shots under a 10-second Muse cap.

    The fewest clips is the runtime divided by 10, because nothing can be
    longer than that. The working count assumes a cut about every 5 seconds,
    matching the original shot pacing. Codex then sets each shot's own dur
    between 3 and 10 seconds so the sum meets the target.
    """
    cap = int(muse.get("generation_seconds") or 10)
    shortest = 3
    typical = 5
    fewest = (target_seconds + cap - 1) // cap
    guide = max(1, round(target_seconds / typical))
    return {
        "muse_max_seconds": cap,
        "shot_seconds_min": shortest,
        "shot_seconds_typical": typical,
        "shot_seconds_max": cap,
        "fewest_clips": fewest,
        "prompts_to_write": guide,
        "planning_note": (
            "Write about this many shots. Give each shot its own dur from "
            f"{shortest} to {cap} seconds, the way the API used shot.dur. "
            "Do not set every shot to 10. The durations must add up to the target."
        ),
    }


def resolve_seconds(minutes, pipeline):
    fmt = pipeline["formats"]["main"]
    low, high = int(fmt["target_seconds_min"]), int(fmt["target_seconds_max"])
    if minutes is None:
        seconds = int(fmt.get("target_seconds_default", 600))
    else:
        seconds = int(round(float(minutes) * 60))
    if seconds < low or seconds > high:
        raise SystemExit(
            f"{seconds}s is outside {low // 60}-{high // 60} minutes ({low}-{high}s)."
        )
    return seconds, low, high


def count_shots(doc):
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
            if dur < 3 or dur > 10:
                problems.append(dur)
    return count, total_dur, problems


def run(project_dir, minutes=None):
    refuse_out_dir(project_dir)
    path = os.path.join(project_dir, "beats.json")
    with open(path, encoding="utf-8-sig") as f:
        doc = json.load(f)
    if not doc.get("channel_id"):
        raise SystemExit("Bind a channel before planning runtime.")
    pipeline = load_pipeline()
    seconds, low, high = resolve_seconds(minutes, pipeline)
    visual = plan_visuals(seconds, pipeline["muse"])
    fmt = pipeline["formats"]["main"]
    doc["aspect"] = fmt["aspect_ratio"]
    doc["format"] = {
        "profile": "main",
        "aspect_ratio": fmt["aspect_ratio"],
        "width": fmt["width"],
        "height": fmt["height"],
        "fps": fmt["fps"],
        "target_seconds": seconds,
        "target_minutes": round(seconds / 60, 2),
        "target_seconds_min": low,
        "target_seconds_max": high,
    }
    doc["visual_plan"] = visual
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    have, total_dur, problems = count_shots(doc)
    print(f"Runtime {seconds // 60}:{seconds % 60:02d} ({seconds}s) inside {low // 60}-{high // 60} min")
    print(f"Muse cap: {visual['muse_max_seconds']}s per clip. Each shot keeps its own dur.")
    print(f"Fewest clips, if every shot used the full {visual['muse_max_seconds']}s: {visual['fewest_clips']}")
    print(f"Working count at ~{visual['shot_seconds_typical']}s per shot: {visual['prompts_to_write']} stills + {visual['prompts_to_write']} motion prompts")
    print(f"Set each dur from {visual['shot_seconds_min']} to {visual['shot_seconds_max']} so the sum is {seconds}s.")
    if have:
        print(f"beats.json currently has {have} shots totaling {total_dur:.0f}s.")
    if problems:
        print(f"{len(problems)} shots are missing dur or are outside 3-10s.")
    print(f"updated {path}")
    return visual


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python plan_runtime.py <episode_dir> [--minutes 7-20]")
    episode = os.path.abspath(sys.argv[1])
    minutes = None
    if "--minutes" in sys.argv:
        minutes = sys.argv[sys.argv.index("--minutes") + 1]
    run(episode, minutes)
