#!/usr/bin/env python3
"""
Write collage still prompts for Codex to render. No image API.

Codex reads each prompt, generates the image, and saves it at the path in
the manifest. Then:

  python codex_prompts.py <project_dir> --register

Bake-off (one beat, several themes) before the full set:

  python codex_prompts.py <project_dir> --bakeoff american-retro,swiss-modern,punk-zine

Usage: python codex_prompts.py <project_dir>
"""
import json
import os
import sys

from local_guard import refuse_out_dir
from styles import compose_collage_prompt, compose_keyframe_prompt, resolve_theme

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
HEADLINE_LANGUAGE = {
    "vi": "Vietnamese",
    "es": "Spanish",
    "ja": "Japanese",
    "ko": "Korean",
}


def require_channel(doc):
    if not doc.get("channel_id"):
        raise SystemExit(
            "No channel bound. Run: python scripts/channels.py bind <channel-id> <slug>"
        )


def require_research(project_dir):
    folder = os.path.join(project_dir, "research")
    found = []
    if os.path.isdir(folder):
        found = [
            name for name in os.listdir(folder)
            if name.startswith("youtube-market-scan-") and name.endswith(".md")
        ]
    if not found:
        raise SystemExit(
            "No YouTube research in this episode yet.\n"
            "Run: python scripts/research_youtube.py --channel <id> "
            "--query \"<the episode question>\" --tag <slug> "
            "--output-dir \"<episode>\\research\"\n"
            "Read that report, then write the beat map. See references/topic-research.md."
        )


def shots_of(beat):
    if beat.get("shots"):
        for shot in beat["shots"]:
            yield shot, f"{beat['id']}{shot.get('id', '')}"
    else:
        yield beat, f"{beat['id']}"


def load(project_dir):
    refuse_out_dir(project_dir)
    path = os.path.join(project_dir, "beats.json")
    with open(path, encoding="utf-8-sig") as f:
        return path, json.load(f)


def save(path, doc):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)


def image_prompt(doc, beat, shot):
    aspect = doc.get("aspect", "16:9")
    style = doc.get("style", "collage")
    theme = resolve_theme(doc.get("theme")) or {}
    collage_style = theme.get("idiom") or doc.get("collage_style", "american-retro")
    palette = theme.get("palette") or doc.get("palette")
    type_style = theme.get("type_style") or doc.get("type_style")
    finish = theme.get("finish") or doc.get("finish")
    scene = shot["scene"]
    if style == "collage":
        return compose_collage_prompt(
            scene, beat.get("title_cn", ""), beat.get("title_en", ""),
            beat.get("bg", "warm ochre"), aspect,
            with_title=shot.get("title", True),
            style=collage_style, palette=palette,
            type_style=type_style, finish=finish,
            headline_language=HEADLINE_LANGUAGE.get(doc.get("language")))
    return compose_keyframe_prompt(
        doc.get("era", "tang"), scene, beat.get("title_cn", ""),
        beat.get("title_en", ""), aspect)


def find_image(folder, stem):
    for ext in IMAGE_EXTS:
        path = os.path.join(folder, stem + ext)
        if os.path.exists(path):
            return path
    return None


def write_prompts(project_dir):
    bpath, doc = load(project_dir)
    require_channel(doc)
    require_research(project_dir)
    plan = doc.get("visual_plan") or {}
    target_seconds = (doc.get("format") or {}).get("target_seconds")
    if not plan or not target_seconds:
        raise SystemExit(
            "No runtime plan. Run: python scripts/plan_runtime.py <episode> --minutes 7-20"
        )
    shot_rows = []
    for beat in doc["beats"]:
        for shot, key in shots_of(beat):
            if shot.get("kind") == "host":
                continue
            shot_rows.append((key, shot))
    if not shot_rows:
        raise SystemExit("beats.json has no shots. Write the beat map before generating stills.")
    total = 0.0
    for key, shot in shot_rows:
        if shot.get("dur") is None:
            raise SystemExit(f"[{key}] needs dur. Each shot is 3-10 seconds, not a fixed 10.")
        dur = float(shot["dur"])
        if dur < 3 or dur > 10:
            raise SystemExit(
                f"[{key}] dur is {dur}s. Muse accepts that shot's own duration up to 10 seconds."
            )
        total += dur
    slack = max(15, float(target_seconds) * 0.05)
    if abs(total - float(target_seconds)) > slack:
        raise SystemExit(
            f"Shot durations sum to {total:.0f}s; the film target is {target_seconds}s. "
            "Change individual dur values between 3 and 10 seconds."
        )
    doc["pipeline"] = "local"
    aspect = doc.get("aspect", "16:9")
    kf_dir = os.path.join(project_dir, "keyframes")
    prompt_dir = os.path.join(project_dir, "codex")
    os.makedirs(kf_dir, exist_ok=True)
    os.makedirs(prompt_dir, exist_ok=True)

    jobs = []
    for beat in doc["beats"]:
        for shot, key in shots_of(beat):
            if shot.get("kind") == "host":
                continue
            prompt = image_prompt(doc, beat, shot)
            shot["keyframe_prompt"] = prompt
            prompt_file = os.path.join(prompt_dir, f"kf_{key}.txt")
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(prompt.strip() + "\n")
            save_as = os.path.join(kf_dir, f"kf_{key}.png")
            existing = find_image(kf_dir, f"kf_{key}")
            jobs.append({
                "key": key,
                "beat_id": beat["id"],
                "aspect": aspect,
                "prompt_file": os.path.relpath(prompt_file, project_dir),
                "save_as": os.path.relpath(save_as, project_dir),
                "status": "ready" if existing else "needs_image",
            })
            print(f"[{key}] {jobs[-1]['status']}  {jobs[-1]['prompt_file']}")

    manifest = {
        "aspect": aspect,
        "note": "Generate each still with Codex from prompt_file. Save the image at save_as, then run: python scripts/codex_prompts.py <project> --register",
        "shots": jobs,
    }
    man_path = os.path.join(prompt_dir, "manifest.json")
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    save(bpath, doc)
    pending = sum(1 for j in jobs if j["status"] != "ready")
    print(f"wrote {man_path}  ({pending} stills left for Codex, {total:.0f}s of shots)")
    return pending


