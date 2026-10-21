#!/usr/bin/env python3
"""
Write Chibi 2D educational-still prompts for an approved episode. The selected channel's configured visual style is compiled into each prompt. This script does not call an image API; use Codex imagegen with the exported manifest.

Use Codex imagegen for original assets needing images in the current manifest. New episodes do not retrieve or use video footage.
Related shots reuse the same full image without a new prompt or crop. Attach
listed character references and save at the manifest path. Then:

  python codex_prompts.py <project_dir> --register

Optional style comparison for a missing still (legacy styles remain available):

  python codex_prompts.py <project_dir> --bakeoff documentary-realistic,graphic-2d

Usage: python codex_prompts.py <project_dir>
"""
import json
import os
import sys
from datetime import datetime, timezone

from local_guard import configure_console, refuse_out_dir
from research_youtube import normalize_tag
from animation_prompts import (
    ANIMATION_STYLES,
    DEFAULT_ANIMATION_STYLE,
    compose_animation_frame_prompt,
    compose_in_scene_text_prompt,
    default_image_text_policy,
    resolve_people_policy,
    visible_character_ids,
)
from cache_keys import stable_hash
from image_reuse import image_sources, shot_rows as iter_shot_rows
from visual_policy import episode_style, is_video_shot
from visual_sources import validate_source_plan

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PIPELINE_FILE = os.path.join(ROOT, "config", "pipeline.json")


def require_channel(doc):
    if not doc.get("channel_id"):
        raise SystemExit(
            "No channel bound. Run: python scripts/channels.py bind <channel-id> <slug>"
        )


def require_research(project_dir, doc):
    folder = os.path.join(project_dir, "research")
    slug = doc.get("episode_slug") or doc.get("project") or os.path.basename(project_dir)
    tag = normalize_tag(slug)
    if not tag:
        raise SystemExit("This episode has no usable slug for its research report tag.")
    with open(PIPELINE_FILE, encoding="utf-8-sig") as handle:
        pipeline = json.load(handle)
    max_age_days = int((pipeline.get("research") or {}).get("youtube_market_scan_max_age_days", 90))
    now = datetime.now(timezone.utc)
    valid = []
    problems = []
    prefix = "youtube-market-scan-"
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            if not name.startswith(prefix) or not name.endswith(".md"):
                continue
            stem = name[:-3]
            dated_tag = stem[len(prefix):]
            if len(dated_tag) < 12 or dated_tag[10] != "-":
                continue
            date_text, report_tag = dated_tag[:10], dated_tag[11:]
            if report_tag != tag and not report_tag.startswith(tag + "-"):
                continue
            try:
                file_date = datetime.strptime(date_text, "%Y-%m-%d").date()
            except ValueError:
                continue
            json_path = os.path.join(folder, stem + ".json")
            try:
                with open(json_path, encoding="utf-8-sig") as handle:
                    report = json.load(handle)
                scanned_text = str(report.get("scanned_at_utc") or "")
                scanned_at = datetime.fromisoformat(scanned_text.replace("Z", "+00:00"))
                if scanned_at.tzinfo is None:
                    problems.append(f"{name}: scan timestamp has no timezone")
                    continue
                scanned_at = scanned_at.astimezone(timezone.utc)
                if scanned_at.date() != file_date:
                    problems.append(f"{name}: scan timestamp does not match its filename")
                    continue
                channels = report.get("channels") or []
                channel = next(
                    (item for item in channels if item.get("channel_id") == doc.get("channel_id")),
                    None,
                )
                if channel is None:
                    problems.append(f"{name}: report is for a different channel")
                    continue
                queries = channel.get("queries") or []
                if not any(str(item.get("query") or "").strip() for item in queries):
                    problems.append(f"{name}: report has no episode query")
                    continue
                age_days = (now - scanned_at).total_seconds() / 86400
                if age_days < 0 or age_days > max_age_days:
                    problems.append(f"{name}: report is older than {max_age_days} days or dated in the future")
                    continue
                valid.append((scanned_at, name))
            except (OSError, ValueError, TypeError, AttributeError) as exc:
                problems.append(f"{name}: cannot read matching metadata ({exc})")
    if not valid:
        detail = f" Latest issue: {problems[-1]}." if problems else ""
        raise SystemExit(
            f"No current YouTube scan tagged for episode '{tag}' and channel "
            f"'{doc.get('channel_id')}'.{detail}\n"
            "Run: python scripts/research_youtube.py --channel <id> "
            "--query \"<the episode question>\" --tag <slug> "
            "--output-dir \"<episode>\\research\"\n"
            f"The matching Markdown and JSON report must be no older than {max_age_days} days. "
            "See references/topic-research.md."
        )
    newest = max(valid, key=lambda item: item[0])[1]
    print(f"[research] accepted {newest}")


