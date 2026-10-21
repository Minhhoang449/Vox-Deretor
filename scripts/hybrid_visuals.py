"""Assemble Montage-retrieved clips and generated stills without changing speech.

Footage is trimmed at native speed. Stills use the existing balanced FFmpeg
camera renderer. Each normalized shot is cached; boundaries use clean cuts.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
import threading
from pathlib import Path
import time

from cache_keys import file_fingerprint, stable_hash
from ffmpeg_stills import invoke, probe, render as render_still, settings, validate


def render(project_dir, segments, width, height, fps, output_path, doc, force=False):
    started = time.perf_counter()
    config = settings()
    output = Path(output_path).resolve()
    cache = output.parent / "hybrid-shot-cache"
    cache.mkdir(parents=True, exist_ok=True)
    jobs, elapsed, fingerprints = [], 0.0, {}
    for index, segment in enumerate(segments):
        start_frame = round(elapsed * fps)
        elapsed += float(segment["dur"])
        frames = round(elapsed * fps) - start_frame
        if frames < 1:
            raise ValueError("Every visual segment needs at least one frame.")
        source = segment.get("clip") or segment.get("image")
        if source not in fingerprints:
            fingerprints[source] = file_fingerprint(source, include_content=True)
        payload = {"revision": "hybrid-native-speed-v3-no-disclosure", "segment": segment,
                   "source": fingerprints[source],
                   "frames": frames, "size": [width, height], "fps": fps,
                   "settings": config}
        if not payload["source"]["exists"]:
            raise FileNotFoundError(source)
        jobs.append((index, segment, frames, stable_hash(payload)))

    still_cache_lock = threading.Lock()

    def one(job):
        index, segment, frames, fingerprint = job
        target = cache / f"shot-{index:04d}-{fingerprint}.mp4"
        if target.is_file() and not force:
            try:
                validate(target, config, width, height, fps, frames)
                return target, True
            except RuntimeError:
                pass
        seconds = frames / fps
        if segment.get("clip"):
            source = segment["clip"]
            offset = float(segment.get("source_in_seconds", 0))
            if not math.isfinite(offset) or offset < 0:
                raise ValueError(f"Invalid source_in_seconds for {source}")
            available = float(probe(source, config)["format"]["duration"])
            if offset + seconds > available + 0.001:
                raise ValueError(f"Footage {source} is too short for {seconds:.3f}s at {offset:.3f}s; select another range/clip. Native speed is preserved.")
            inputs = ["-ss", f"{offset:.9f}", "-i", source]
            filters = (f"[0:v]setpts=PTS-STARTPTS,fps={fps},"
                       f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                       f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1[v]")
        else:
            still = cache / f"still-{fingerprint}.mp4"
            # Independent hybrid shots can still share an inner FFmpeg still
            # cache target (same image, duration and camera plan). Serialize the
            # inner cache lookup/render to avoid concurrent partial-file races.
            with still_cache_lock:
                render_still(project_dir, [dict(segment, dur=seconds)], width, height, fps,
                             still, workers=1, cache_dir=cache / "stills-locked-v2", force=force)
            inputs = ["-i", str(still)]
            filters = "[0:v]null[v]"
        temporary = target.with_suffix(".tmp.mp4")
        invoke([config["ffmpeg"], "-y", "-hide_banner", "-loglevel", "error", *inputs,
                "-filter_complex", filters, "-map", "[v]", "-an", "-frames:v", str(frames),
                "-c:v", config["codec"], "-preset", config["preset"], "-cq", str(config["cq"]),
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temporary)])
        validate(temporary, config, width, height, fps, frames)
        os.replace(temporary, target)
        print(f"[hybrid] {index + 1}/{len(jobs)}: {'footage' if segment.get('clip') else 'still'}", flush=True)
        return target, False

    with ThreadPoolExecutor(max_workers=config["workers"]) as pool:
        results = list(pool.map(one, jobs))
    concat = cache / "concat.txt"
    concat.write_text("".join(
        "file '" + path.as_posix().replace("'", "'\\''") + "'\n"
        + f"duration {job[2] / fps:.12f}\n"
        for (path, _), job in zip(results, jobs)), encoding="utf-8")
    temporary = output.with_suffix(".tmp.mp4")
    invoke([config["ffmpeg"], "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat), "-map", "0:v:0", "-an",
            "-c:v", "copy", "-movflags", "+faststart", str(temporary)])
    validate(temporary, config, width, height, fps, sum(j[2] for j in jobs))
    os.replace(temporary, output)
    report = {"backend": "ffmpeg_hybrid", "shots": len(jobs),
              "footage_shots": sum(bool(s.get("clip")) for s in segments),
              "cached_shots": sum(cached for _, cached in results),
              "workers": config["workers"], "video_seconds": sum(j[2] for j in jobs) / fps,
              "wall_seconds": round(time.perf_counter() - started, 3),
              "transitions": "cuts", "source_audio": "muted; optional standalone SFX is mixed by assembly",
              "sources": segments, "output": file_fingerprint(output),
              "review": "Structural render validation only; inspect actual footage, rights, crops and continuity before delivery."}
    Path(str(output) + ".render-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
