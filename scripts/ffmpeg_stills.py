#!/usr/bin/env python3
"""Optional direct FFmpeg renderer for the existing still-image shot grammar.

Uses cumulative frame boundaries, smooth camera easing and a held predecessor
frame during each incoming dissolve. Each shot is cached independently.
It never writes to the source images, narration, beats or Revideo output.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from cache_keys import file_fingerprint, stable_hash
from stills_camera import GENERIC_CAMERAS, plan_cameras, shot_camera_metadata

ROOT = Path(__file__).resolve().parent.parent


def settings():
    with (ROOT / "config" / "pipeline.json").open(encoding="utf-8-sig") as handle:
        pipeline = json.load(handle)
        source = pipeline.get("revideo") or {}
        renderer = pipeline.get("renderer") or {}
    return {
        "ffmpeg": shutil.which(source.get("ffmpeg_path") or "ffmpeg")
                  or source.get("ffmpeg_path") or "ffmpeg",
        "ffprobe": shutil.which(source.get("ffprobe_path") or "ffprobe")
                   or source.get("ffprobe_path") or "ffprobe",
        "codec": source.get("video_codec") or "h264_nvenc",
        "preset": source.get("video_preset") or "p4",
        "cq": source.get("video_cq", 20),
        "transition": float(source.get("transition_seconds", 0.46)),
        "beat_transition": float(source.get("beat_transition_seconds", 0.68)),
        "workers": int(source.get("workers", 2)),
        "camera_sampling": "perspective_cubic_yuv444",
        "camera_policy": renderer.get("stills_camera_policy", "balanced"),
        "incoming_zoom": float(renderer.get("stills_incoming_zoom", 0.0)),
    }


def invoke(command):
    result = subprocess.run(command, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(f"FFmpeg command failed ({result.returncode}):\n"
                           f"{result.stderr[-4000:]}")
    return result.stdout


def probe(path, config):
    return json.loads(invoke([
        config["ffprobe"], "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_frames:format=duration",
        "-of", "json", str(path),
    ]))


def validate(path, config, width, height, fps, frames):
    info = probe(path, config)
    stream = info["streams"][0]
    numerator, denominator = map(int, stream["r_frame_rate"].split("/"))
    duration = float(info["format"]["duration"])
    if ((stream["width"], stream["height"]) != (width, height)
            or abs(numerator / denominator - fps) > 1e-6
            or int(stream.get("nb_frames", -1)) != frames
            or abs(duration - frames / fps) > 0.002):
        raise RuntimeError(f"Invalid still render: {path}; {info}")
    return info


def smooth(expression):
    p = f"min(1,max(0,({expression})))"
    return f"({p}*{p}*(3-2*{p}))"


def smooth_value(value):
    p = min(1.0, max(0.0, value))
    return p * p * (3 - 2 * p)


def opacity_filter(top, bottom, name, values, fps, output):
    # Evaluate easing once per frame in Python. blend's normal mode then uses
    # optimized pixel blending instead of interpreting an expression per pixel.
    commands = ";".join(
        f"{max(0, frame / fps - 0.0000001):.9f} blend@{name} all_opacity {alpha:.9f}"
        for frame, alpha in values
    )
    return [
        f"[{top}]sendcmd=c='{commands}'[{name}cmd]",
        f"[{name}cmd][{bottom}]blend@{name}=all_mode=normal:all_opacity=1:"
        f"eof_action=repeat:repeatlast=1[{output}]",
    ]


def camera_parameters(camera, width):
    camera = (camera or "locked-off").lower()
    movement = re.search(r"pan|track|lateral|follow|arc|tilt|pull|push|zoom|crane", camera)
    if re.search(r"locked|static", camera) or ("hold" in camera and not movement):
        return 1.0, 1.0, 0.0, 0.0
    elif re.search(r"pan|track|lateral|follow|arc|tilt", camera):
        first, last = 1.04, 1.04
    elif camera == "gentle zoom-in":
        first, last = 1.025, 1.055
    elif camera == "gentle zoom-out":
        first, last = 1.055, 1.025
    elif re.search(r"pull.?back|pull out|crane up|reveal", camera):
        first, last = 1.065, 1.025
    elif re.search(r"push.?in|zoom", camera):
        first, last = 1.018, 1.072
    else:
        first, last = 1.025, 1.052
    distance = min(34, width * 0.018)
    dx = dy = 0.0
    if re.search(r"left to right|pan right|track right|lateral|follow|arc", camera):
        dx = -distance
    elif re.search(r"right to left|pan left|track left", camera):
        dx = distance
    elif re.search(r"pan|track", camera):
        dx = -distance * 0.65
    if re.search(r"tilt down|camera down|lower", camera):
        dy = -distance * 0.55
    elif re.search(r"tilt up|crane up|camera up", camera):
        dy = distance * 0.55
    return first, last, dx, dy




def shot_filter(segment, width, height, fps, frames, config,
                transition=0, endpoint=False):
    first, last, dx, dy = camera_parameters(segment.get("camera"), width)
    camera_duration = float(segment.get("camera_duration", segment["dur"]))
    eased = "1" if endpoint else smooth(f"on/{fps}/{camera_duration:.9f}")
    zoom = f"({first}+({last-first:.9f})*{eased})"
    if transition and config["incoming_zoom"]:
        zoom += f"+{config['incoming_zoom']:.9f}*(1-{smooth(f'on/{fps}/{transition:.9f}')})"
    # Moving zoompan crops truncate their dimensions/offsets to integers and
    # align to chroma boundaries. Fractional perspective coordinates avoid
    # those stepping artifacts; full-resolution chroma keeps all planes aligned.
    left = f"W/2-W/2*({zoom})+({dx:.9f})*{eased}"
    right = f"W/2+W/2*({zoom})+({dx:.9f})*{eased}"
    top = f"H/2-H/2*({zoom})+({dy:.9f})*{eased}"
    bottom = f"H/2+H/2*({zoom})+({dy:.9f})*{eased}"
    return (
        "format=yuv444p,"
        f"scale={width}:{height}:"
        "force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={width}:{height},setsar=1,"
        f"loop=loop={frames-1}:size=1:start=0,"
        f"settb=1/{fps},setpts=N,fps={fps},"
        f"perspective=x0='{left}':y0='{top}':x1='{right}':y1='{top}':"
        f"x2='{left}':y2='{bottom}':x3='{right}':y3='{bottom}':"
        "sense=destination:eval=frame:interpolation=cubic,format=yuv420p,"
        f"settb=1/{fps},setpts=PTS-STARTPTS"
    )


def jobs_for(segments, width, height, fps, config):
    if not segments or width < 2 or height < 2 or width % 2 or height % 2 or fps < 1:
        raise ValueError("Stills need a nonempty timeline, even dimensions and positive fps.")
    if not math.isfinite(config["incoming_zoom"]) or not 0 <= config["incoming_zoom"] <= 0.1:
        raise ValueError("stills_incoming_zoom must be between 0 and 0.1.")
    segments = plan_cameras(segments, config)
    fingerprints = {}
    boundary = 0
    seconds = 0.0
    jobs = []
    renderer = file_fingerprint(__file__, include_content=True)
    # Worker count only affects scheduling, never the rendered pixels.
    render_settings = {k: v for k, v in config.items() if k != "workers"}
    for index, segment in enumerate(segments):
        duration = float(segment["dur"])
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError(f"Shot {index} has invalid duration {duration}.")
        seconds += duration
        end = round(seconds * fps)
        frames = end - boundary
        boundary = end
        if frames < 1:
            raise ValueError(f"Shot {index} is shorter than one output frame.")
        prior = segments[index - 1] if index else None
        transition = 0.0
        if prior:
            transition = config["beat_transition"] if (
                prior.get("beat_id", "") != segment.get("beat_id", "")
            ) else config["transition"]
            transition = max(0.0, min(transition, frames / fps))
        sources = []
        for item in ([segment, prior] if prior and transition else [segment]):
            image = str(Path(item["image"]).resolve())
            if image not in fingerprints:
                fingerprints[image] = file_fingerprint(image, include_content=True)
            if not fingerprints[image]["exists"]:
                raise FileNotFoundError(image)
            sources.append({
                "image": fingerprints[image],
                "camera": item.get("camera") or "locked-off",
                "duration": float(item["dur"]),
                "camera_duration": float(item.get("camera_duration", item["dur"])),
            })
        payload = {
            "schema": 1, "sources": sources, "frames": frames,
            "size": [width, height, fps], "transition": transition,
            "fade_in": index == 0, "fade_out": index == len(segments) - 1,
            "settings": render_settings, "renderer": renderer,
        }
        jobs.append({"index": index, "segment": segment, "prior": prior,
                     "frames": frames, "transition": transition,
                     "fade_in": payload["fade_in"], "fade_out": payload["fade_out"],
                     "fingerprint": stable_hash(payload)})
    return jobs


def render_cache_fingerprint(project_dir, segments, width, height, fps):
    return stable_hash({
        "project": str(Path(project_dir).resolve()),
        "shots": [job["fingerprint"] for job in
                  jobs_for(segments, width, height, fps, settings())],
    })


def write_json(path, value):
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def render_shot(job, cache_dir, width, height, fps, config, force):
    output = cache_dir / f"{job['index']:04d}-{job['fingerprint']}.mp4"
    metadata = Path(str(output) + ".cache.json")
    if not force and output.is_file() and metadata.is_file():
        try:
            saved = json.loads(metadata.read_text(encoding="utf-8"))
            if saved["output"] == file_fingerprint(output):
                validate(output, config, width, height, fps, job["frames"])
                return output, True
        except (KeyError, ValueError, OSError, RuntimeError, IndexError):
            pass
    temporary = output.with_suffix(".partial.mp4")
    inputs = ["-i", str(job["segment"]["image"])]
    filters = [
        "[0:v]" + shot_filter(job["segment"], width, height, fps, job["frames"],
                             config, job["transition"]) + "[current]"
    ]
    previous = "current"
    input_count = 1
    if job["transition"]:
        inputs += ["-i", str(job["prior"]["image"])]
        input_count += 1
        filters.append(
            "[1:v]" + shot_filter(job["prior"], width, height, fps, 1,
                                  config, endpoint=True) + "[prior]"
        )
        values = [(frame, smooth_value(frame / fps / job["transition"]))
                  for frame in range(min(job["frames"], math.ceil(job["transition"] * fps) + 1))]
        filters.extend(opacity_filter("current", "prior", "incoming", values,
                                      fps, "transitioned"))
        previous = "transitioned"
    if job["fade_in"] or job["fade_out"]:
        duration = job["frames"] / fps
        inputs += ["-f", "lavfi", "-i",
                   f"color=c=0x10100e:s={width}x{height}:r={fps}:d={1/fps:.9f}"]
        filters.append(f"[{input_count}:v]settb=1/{fps},setpts=PTS-STARTPTS[background]")
        values = []
        last_alpha = None
        for frame in range(job["frames"]):
            t = frame / fps
            fade_in = smooth_value(t / 0.48) if job["fade_in"] else 1
            fade_out = 1 - smooth_value((t - (duration - 0.58)) / 0.58) if job["fade_out"] else 1
            alpha = min(fade_in, fade_out)
            if alpha != last_alpha:
                values.append((frame, alpha))
                last_alpha = alpha
        filters.extend(opacity_filter(previous, "background", "fade", values, fps, "faded"))
        previous = "faded"
    if config["codec"] != "h264_nvenc":
        raise ValueError("Experimental FFmpeg still renderer currently requires h264_nvenc.")
    invoke([
        config["ffmpeg"], "-y", "-hide_banner", "-loglevel", "error",
        "-filter_complex_threads", "2", *inputs,
        "-filter_complex", ";".join(filters), "-map", f"[{previous}]", "-an",
        "-frames:v", str(job["frames"]), "-c:v", config["codec"],
        "-preset", str(config["preset"]), "-cq", str(config["cq"]), "-b:v", "0",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temporary),
    ])
    validate(temporary, config, width, height, fps, job["frames"])
    os.replace(temporary, output)
    write_json(metadata, {"fingerprint": job["fingerprint"],
                          "output": file_fingerprint(output)})
    return output, False


def render(project_dir, segments, width, height, fps, output_path,
           workers=None, cache_dir=None, force=False):
    started = time.perf_counter()
    config = settings()
    count = config["workers"] if workers is None else int(workers)
    if count < 1:
        raise ValueError("Worker count must be at least one.")
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(cache_dir or output.parent / "ffmpeg-shot-cache").resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    jobs = jobs_for(segments, width, height, fps, config)
    clips = [None] * len(jobs)
    reused = 0
    print(f"[ffmpeg-stills] {len(jobs)} shots; {width}x{height}/{fps}fps; "
          f"{count} workers; {config['codec']} {config['preset']} CQ {config['cq']}", flush=True)
    with ThreadPoolExecutor(max_workers=count) as pool:
        pending = {pool.submit(render_shot, job, cache_dir, width, height, fps,
                               config, force): job["index"] for job in jobs}
        for completed, future in enumerate(as_completed(pending), 1):
            index = pending[future]
            clips[index], cached = future.result()
            reused += int(cached)
            print(f"[ffmpeg-stills] {completed}/{len(jobs)} shots"
                  f" ({reused} cached)", flush=True)
    concat_file = cache_dir / f"concat-{stable_hash([str(p) for p in clips])}.txt"
    # MP4's reported duration is rounded. Explicit frame-derived durations keep
    # concat from accumulating that rounding across a long episode.
    concat_file.write_text("".join(
        "file '" + clip.as_posix().replace("'", "'\\''") + "'\n"
        + f"duration {job['frames'] / fps:.12f}\n"
        for clip, job in zip(clips, jobs)
    ), encoding="utf-8")
    temporary = output.with_name(output.stem + ".partial.mp4")
    invoke([config["ffmpeg"], "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-map", "0:v:0", "-an", "-c:v", "copy", "-movflags", "+faststart",
            str(temporary)])
    total_frames = sum(job["frames"] for job in jobs)
    info = validate(temporary, config, width, height, fps, total_frames)
    os.replace(temporary, output)
    elapsed = time.perf_counter() - started
    duration = total_frames / fps
    report = {
        "backend": "ffmpeg_stills", "wall_seconds": round(elapsed, 3),
        "video_seconds": duration, "video_seconds_per_wall_second": duration / elapsed,
        "frames": total_frames, "shots": len(jobs), "reused_shots": reused,
        "unique_source_images": len({str(Path(segment["image"]).resolve()) for segment in segments}),
        "full_image_reuse_shots": len(segments) - len({str(Path(segment["image"]).resolve()) for segment in segments}),
        "rendered_shots": len(jobs) - reused, "workers": count,
        "settings": config, "output": file_fingerprint(output), "probe": info,
        "motion_plan": [{"shot": job["index"] + 1,
                         "original": job["segment"]["original_camera"],
                         "camera": job["segment"]["camera"],
                         "reason": job["segment"]["camera_reason"]} for job in jobs],
        "limitations": [
            "Visuals only; final caption/audio export is a separate measured stage.",
            "Camera sampling differs from Chromium Canvas; review motion before delivery.",
            "Purpose-led camera uses authored metadata and text hints, not image understanding; verify labels and crop visually.",
        ],
    }
    write_json(str(output) + ".render-report.json", report)
    print(f"[ffmpeg-stills] {duration:.2f}s video in {elapsed:.2f}s; "
          f"{duration/elapsed:.2f}x realtime", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline", help="An existing Revideo src/timeline.json; read-only.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--seconds", type=float, help="Preview only the first N seconds.")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--cache-dir")
    args = parser.parse_args()
    timeline_path = Path(args.timeline).resolve()
    data = json.loads(timeline_path.read_text(encoding="utf-8-sig"))
    project_dir = timeline_path.parent.parent.parent
    limit = float(data["duration"]) if args.seconds is None else args.seconds
    if not math.isfinite(limit) or limit <= 0:
        parser.error("--seconds must be positive.")
    segments = []
    beats_path = project_dir / "beats.json"
    shot_metadata = {}
    ordered_shots = []
    if beats_path.is_file():
        beats = json.loads(beats_path.read_text(encoding="utf-8-sig"))
        from image_reuse import apply_image_reuse
        apply_image_reuse(beats)
        for beat in beats.get("beats", []):
            for shot in beat.get("shots") or [beat]:
                if shot.get("kind") == "host":
                    continue
                ordered_shots.append(shot)
                image = shot.get("keyframe_path") or shot.get("image_path")
                if image:
                    shot_metadata[Path(image).name] = shot
    for item in data["segments"]:
        if float(item["start"]) >= limit:
            break
        shot = shot_metadata.get(Path(item["image"]).name, {})
        # One full image can appear in multiple shots with different camera plans.
        # Prefer timeline position when it still matches the current beat map.
        index = item.get("index")
        if isinstance(index, int) and 0 <= index < len(ordered_shots):
            candidate = ordered_shots[index]
            image = candidate.get("keyframe_path") or candidate.get("image_path")
            if image and Path(image).name == Path(item["image"]).name:
                shot = candidate
        animation = shot.get("animation") or {}
        segments.append({
            "image": str(project_dir / "keyframes" / item["image"]),
            "dur": min(float(item["duration"]), limit - float(item["start"])),
            "camera_duration": float(item["duration"]),
            "camera": item["camera"], "beat_id": item.get("beatId", ""),
            "scene": shot.get("scene", ""), "framing": animation.get("framing", ""),
            "camera_policy": animation.get("camera_policy", "auto"),
            **shot_camera_metadata(shot),
        })
    render(project_dir, segments, int(data["width"]), int(data["height"]),
           int(data["fps"]), args.output, args.workers, args.cache_dir)


if __name__ == "__main__":
    main()