def shot_duration_bounds(doc):
    fmt = doc.get("format") or {}
    return int(fmt.get("scene_seconds_min", 3)), int(fmt.get("scene_seconds_max", 10))


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
    doc.setdefault("animation_style", episode_style(doc))
    return compose_animation_frame_prompt(doc, beat, shot)


def reference_images(doc, shot):
    """Return episode-relative image references for the shot's recurring characters."""
    explicit = shot.get("reference_images") or []
    if isinstance(explicit, str):
        explicit = [explicit]

    bible = doc.get("visual_bible") or {}
    characters = bible.get("characters") if isinstance(bible, dict) else []
    character_refs = {
        str(item.get("id")): item.get("reference_image")
        for item in (characters or [])
        if isinstance(item, dict) and item.get("id") and item.get("reference_image")
    }
    resolve_people_policy(shot)
    selected = visible_character_ids(shot)
    if selected:
        refs = [character_refs[str(name)] for name in sorted(selected) if str(name) in character_refs]
    else:
        refs = []

    result = []
    for path in [*explicit, *refs]:
        value = str(path or "").strip().replace("\\", "/")
        if value and value not in result:
            result.append(value)
    return result


def find_image(folder, stem):
    for ext in IMAGE_EXTS:
        path = os.path.join(folder, stem + ext)
        if os.path.exists(path):
            return path
    return None


