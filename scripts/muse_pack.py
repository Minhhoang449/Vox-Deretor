#!/usr/bin/env python3
"""
Export one Muse.ai image-to-video job per shot, using this project's motion prompt.

Does not call a video API. After you render in Muse.ai, save each clip as
clips/clip_<key>.mp4 (or muse/<key>/clip.mp4) and run:

  python muse_pack.py <project_dir> --register

Usage: python muse_pack.py <project_dir>
"""
import json
import os
import shutil
import sys

from clips import collage_prompt, painterly_prompt
from styles import resolve_theme

from codex_prompts import load, save, shots_of


def export(project_dir):
    bpath, doc = load(project_dir)
    style = doc.get("style", "collage")
    theme = resolve_theme(doc.get("theme")) or {}
    motion_style = doc.get("motion_style") or theme.get("motion_style", "punchy")
    constraints = doc.get("constraints", "strict")
    aspect = doc.get("aspect", "16:9")
    muse_root = os.path.join(project_dir, "muse")
    os.makedirs(muse_root, exist_ok=True)

    rows = []
    missing = []
    for beat in doc["beats"]:
        for shot, key in shots_of(beat):
            if shot.get("kind") == "host":
                continue
            src = shot.get("keyframe_path")
            if not src or not os.path.exists(src):
                missing.append(key)
                print(f"[{key}] no local keyframe — run Codex, then codex_prompts.py --register")
                continue
            camera = shot.get("camera_move") or shot.get("motion", "push_in")
            if style == "collage":
                prompt = collage_prompt(
                    camera, element_motion=shot.get("element_motion"),
                    feel=beat.get("feel"), palette=beat.get("bg"),
                    amplitude=motion_style, anchor_freeze=doc.get("anchor_freeze"),
                    has_title=shot.get("title", True), constraints=constraints)
            else:
                prompt = painterly_prompt(shot.get("motion", camera))
            shot["motion_prompt"] = prompt
            if shot.get("dur") is None:
                raise SystemExit(f"[{key}] needs dur. Muse uses that shot's duration, up to 10 seconds.")
            dur = float(shot["dur"])
            if dur < 3 or dur > 10:
                raise SystemExit(f"[{key}] dur is {dur}s. Set it between 3 and 10.")
            slot = os.path.join(muse_root, key)
            os.makedirs(slot, exist_ok=True)
            ext = os.path.splitext(src)[1].lower() or ".png"
            image_name = "image" + ext
            shutil.copy2(src, os.path.join(slot, image_name))
            with open(os.path.join(slot, "prompt.txt"), "w", encoding="utf-8") as f:
                f.write(prompt.strip() + "\n")
            meta = {
                "key": key,
                "beat_id": beat["id"],
                "duration_sec": dur,
                "aspect": aspect,
                "image": image_name,
                "save_clip_as": os.path.join("clips", f"clip_{key}.mp4").replace("\\", "/"),
                "narration": beat.get("narration", ""),
            }
            with open(os.path.join(slot, "meta.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            rows.append(meta)
            print(f"[{key}] muse/{key}/  {dur}s")

    lines = [
        "# Muse.ai — ảnh thành video",
        "",
        "Mỗi thư mục là một shot. Muse image-to-video tối đa 10 giây. Không gọi API video.",
        "",
        "1. Mở Muse.ai, chế độ image-to-video.",
        "2. Upload `image` trong thư mục shot.",
        "3. Dán nguyên văn `prompt.txt` (đây là prompt chuyển động của dự án).",
        "4. Đặt thời lượng bằng `duration_sec` của shot đó. Không vượt 10 giây, và không kéo mọi shot thành 10 giây.",
        "5. Tải clip về `clips/clip_<key>.mp4`.",
        "6. Chạy `python scripts/muse_pack.py <project> --register`.",
        "",
        "| Shot | Giây | Ảnh | Prompt | Lưu clip |",
        "|---|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['key']} | {row['duration_sec']} | `muse/{row['key']}/{row['image']}` "
            f"| `muse/{row['key']}/prompt.txt` | `{row['save_clip_as']}` |"
        )
    if missing:
        lines += ["", f"Thiếu ảnh cho: {', '.join(missing)}."]
    index = os.path.join(muse_root, "INDEX.md")
    with open(index, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    save(bpath, doc)
    print("wrote", index)
    if missing:
        raise SystemExit(f"{len(missing)} shots have no still")


def register(project_dir):
    bpath, doc = load(project_dir)
    clip_dir = os.path.join(project_dir, "clips")
    muse_root = os.path.join(project_dir, "muse")
    os.makedirs(clip_dir, exist_ok=True)
    missing = []
    for beat in doc["beats"]:
        for shot, key in shots_of(beat):
            if shot.get("kind") == "host":
                continue
            candidates = [
                os.path.join(clip_dir, f"clip_{key}.mp4"),
                os.path.join(muse_root, key, "clip.mp4"),
            ]
            found = next((p for p in candidates if os.path.exists(p)), None)
            if not found:
                missing.append(key)
                print(f"[{key}] missing clips/clip_{key}.mp4")
                continue
            if os.path.basename(found) == "clip.mp4":
                dest = os.path.join(clip_dir, f"clip_{key}.mp4")
                if os.path.abspath(found) != os.path.abspath(dest):
                    shutil.copy2(found, dest)
                found = dest
            shot["clip_path"] = found
            shot.pop("clip_url", None)
            print(f"[{key}] {found}")
    save(bpath, doc)
    if missing:
        raise SystemExit(f"{len(missing)} clips still missing: {', '.join(missing)}")
    print("registered clips")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python muse_pack.py <project_dir> [--register]")
    proj = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2] == "--register":
        register(proj)
    else:
        export(proj)
