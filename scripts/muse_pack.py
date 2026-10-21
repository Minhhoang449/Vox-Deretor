#!/usr/bin/env python3
"""
Export a subject-led Muse text-to-video package with optional cast references.

This script creates prompt and metadata files only. Muse creates the character
reference sheets, shot scenes, and video clips in its own workspace. Numbered
clip names retain the beat key internally for registration after generation:

  python muse_pack.py <project_dir> --register

Usage: python muse_pack.py <project_dir> [--characters-only]
"""
import json
import os
import re
import shutil
import sys

from animation_prompts import (
    ANIMATION_STYLES,
    CHIBI_FRAME_GUARD,
    DEFAULT_ANIMATION_STYLE,
    HISTORICAL_CONTEXT_GUARD,
    SCENARIO_CONTEXT_GUARD,
    compose_animation_motion_prompt,
    visible_character_ids,
    resolve_people_policy,
)
from codex_prompts import load, save, shots_of
from local_guard import configure_console


def ordered_shots(doc):
    """Yield non-host shots in narration order with a stable one-based number."""
    order = 0
    for beat in doc["beats"]:
        for shot, key in shots_of(beat):
            if shot.get("kind") == "host":
                continue
            order += 1
            yield order, beat, shot, key


def _slug(value):
    value = str(value or "character").strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "-", value).strip("-_")
    return value or "character"


def character_entries(doc):
    bible = doc.get("visual_bible") or {}
    if not isinstance(bible, dict):
        return []
    return [item for item in bible.get("characters", []) if isinstance(item, dict)]


def character_design_prompt(doc, character):
    style_name = doc.get("animation_style") or DEFAULT_ANIMATION_STYLE
    style = ANIMATION_STYLES.get(style_name, style_name)
    excluded = {"reference_image", "reference_images", "muse_reference_id", "id", "spec_path"}
    details = {key: value for key, value in character.items() if key not in excluded and value not in (None, "", [], {})}
    spec = json.dumps(details, ensure_ascii=False, indent=2)
    return "\n\n".join([
        f"Create one reusable character reference sheet for an original animated mission explainer in this style: {style}.",
        f"CHARACTER ID: {character.get('id')}.",
        f"APPROVED CHARACTER SPECIFICATION:\n{spec}",
        "Show the same character in a clean turnaround sheet: full-body front, three-quarter, profile, and back views, plus three small readable expressions. Keep the face, head-to-body ratio, hair, clothing, palette, and props identical in every view. Use one plain neutral background. No text, labels, extra people, scene collage, or decorative layout.",
        "This is a design reference, not an archival image or evidence. For a documented historical person, use only established visual details and leave uncertain details understated. For a reconstruction or hypothetical character, keep that status clear in the design and do not present it as a real witness.",
        CHIBI_FRAME_GUARD,
        HISTORICAL_CONTEXT_GUARD,
        SCENARIO_CONTEXT_GUARD,
    ])


def _character_reference(project_dir, character):
    character_id = str(character.get("id") or "").strip()
    display_name = str(character.get("display_name") or character_id).strip()
    asset_id = str(character.get("muse_reference_id") or "").strip()
    reference_image = str(character.get("reference_image") or "").strip()
    resolved = None
    if reference_image:
        resolved = reference_image if os.path.isabs(reference_image) else os.path.join(project_dir, reference_image)
    available = bool(asset_id or (resolved and os.path.isfile(resolved)))
    return {
        "id": character_id,
        "display_name": display_name,
        "muse_reference_id": asset_id,
        "reference_image": reference_image,
        "reference_image_available": bool(resolved and os.path.isfile(resolved)),
        "available": available,
    }