def write_prompts(project_dir):
    bpath, doc = load(project_dir)
    require_channel(doc)
    require_research(project_dir, doc)
    validate_source_plan(project_dir, doc)
    plan = doc.get("visual_plan") or {}
    target_seconds = (doc.get("format") or {}).get("target_seconds")
    if not plan or not target_seconds:
        raise SystemExit(
            "No runtime plan. Run: python scripts/plan_runtime.py <episode> --minutes 14-30"
        )
    shot_rows = []
    for beat in doc["beats"]:
        for shot, key in shots_of(beat):
            if shot.get("kind") == "host":
                continue
            shot_rows.append((key, shot))
    if not shot_rows:
        raise SystemExit("beats.json has no shots. Write the beat map before generating stills.")
    minimum, maximum = shot_duration_bounds(doc)
    total = 0.0
    for key, shot in shot_rows:
        if shot.get("dur") is None:
            raise SystemExit(
                f"[{key}] needs dur. Set each shot between {minimum} and {maximum} seconds."
            )
        dur = float(shot["dur"])
        if dur < minimum or dur > maximum:
            raise SystemExit(
                f"[{key}] dur is {dur}s. Set it between {minimum} and {maximum} seconds."
            )
        total += dur
    tolerance = float((doc.get("format") or {}).get("target_runtime_tolerance_percent", 5))
    slack = max(15, float(target_seconds) * tolerance / 100)
    if abs(total - float(target_seconds)) > slack:
        raise SystemExit(
            f"Shot durations sum to {total:.0f}s; the film target is {target_seconds}s. "
            f"Change individual dur values between {minimum} and {maximum} seconds."
        )
    doc["pipeline"] = "local"
    doc.setdefault("visual_mode", "revideo_stills")
    doc.setdefault("image_text_policy", default_image_text_policy())
    sources = image_sources(doc, enforce_limits=True)
    # Only original images need generation text. Reused shots inherit baked text.
    for beat in doc["beats"]:
        for shot, key in shots_of(beat):
            if shot.get("kind") != "host" and not is_video_shot(shot) and sources[key] == key:
                compose_in_scene_text_prompt(
                    doc, dict(shot, id=shot.get("id") or key), require_text=True
                )
    aspect = doc.get("aspect", "16:9")
    kf_dir = os.path.join(project_dir, "keyframes")
    prompt_dir = os.path.join(project_dir, "imagegen")
    os.makedirs(kf_dir, exist_ok=True)
    os.makedirs(prompt_dir, exist_ok=True)

    assets = []
    for beat in doc["beats"]:
        for shot, key in shots_of(beat):
            if shot.get("kind") == "host" or is_video_shot(shot):
                continue
            if sources[key] != key:
                continue
            prompt = image_prompt(doc, beat, shot)
            shot["keyframe_prompt"] = prompt
            current_prompt_hash = stable_hash(prompt)
            shot["keyframe_prompt_current_hash"] = current_prompt_hash
            prompt_file = os.path.join(prompt_dir, f"kf_{key}.txt")
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(prompt.strip() + "\n")
            save_as = os.path.join(kf_dir, f"kf_{key}.png")
            existing = find_image(kf_dir, f"kf_{key}")
            saved_prompt_hash = shot.get("keyframe_prompt_hash")
            if not existing:
                status = "needs_image"
            elif not saved_prompt_hash:
                status = "needs_review"
            elif saved_prompt_hash != current_prompt_hash:
                status = "needs_image"
            else:
                status = "ready"
            assets.append({
                "key": key,
                "action": "generate",
                "source_key": key,
                "used_by": [item for item, source in sources.items() if source == key],
                "beat_id": beat["id"],
                "aspect": aspect,
                "reference_images": reference_images(doc, shot),
                "people_policy": resolve_people_policy(shot),
                "visual_intent": shot.get("visual_intent") or {},
                "prompt_file": os.path.relpath(prompt_file, project_dir),
                "save_as": os.path.relpath(save_as, project_dir),
                "status": status,
                "existing_image": bool(existing),
                "prompt_hash": current_prompt_hash,
            })
            note = " (image exists; prompt match unverified)" if status == "needs_review" else ""
            print(f"[{key}] {status}{note}  {assets[-1]['prompt_file']}")

    by_source = {asset["key"]: asset for asset in assets}
    jobs = []
    for beat, shot, key in iter_shot_rows(doc):
        source = by_source[sources[key]]
        if key == sources[key]:
            jobs.append(dict(source))
            continue
        shot["keyframe_prompt_current_hash"] = source["prompt_hash"]
        shot.pop("keyframe_prompt", None)
        jobs.append({
            "key": key, "beat_id": beat["id"], "aspect": aspect,
            "action": "reuse", "source_key": sources[key],
            "reuse_reason": shot["reuse_reason"],
            "prompt_file": None, "save_as": source["save_as"],
            "reference_images": [], "prompt_hash": source["prompt_hash"],
            "existing_image": source["existing_image"],
            "source_status": source["status"],
            "status": "ready" if source["status"] == "ready" else "reuse",
        })
        print(f"[{key}] reuse [{sources[key]}] (no new image)")

    manifest = {
        "aspect": aspect,
        "footage_shots": [{"key": key, "clip_path": shot.get("clip_path"),
                           "visual_source": shot.get("visual_source")}
                          for beat in doc.get("beats") or []
                          for shot, key in shots_of(beat) if is_video_shot(shot)],
        "note": "Generate/review only assets, one image per original source. Reuse no more than 35% of scene shots, and reuse any original image no more than twice after its first appearance (maximum three appearances total). Count each reuse shot and count appearances by final original source, including reuse chains. Shots with action: reuse use the same full image; do not generate, copy, crop or enlarge it for reuse. Attach reference_images when listed. Paths are relative to the episode folder. Save at save_as, inspect every use, then run --register. Existing images without a saved fingerprint need review.",
        "assets": assets,
        "image_summary": {"shots": len(jobs), "unique_images": len(assets),
                          "reused_shots": len(jobs) - len(assets)},
        "shots": jobs,
    }
    man_path = os.path.join(prompt_dir, "manifest.json")
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    save(bpath, doc)
    pending = sum(1 for j in assets if j["status"] == "needs_image")
    unverified = sum(1 for j in assets if j["status"] == "needs_review")
    print(f"wrote {man_path}  ({len(jobs)} shots, {len(assets)} unique images, "
          f"{len(jobs) - len(assets)} reused shots; {pending} stills left for imagegen, {total:.0f}s)")
    if unverified:
        print(f"{unverified} existing stills have no saved prompt fingerprint; inspect, then register them.")
    return pending