def write_bakeoff(project_dir, styles, beat_index=0):
    bpath, doc = load(project_dir)
    require_channel(doc)
    require_research(project_dir)
    doc["pipeline"] = "local"
    aspect = doc.get("aspect", "16:9")
    beat = doc["beats"][beat_index]
    shot = beat["shots"][0] if beat.get("shots") else beat
    out = os.path.join(project_dir, "style-bakeoff")
    prompt_dir = os.path.join(out, "prompts")
    os.makedirs(prompt_dir, exist_ok=True)
    jobs = []
    for name in styles:
        theme = resolve_theme(name) or {}
        prompt = compose_collage_prompt(
            shot["scene"], beat.get("title_cn", ""), beat.get("title_en", ""),
            beat.get("bg", "warm ochre"), aspect,
            with_title=shot.get("title", True),
            style=theme.get("idiom", name), palette=theme.get("palette"),
            type_style=theme.get("type_style"), finish=theme.get("finish"),
            headline_language=HEADLINE_LANGUAGE.get(doc.get("language")))
        prompt_file = os.path.join(prompt_dir, f"{name}.txt")
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt.strip() + "\n")
        save_as = os.path.join(out, f"{name}.png")
        existing = find_image(out, name)
        jobs.append({
            "theme": name,
            "aspect": aspect,
            "prompt_file": os.path.relpath(prompt_file, project_dir),
            "save_as": os.path.relpath(save_as, project_dir),
            "status": "ready" if existing else "needs_image",
        })
        print(f"[bakeoff {name}] {jobs[-1]['status']}")
    man_path = os.path.join(out, "manifest.json")
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump({"beat_index": beat_index, "aspect": aspect, "themes": jobs}, f,
                  ensure_ascii=False, indent=2)
    save(bpath, doc)
    print(f"wrote {man_path}")
    print("Codex renders each theme, you pick one, then set \"theme\" in beats.json.")


def register(project_dir):
    bpath, doc = load(project_dir)
    kf_dir = os.path.join(project_dir, "keyframes")
    missing = []
    for beat in doc["beats"]:
        for shot, key in shots_of(beat):
            if shot.get("kind") == "host":
                continue
            found = find_image(kf_dir, f"kf_{key}")
            if not found:
                missing.append(key)
                print(f"[{key}] missing keyframes/kf_{key}.png")
                continue
            shot["keyframe_path"] = found
            shot.pop("keyframe_url", None)
            print(f"[{key}] {found}")
    save(bpath, doc)
    if missing:
        raise SystemExit(f"{len(missing)} stills still missing: {', '.join(missing)}")
    print("registered keyframes")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python codex_prompts.py <project_dir> [--register | --bakeoff a,b,c [beat_index]]")
    proj = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2] == "--register":
        register(proj)
    elif len(sys.argv) > 2 and sys.argv[2] == "--bakeoff":
        if len(sys.argv) < 4:
            raise SystemExit("usage: python codex_prompts.py <project_dir> --bakeoff theme1,theme2 [beat_index]")
        bi = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        write_bakeoff(proj, [s.strip() for s in sys.argv[3].split(",") if s.strip()], bi)
    else:
        write_prompts(proj)