def write_character_prompts(project_dir, doc):
    characters = character_entries(doc)
    if not characters:
        raise SystemExit("Add at least one character to visual_bible.characters before the Muse character stage.")
    muse_root = os.path.join(project_dir, "muse", "characters")
    os.makedirs(muse_root, exist_ok=True)
    rows = []
    seen = set()
    for index, character in enumerate(characters, 1):
        character_id = str(character.get("id") or "").strip()
        if not character_id:
            raise SystemExit(f"visual_bible.characters[{index - 1}] needs a stable id.")
        key = _slug(character_id)
        if key in seen:
            raise SystemExit(f"Character ids must be unique after slugging: {character_id}")
        seen.add(key)
        folder = os.path.join(muse_root, key)
        os.makedirs(folder, exist_ok=True)
        prompt_path = os.path.join(folder, "design_prompt.txt")
        with open(prompt_path, "w", encoding="utf-8") as handle:
            handle.write(character_design_prompt(doc, character).strip() + "\n")
        if not character.get("reference_image"):
            character["reference_image"] = os.path.join("characters", key, "reference.png").replace("\\", "/")
        row = {
            "id": character_id,
            "display_name": character.get("display_name") or character_id,
            "prompt_file": os.path.relpath(prompt_path, project_dir).replace("\\", "/"),
            "save_reference_as": character["reference_image"],
            "muse_reference_id": character.get("muse_reference_id", ""),
        }
        with open(os.path.join(folder, "meta.json"), "w", encoding="utf-8") as handle:
            json.dump(row, handle, ensure_ascii=False, indent=2)
        rows.append(row)
    index_path = os.path.join(muse_root, "INDEX.md")
    lines = [
        "# Muse character setup",
        "",
        "Do this stage before exporting or generating any shot videos. Review the approved character specification, then run each design prompt in Muse and approve the resulting reference sheet.",
        "Save each accepted sheet at `save_reference_as`, or record its reusable Muse asset ID as `muse_reference_id` in `beats.json`.",
        "",
        "| Character | Prompt | Save reference | Muse asset ID |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['display_name']} | `{row['prompt_file']}` | `{row['save_reference_as']}` | `{row['muse_reference_id'] or 'add after generation'}` |"
        )
    with open(index_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return rows, index_path


def _shot_character_entries(doc, shot):
    characters = character_entries(doc)
    raw = shot.get("characters") or []
    if isinstance(raw, str):
        raw = [raw]
    wanted = {str(value) for value in raw}
    selected = [item for item in characters if str(item.get("id")) in wanted]
    known = {str(item.get("id")) for item in characters}
    unknown = sorted(wanted - known)
    if unknown:
        raise SystemExit(f"Shot references unknown character ids: {', '.join(unknown)}")
    return selected


def export(project_dir, characters_only=False):
    bpath, doc = load(project_dir)
    doc.setdefault("animation_style", DEFAULT_ANIMATION_STYLE)
    if doc.get("animation_style") != DEFAULT_ANIMATION_STYLE:
        raise SystemExit("Muse character and shot prompts currently require animation_style: chibi-2d.")
    aspect = doc.get("aspect", "16:9")
    fmt = doc.get("format") or {}
    minimum = int(fmt.get("scene_seconds_min", 3))
    maximum = int(fmt.get("scene_seconds_max", 10))
    muse_root = os.path.join(project_dir, "muse")
    os.makedirs(muse_root, exist_ok=True)

    if characters_only:
        character_rows, character_index = write_character_prompts(project_dir, doc)
        save(bpath, doc)
        print("wrote", character_index)
        print("Generate and approve these character references in Muse before exporting shot prompts.")
        return

    visible_ids = set().union(*(visible_character_ids(shot) for _, _, shot, _ in ordered_shots(doc)))
    characters = [item for item in character_entries(doc) if str(item.get("id")) in visible_ids]
    if characters:
        reference_doc = dict(doc, visual_bible=dict(doc.get("visual_bible") or {}, characters=characters))
        write_character_prompts(project_dir, reference_doc)
    save(bpath, doc)
    missing_refs = [
        str(item.get("id")) for item in characters
        if not _character_reference(project_dir, item)["available"]
    ]
    if missing_refs:
        missing_text = ", ".join(missing_refs)
        raise SystemExit(
            f"Muse character reference(s) missing: {missing_text}. Generate them first with "
            "--characters-only, save each approved sheet at its reference_image path, or set muse_reference_id."
        )

    rows = []
    for order, beat, shot, key in ordered_shots(doc):
        order_id = f"{order:03d}"
        anim = shot.get("animation") if isinstance(shot.get("animation"), dict) else {}
        missing_motion = [name for name in ("start", "action", "end") if not str(anim.get(name) or "").strip()]
        if missing_motion:
            raise SystemExit(f"[{order_id}] add animation.{missing_motion[0]} before generating the Muse prompt.")
        shot_characters = _shot_character_entries(doc, shot)
        resolve_people_policy(shot)
        prompt_doc = dict(doc)
        prompt_bible = dict(doc.get("visual_bible") or {})
        prompt_bible["characters"] = shot_characters
        prompt_doc["visual_bible"] = prompt_bible
        prompt = compose_animation_motion_prompt(prompt_doc, beat, shot)
        if shot.get("dur") is None:
            raise SystemExit(
                f"[{order_id}] needs dur. Set each Muse shot between {minimum} and {maximum} seconds."
            )
        dur = float(shot["dur"])
        if dur < minimum or dur > maximum:
            raise SystemExit(
                f"[{order_id}] dur is {dur}s. Set it between {minimum} and {maximum}."
            )
        prompt = (
            f"{prompt.strip()}\n\n"
            f"VIDEO DURATION: exactly {dur:.2f} seconds total. "
            f"Render one clip at this duration; do not exceed {maximum} seconds, "
            "extend, pad, or loop to a default duration."
        )
        shot["motion_prompt"] = prompt
        shot["muse_prompt_file"] = os.path.join("muse", order_id, "prompt.txt").replace("\\", "/")
        slot = os.path.join(muse_root, order_id)
        os.makedirs(slot, exist_ok=True)
        with open(os.path.join(slot, "prompt.txt"), "w", encoding="utf-8") as f:
            f.write(prompt.strip() + "\n")
        reference_rows = [_character_reference(project_dir, item) for item in shot_characters]
        beat_title = beat.get("title_en") or f"Beat {beat['id']}"
        meta = {
            "order": order,
            "key": key,
            "beat_id": beat["id"],
            "beat_title": beat_title,
            "duration_sec": dur,
            "aspect": aspect,
            "generation_mode": "text_to_video_with_character_references" if shot_characters else "text_to_video",
            "character_references": reference_rows,
            "save_clip_as": os.path.join("clips", f"clip_{order_id}.mp4").replace("\\", "/"),
            "narration": beat.get("narration", ""),
        }
        with open(os.path.join(slot, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        rows.append(meta)
        print(f"[{order_id}] Muse text-to-video prompt  {dur}s")

    lines = [
        "# Muse — Chibi scene and video generation",
        "",
        "Complete and approve `muse/characters/INDEX.md` first. Each shot folder then contains text instructions and metadata only; no scene still is generated or required in this repository.",
        "",
        "Use Muse's text-to-video or reference-to-video mode that accepts character reference assets. Attach only the approved character reference(s) listed in each `meta.json`; do not attach a scene keyframe. Muse creates the scene image and its motion from the prompt.",
        "",
        "Each prompt directs a subject-led continuous Chibi/Q-Version 2D scene: an action, process, explanation or readable hold, with appropriate camera and exact duration. Character references are required only for visible recurring cast. The exporter does not call a Muse API or inspect generated media.",
        "",
        "1. Only for recurring characters visible in the planned shots, create the approved reference(s) from `muse/characters/`. Environment or mechanism-only scenes need no character stage.",
        "2. Save each reference at the listed `reference_image` path or record a reusable `muse_reference_id` in `beats.json`.",
        "3. Run `python scripts/muse_pack.py <episode>` to export shot prompts. Generate each video with the listed character reference(s), then save it as the numbered `clips/clip_###.mp4` path.",
        "4. Run `python scripts/muse_pack.py <episode> --register`, then create narration and assemble with the local TTS and FFmpeg steps.",
        "",
        "| Shot | Beat | Seconds | Character references | Prompt | Save clip as |",
        "|---|---:|---|---|---|---|",
    ]
    for row in rows:
        refs = ", ".join(item["display_name"] for item in row["character_references"]) or "—"
        lines.append(
            f"| {row['order']:03d} | {row['beat_title']} | {row['duration_sec']} "
            f"| {refs} | `muse/{row['order']:03d}/prompt.txt` | `{row['save_clip_as']}` |"
        )
    index = os.path.join(muse_root, "INDEX.md")
    with open(index, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    save(bpath, doc)
    print("wrote", index)


def register(project_dir):
    bpath, doc = load(project_dir)
    clip_dir = os.path.join(project_dir, "clips")
    muse_root = os.path.join(project_dir, "muse")
    os.makedirs(clip_dir, exist_ok=True)
    missing = []
    for order, beat, shot, key in ordered_shots(doc):
        order_id = f"{order:03d}"
        candidates = [
            os.path.join(clip_dir, f"clip_{order_id}.mp4"),
            os.path.join(muse_root, order_id, "clip.mp4"),
            os.path.join(muse_root, order_id, f"{beat['id']}.mp4"),
            # Accept clips exported with the earlier beat-letter naming scheme.
            os.path.join(clip_dir, f"clip_{key}.mp4"),
            os.path.join(muse_root, key, "clip.mp4"),
            os.path.join(muse_root, key, f"{beat['id']}.mp4"),
        ]
        found = next((p for p in candidates if os.path.exists(p)), None)
        if not found:
            missing.append(order_id)
            print(f"[{order_id}] missing clips/clip_{order_id}.mp4")
            continue
        dest = os.path.join(clip_dir, f"clip_{order_id}.mp4")
        if os.path.abspath(found) != os.path.abspath(dest):
            shutil.copy2(found, dest)
        found = dest
        shot["clip_path"] = found
        shot.pop("clip_url", None)
        print(f"[{order_id}] {found}")
    save(bpath, doc)
    if missing:
        raise SystemExit(f"{len(missing)} clips still missing: {', '.join(missing)}")
    print("registered clips")


if __name__ == "__main__":
    configure_console()
    if len(sys.argv) < 2:
        raise SystemExit("usage: python muse_pack.py <episode_dir> [--characters-only | --prompts-only | --register]")
    proj = os.path.abspath(sys.argv[1])
    option = sys.argv[2] if len(sys.argv) > 2 else ""
    if option == "--register":
        register(proj)
    elif option in ("", "--prompts-only"):
        export(proj)
    elif option == "--characters-only":
        export(proj, characters_only=True)
    else:
        raise SystemExit(f"Unknown option {option}. Use --characters-only, --prompts-only, or --register.")