def write_bakeoff(project_dir, styles, beat_index=0):
    bpath, doc = load(project_dir)
    require_channel(doc)
    require_research(project_dir, doc)
    validate_source_plan(project_dir, doc)
    doc["pipeline"] = "local"
    beat = doc["beats"][beat_index]
    shot = next((s for s, _ in shots_of(beat) if not is_video_shot(s)), None)
    if shot is None:
        raise SystemExit("This beat is covered by footage; choose a beat needing a generated still for a style comparison.")
    compose_in_scene_text_prompt(doc, shot, require_text=True)
    out = os.path.join(project_dir, "style-bakeoff")
    prompt_dir = os.path.join(out, "prompts")
    os.makedirs(prompt_dir, exist_ok=True)
    jobs = []
    for name in styles:
        if name not in ANIMATION_STYLES:
            choices = ", ".join(ANIMATION_STYLES)
            raise SystemExit(f"Unknown animation style {name!r}. Choose from: {choices}")
        bakeoff_doc = dict(doc, animation_style=name)
        prompt = compose_animation_frame_prompt(bakeoff_doc, beat, shot)
        prompt_file = os.path.join(prompt_dir, f"{name}.txt")
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt.strip() + "\n")
        save_as = os.path.join(out, f"{name}.png")
        existing = find_image(out, name)
        jobs.append({
            "animation_style": name,
            "aspect": doc.get("aspect", "16:9"),
            "reference_images": reference_images(doc, shot),
            "prompt_file": os.path.relpath(prompt_file, project_dir),
            "save_as": os.path.relpath(save_as, project_dir),
            "status": "ready" if existing else "needs_image",
        })
        print(f"[bakeoff {name}] {jobs[-1]['status']}")
    man_path = os.path.join(out, "manifest.json")
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump({"beat_index": beat_index, "aspect": doc.get("aspect", "16:9"), "styles": jobs}, f,
                  ensure_ascii=False, indent=2)
    save(bpath, doc)
    print(f"wrote {man_path}")
    print("Use imagegen for each animation style. Pick one, then set animation_style in beats.json.")


def register(project_dir):
    bpath, doc = load(project_dir)
    validate_source_plan(project_dir, doc)
    kf_dir = os.path.join(project_dir, "keyframes")
    sources = image_sources(doc, enforce_limits=True)
    rows = list(iter_shot_rows(doc))
    shots_by_key = {key: shot for _, shot, key in rows}
    missing = []
    for _, shot, key in rows:
        if sources[key] != key:
            continue
        found = find_image(kf_dir, f"kf_{key}")
        if not found:
            shot.pop("keyframe_path", None)
            shot.pop("keyframe_prompt_hash", None)
            missing.append(key)
            print(f"[{key}] missing keyframes/kf_{key}.png")
            continue
        shot["keyframe_path"] = found
        shot.pop("keyframe_url", None)
        current_hash = shot.get("keyframe_prompt_current_hash")
        if current_hash:
            shot["keyframe_prompt_hash"] = current_hash
            print(f"[{key}] {found} (prompt fingerprint recorded)")
        else:
            print(f"[{key}] {found} (prompt fingerprint unavailable)")
    for _, shot, key in rows:
        if sources[key] == key:
            continue
        source = shots_by_key[sources[key]]
        for field in ("keyframe_path", "keyframe_prompt_hash", "keyframe_prompt_current_hash"):
            shot.pop(field, None)
            if source.get(field):
                shot[field] = source[field]
        shot.pop("keyframe_url", None)
        print(f"[{key}] reuse [{sources[key]}] (same full image)")
    manifest_path = os.path.join(project_dir, "imagegen", "manifest.json")
    try:
        with open(manifest_path, encoding="utf-8-sig") as handle:
            manifest = json.load(handle)
        for job in [*manifest.get("assets", []), *manifest.get("shots", [])]:
            shot = shots_by_key.get(job.get("key"))
            if not shot:
                continue
            job["existing_image"] = bool(shot.get("keyframe_path") and os.path.isfile(shot["keyframe_path"]))
            job["status"] = (
                "ready" if shot.get("keyframe_prompt_hash")
                and shot.get("keyframe_prompt_hash") == shot.get("keyframe_prompt_current_hash")
                else ("needs_review" if shot.get("keyframe_path") else "needs_image")
            )
            if sources[job["key"]] != job["key"]:
                job["source_status"] = job["status"]
                if job["status"] != "ready":
                    job["status"] = "reuse"
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
    except (OSError, ValueError, TypeError):
        pass
    save(bpath, doc)
    if missing:
        raise SystemExit(f"{len(missing)} stills still missing: {', '.join(missing)}")
    print("registered keyframes")


if __name__ == "__main__":
    configure_console()
    if len(sys.argv) < 2:
        raise SystemExit("usage: python codex_prompts.py <episode_dir> [--register | --bakeoff <style1,style2,...> [beat_index]]")
    proj = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2] == "--register":
        register(proj)
    elif len(sys.argv) > 2 and sys.argv[2] == "--bakeoff":
        if len(sys.argv) < 4:
            raise SystemExit("usage: python codex_prompts.py <episode_dir> --bakeoff <style1,style2,...> [beat_index]")
        bi = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        write_bakeoff(proj, [s.strip() for s in sys.argv[3].split(",") if s.strip()], bi)
    else:
        write_prompts(proj)
