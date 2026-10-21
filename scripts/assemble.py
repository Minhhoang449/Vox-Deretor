#!/usr/bin/env python3
"""
Assembly stage: imagegen stills + narration + effects + music -> final.mp4

FFmpeg/NVENC animates stills by default; Revideo is optional. TTS, captions,
audio mixing, and final assembly run locally. Narration and captions are timed per phrase from final.srt when
caption_source is `srt`. Optional SFX and BGM are mixed under narration.

Usage: python3 assemble.py <project_dir>   (default: out/tang-30s)
"""
import json
import os
import subprocess
import sys
import time

import text_overlay
from cache_keys import file_fingerprint
from local_guard import configure_console, refuse_out_dir
from image_reuse import apply_image_reuse, shot_rows as image_shot_rows
from image_reuse_qa import build_report as build_image_reuse_report
from stills_camera import plan_cameras, shot_camera_metadata
from narration_lock import assert_approved, assert_audio
from visual_policy import is_video_shot
from visual_sources import validate_source_plan

FPS, TAIL = 24, 0.5
WATERMARK = "Made with Atlas Cloud · vox-director"
LOCAL_WATERMARK = "Vox Director"
RES = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}


def ff(args, cwd=None):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True, cwd=cwd)


def probe_dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def has_audio(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout
    return bool(out.strip())


def shots_of(beat):
    if beat.get("shots"):
        for s in beat["shots"]:
            yield s
    else:
        yield beat


def resolve_project_path(project_dir, path):
    if not path:
        return None
    return path if os.path.isabs(path) else os.path.abspath(os.path.join(project_dir, path))


def pipeline_config():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "pipeline.json")
    try:
        with open(path, encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return {}


def renderer_config():
    return pipeline_config().get("renderer") or {}


def allocate_narration_tail(durations, shot_list, required, max_shot):
    """Extend available still shots without silently exceeding their planned limit."""
    extra = max(0.0, required - sum(durations))
    for index in range(len(durations) - 1, -1, -1):
        if shot_list[index].get("kind") == "host" or is_video_shot(shot_list[index]):
            continue
        capacity = max(0.0, max_shot - durations[index])
        addition = min(extra, capacity)
        durations[index] += addition
        extra -= addition
        if extra <= 1e-6:
            return
    if extra > 1e-6:
        raise SystemExit(
            f"Narration needs {required:.2f}s of visuals, but the remaining shots cannot "
            f"cover it while staying at or below {max_shot}s. Add a shot or revise the beat."
        )


def cached_revideo_is_valid(body, cache_path, fingerprint, expected_duration):
    try:
        with open(cache_path, encoding="utf-8-sig") as handle:
            cache = json.load(handle)
    except (OSError, ValueError, TypeError):
        return False
    try:
        return (
            cache.get("fingerprint") == fingerprint
            and cache.get("output_file") == file_fingerprint(body)
            and abs(float(cache.get("duration", 0)) - expected_duration) <= 0.25
            and abs(probe_dur(body) - expected_duration) <= 0.25
        )
    except (TypeError, ValueError):
        return False


def save_revideo_cache(body, cache_path, fingerprint, duration):
    temporary = cache_path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump({
            "fingerprint": fingerprint,
            "output_file": file_fingerprint(body),
            "duration": probe_dur(body),
        }, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, cache_path)


def run(project_dir, output_path=None, reuse_video=False, reuse_source_audio=False,
        force_video=False, reuse_revideo=False, stills_renderer=None):
    started = time.perf_counter()
    timings = {}
    configure_console()
    requested_renderer = stills_renderer
    stills_renderer = stills_renderer or ("revideo" if reuse_revideo else
        renderer_config().get("stills_renderer", "ffmpeg"))
    if stills_renderer not in ("revideo", "ffmpeg"):
        raise SystemExit("--stills-renderer must be revideo or ffmpeg.")
    if reuse_revideo and stills_renderer != "revideo":
        raise SystemExit("--reuse-revideo requires --stills-renderer=revideo.")
    with open(os.path.join(project_dir, "beats.json"), encoding="utf-8-sig") as f:
        doc = json.load(f)
    if doc.get("pipeline") == "local":
        refuse_out_dir(project_dir)
        assert_approved(project_dir, doc)
        assert_audio(project_dir, doc)
        validate_source_plan(project_dir, doc)
    beats = doc["beats"]
    W, H = RES.get(doc.get("aspect", "16:9"), (1920, 1080))
    if doc.get("pipeline") == "local":
        channel = doc.get("channel") or {}
        if doc.get("visual_disclosure_enabled") is False:
            wm_text = ""
        else:
            wm_text = (doc.get("visual_disclosure") or channel.get("display_name")
                       or doc.get("channel_id") or LOCAL_WATERMARK).strip()
    else:
        wm_text = doc.get("watermark", WATERMARK)
    fps = int((doc.get("format") or {}).get("fps") or FPS)
    mix = doc.get("mix", {})                      # per-project audio balance (optional)
    music_vol = float(mix.get("music", 0.6))      # BGM level (was a fixed 0.9 — lowered so VO leads)
    voice_vol = float(mix.get("voice", 1.25))     # narration boost before the duck + final mix
    source_audio_vol = max(0.0, min(1.0, float(mix.get("source_audio", 0.55))))
    source_audio_enabled = bool(mix.get("source_audio_enabled", doc.get("pipeline") == "local"))
    cap_style = doc.get("caption_style", "white") # white (default, clean) | paper (collage)
    captions_on = bool(doc.get("captions", True))
    caption_source = doc.get("caption_source") or ("srt" if doc.get("pipeline") == "local" else "beat")
    captions_from_srt = captions_on and caption_source == "srt"
    tmp = os.path.join(project_dir, "_seg")

    # ---- flatten shots into timed segments; track each beat's span ----
    segs = []          # {clip, dur}
    beat_spans = []    # {start, dur, beat}
    t = 0.0
    is_local = doc.get("pipeline") == "local"
    visual_mode = doc.get("visual_mode") or "clips"
    if visual_mode not in ("revideo_stills", "clips", "hybrid"):
        raise SystemExit(f"Unknown visual_mode {visual_mode!r}; use 'revideo_stills', 'hybrid' or 'clips'.")
    use_revideo = visual_mode == "revideo_stills"
    use_hybrid = visual_mode == "hybrid"
    if use_hybrid and (requested_renderer == "revideo" or reuse_revideo):
        raise SystemExit("Hybrid footage/stills use local FFmpeg; Revideo-only flags cannot be applied.")
    if use_revideo and any(is_video_shot(s) for b in beats for s in shots_of(b)):
        raise SystemExit("Retrieved footage requires visual_mode: hybrid; revideo_stills accepts images only.")
    if use_revideo or use_hybrid:
        image_sources = apply_image_reuse(doc)
        image_shots = {key: shot for _, shot, key in image_shot_rows(doc)}
        unique_images = len(set(image_sources.values()))
        print(f"[images] {len(image_sources)} shots use {unique_images} original images; "
              f"{len(image_sources) - unique_images} shots reuse the full image.")
    if requested_renderer == "ffmpeg" and not (use_revideo or use_hybrid):
        raise SystemExit("The FFmpeg stills renderer requires visual_mode: revideo_stills.")
    fmt = doc.get("format") or {}
    min_shot = int(fmt.get("scene_seconds_min", 3))
    max_shot = int(fmt.get("scene_seconds_max", 10))
    for beat in beats:
        beat_start = t
        shot_list = list(shots_of(beat))
        durs = [float(s.get("dur", 10)) for s in shot_list]
        if is_local:
            audio_path = beat.get("narration_audio")
            if audio_path and not os.path.isabs(audio_path):
                audio_path = os.path.abspath(os.path.join(project_dir, audio_path))
                beat["narration_audio"] = audio_path
            if not audio_path or not os.path.isfile(audio_path):
                raise SystemExit(
                    f"[{beat.get('id', '?')}] narration audio is missing. "
                    "Run scripts/omnivoice_tts.py before assembling."
                )
            narration_dur = probe_dur(audio_path)
            if narration_dur <= 0:
                raise SystemExit(f"[{beat.get('id', '?')}] narration audio has no readable duration: {audio_path}")
            beat["narration_dur"] = round(narration_dur, 2)
            for shot, dur in zip(shot_list, durs):
                if shot.get("kind") != "host" and not min_shot <= dur <= max_shot:
                    raise SystemExit(
                        f"[{beat.get('id', '?')}] shot duration {dur:g}s is outside "
                        f"the planned {min_shot}-{max_shot}s range."
                    )
        else:
            narration_dur = float(beat.get("narration_dur", sum(durs)))
        # Ensure the beat covers its measured narration, with a short visual tail.
        need = narration_dur + TAIL
        # a host shot's audio IS its clip, so it is never extended or slowed (sync would break)
        if sum(durs) < need and shot_list[-1].get("kind") != "host":
            allocate_narration_tail(durs, shot_list, need, max_shot)
        if is_local:
            for shot, dur in zip(shot_list, durs):
                if shot.get("kind") != "host" and not min_shot <= dur <= max_shot:
                    raise SystemExit(
                        f"[{beat.get('id', '?')}] adjusted shot duration {dur:g}s is outside "
                        f"the planned {min_shot}-{max_shot}s range. Add a shot or revise the beat."
                    )
        for s, d in zip(shot_list, durs):
            if use_hybrid and is_video_shot(s):
                source = s["visual_source"]
                segs.append({"clip": resolve_project_path(project_dir, s["clip_path"]),
                             "dur": round(d, 3), "source_in_seconds": s.get("source_in_seconds", 0),
                             "source": source,
                             "beat_id": beat.get("id", ""), "shot_id": s.get("id", "")})
            elif use_revideo or use_hybrid:
                image = resolve_project_path(project_dir, s.get("keyframe_path") or s.get("image_path"))
                if not image or not os.path.isfile(image):
                    raise SystemExit(
                        f"[{beat.get('id', '?')}] still image is missing for shot "
                        f"{s.get('id', s.get('key', '?'))}. Render/register keyframes first."
                    )
                animation = s.get("animation") or {}
                camera = animation.get("camera", "auto")
                shot_key = str(beat['id']) + str(s.get('id', '')) if beat.get('shots') else str(beat['id'])
                image_source_key = image_sources.get(shot_key, shot_key)
                source_shot = image_shots.get(image_source_key, s)
                segs.append({"image": image, "dur": round(d, 3), "camera": camera,
                             "scene": s.get("scene", ""),
                             "framing": animation.get("framing", ""),
                             "camera_policy": animation.get("camera_policy", "auto"),
                             "beat_id": beat.get("id", ""), "shot_id": s.get("id", s.get("key", "")),
                             **shot_camera_metadata(s, source_shot),
                             "image_source_key": image_source_key, "is_scene_shot": shot_key in image_sources, "shot_key": shot_key,
                             })
            else:
                clip = resolve_project_path(project_dir, s.get("clip_path"))
                if not clip or not os.path.isfile(clip):
                    raise SystemExit(f"Missing clip for shot {s.get('id', s.get('key', '?'))}: {clip}")
                segs.append({"clip": clip, "dur": round(d, 3), "host": s.get("kind") == "host"})
            t += d
        beat_spans.append({"start": beat_start, "dur": round(t - beat_start, 2), "beat": beat})
    total = round(t, 2)
    if use_revideo or use_hybrid:
        # Durations include the measured narration tail allocation above.
        image_reuse_report = build_image_reuse_report(segs)
        qa_path = os.path.join(project_dir, "image-reuse-qa.json")
        with open(qa_path, "w", encoding="utf-8") as handle:
            json.dump(image_reuse_report, handle, ensure_ascii=False, indent=2)
        print(f"[images] reuse occupies {image_reuse_report['reused_duration_percent']:.2f}% of scene seconds; QA: {qa_path}")
        for warning in image_reuse_report['warnings']:
            print("[images] review:", json.dumps(warning, ensure_ascii=False))
        if use_revideo:
            segs = plan_cameras(segs, {"camera_policy": renderer_config().get("stills_camera_policy", "balanced")})

    if is_local:
        min_runtime = int(fmt.get("target_seconds_min", 840))
        max_runtime = int(fmt.get("target_seconds_max", 1800))
        if not min_runtime <= total <= max_runtime:
            raise SystemExit(
                f"Predicted final runtime is {total:.0f}s ({total / 60:.1f} min), "
                f"outside the allowed {min_runtime // 60}-{max_runtime // 60} minute range. "
                "Revise the approved narration or visual timing, then run assembly again."
            )
        target = float(fmt.get("target_seconds") or 0)
        tolerance = float(fmt.get("target_runtime_tolerance_percent", 5))
        if target > 0:
            delta = abs(total - target)
            allowed_delta = max(15, target * tolerance / 100)
            message = (
                f"[runtime] planned {target / 60:.1f} min; predicted "
                f"{total / 60:.1f} min (allowed drift {tolerance:g}%)."
            )
            print(message if delta <= allowed_delta else f"{message} Review the mismatch before accepting the render.")

    os.makedirs(tmp, exist_ok=True)

    # Validate captions before any expensive visual render. Both exporters below
    # receive these exact beat starts and the accepted phrase timeline.
    caption_timeline = None
    if captions_from_srt and is_local:
        caption_started = time.perf_counter()
        from caption_timeline import build as build_caption_timeline
        caption_timeline = build_caption_timeline(project_dir, beat_spans, W, H)
        timings['caption_alignment_seconds'] = round(time.perf_counter() - caption_started, 3)

    # ---- 1) render visuals ----
    stage_started = time.perf_counter()
    if use_hybrid:
        from hybrid_visuals import render as render_hybrid
        body = os.path.join(project_dir, "video", "hybrid-visuals.mp4")
        render_hybrid(project_dir, segs, W, H, fps, body, doc, force=force_video)
        seg_files = []
    elif use_revideo:
        body = os.path.join(project_dir, "video", f"{stills_renderer}-visuals.mp4")
        os.makedirs(os.path.dirname(body), exist_ok=True)
        cache_path = body + ".cache.json"
        if stills_renderer == "ffmpeg":
            from ffmpeg_stills import render as render_stills, render_cache_fingerprint
        else:
            from revideo_stills import render as render_stills, render_cache_fingerprint
        render_fingerprint = render_cache_fingerprint(project_dir, segs, W, H, fps)
        if reuse_revideo:
            try:
                with open(cache_path, encoding="utf-8-sig") as handle:
                    cached = json.load(handle)
            except (OSError, ValueError, TypeError):
                raise SystemExit("Cannot reuse Revideo render: its cache metadata is missing or invalid.")
            rendered_duration = probe_dur(body) if os.path.isfile(body) else 0.0
            source_paths = [segment["image"] for segment in segs]
            rendered_mtime = os.path.getmtime(body) if os.path.isfile(body) else 0.0
            changed_sources = [path for path in source_paths
                               if not os.path.isfile(path) or os.path.getmtime(path) > rendered_mtime]
            if (not os.path.isfile(body)
                    or cached.get("fingerprint") != render_fingerprint
                    or cached.get("output_file") != file_fingerprint(body)
                    or abs(float(cached.get("duration", 0)) - rendered_duration) > 0.25
                    or rendered_duration + 0.25 < total
                    or changed_sources):
                raise SystemExit(
                    "Cannot reuse Revideo render: output integrity, source timestamps, or timeline coverage failed."
                )
            print(f"[assemble] reusing existing Revideo render by request ({rendered_duration:.2f}s)")
        elif (not force_video and os.path.isfile(body) and
                cached_revideo_is_valid(body, cache_path, render_fingerprint, total)):
            print(f"[assemble] reusing {stills_renderer} still animation ({probe_dur(body):.2f}s)")
        else:
            if os.path.isfile(body):
                print(f"[assemble] {stills_renderer} cache is stale or --force-video was set; rendering again")
            if stills_renderer == "ffmpeg":
                render_stills(project_dir, segs, W, H, fps, body, force=force_video)
            else:
                render_stills(project_dir, segs, W, H, fps, body)
            save_revideo_cache(body, cache_path, render_fingerprint, total)
        seg_files = []
        print(f"[assemble] {stills_renderer} camera animation and soft dissolves: {len(segs)} stills")
    else:
        body = os.path.join(tmp, "body_silent.mp4")
        seg_files = [os.path.join(tmp, f"seg_{i:02d}.mp4") for i in range(len(segs))]
        if reuse_video:
            if not os.path.isfile(body) or not all(os.path.isfile(p) for p in seg_files):
                raise SystemExit("Cannot reuse normalized video: body_silent.mp4 or shot segments are missing.")
            print(f"[assemble] reusing {len(seg_files)} normalized visual segments")
        else:
            for i, s in enumerate(segs):
                out = seg_files[i]
                # If the clip is shorter than the segment (narration longer than the AI
                # clip), slow it to fill instead of freezing the last frame.
                cd = probe_dur(s["clip"])
                factor = s["dur"] / cd if cd > 0 else 1.0
                pre = f"setpts={factor:.4f}*PTS," if factor > 1.02 and not s["host"] else ""
                fc = (f"[0:v]{pre}split[s0][s1];"
                      f"[s0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                      f"boxblur=26:2,eq=brightness=-0.05[bg];"
                      f"[s1]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
                      f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={fps},"
                      f"tpad=stop_mode=clone:stop_duration=1[v]")
                ff(["-i", s["clip"], "-an", "-filter_complex", fc, "-map", "[v]", "-t", f"{s['dur']}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", out])

            # ---- 2) concat all shot segments (video only) ----
            listf = os.path.join(tmp, "list.txt")
            with open(listf, "w", encoding="utf-8") as f:
                for path in seg_files:
                    f.write(f"file '{os.path.abspath(path)}'\n")
            ff(["-f", "concat", "-safe", "0", "-i", listf, "-c", "copy", body])

    # ---- 2b) optional sound effects under narration ----
    timings["visuals_seconds"] = round(time.perf_counter() - stage_started, 3)
    stage_started = time.perf_counter()
    source_audio_path = None
    if source_audio_enabled:
        source_audio_path = os.path.join(tmp, "source_audio.wav")
        if use_revideo or use_hybrid:
            configured_sfx = resolve_project_path(project_dir, doc.get("sfx_path"))
            default_sfx = os.path.join(project_dir, "audio", "sfx.wav")
            sfx_input = configured_sfx or (default_sfx if os.path.isfile(default_sfx) else None)
            if configured_sfx and not os.path.isfile(configured_sfx):
                raise SystemExit(f"Configured SFX track does not exist: {configured_sfx}")
            if sfx_input and os.path.isfile(sfx_input):
                ff(["-i", sfx_input, "-vn", "-af",
                    f"aresample=48000,apad,atrim=duration={total:.3f},asetpts=PTS-STARTPTS",
                    "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", source_audio_path])
                print(f"[assemble] normalized standalone SFX track at gain {source_audio_vol:.2f}")
            else:
                source_audio_path = None
                print("[assemble] no audio/sfx.wav or sfx_path; rendering without source effects")
        elif reuse_source_audio and os.path.isfile(source_audio_path):
            audio_dur = probe_dur(source_audio_path)
            if abs(audio_dur - total) > 0.2:
                raise SystemExit(
                    f"Cannot reuse source audio: expected {total:.2f}s, found {audio_dur:.2f}s.")
            print(f"[assemble] reusing source audio track ({audio_dur:.2f}s)")
        else:
            audio_segments = []
            for i, s in enumerate(segs):
                wav = os.path.join(tmp, f"source_audio_{i:03d}.wav")
                if has_audio(s["clip"]):
                    af = (f"aresample=48000,apad,atrim=duration={s['dur']:.2f},"
                          "asetpts=PTS-STARTPTS")
                    ff(["-i", s["clip"], "-map", "0:a:0", "-vn", "-af", af,
                        "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", wav])
                else:
                    ff(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{s['dur']:.2f}",
                        "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", wav])
                audio_segments.append(wav)
            audio_list = os.path.join(tmp, "source_audio_list.txt")
            with open(audio_list, "w", encoding="utf-8") as f:
                for path in audio_segments:
                    f.write(f"file '{os.path.abspath(path)}'\n")
            ff(["-f", "concat", "-safe", "0", "-i", audio_list, "-ac", "2", "-ar", "48000",
                "-c:a", "pcm_s16le", source_audio_path])
            print(f"[assemble] preserved source audio for {len(segs)} shots at gain {source_audio_vol:.2f}")

    # ---- 3) captions + watermark PNGs ----
    timings["source_audio_seconds"] = round(time.perf_counter() - stage_started, 3)
    stage_started = time.perf_counter()
    caption_ass_path = None
    if captions_from_srt and doc.get("pipeline") == "local":
        from export_srt import run as write_srt
        write_srt(project_dir, beat_spans, W, H, timeline=caption_timeline)
        from export_ass import run as write_ass
        caption_ass_path = write_ass(project_dir, beat_spans, W, H, timeline=caption_timeline)

    cap_pngs = []
    if captions_on and not captions_from_srt:
        for bs in beat_spans:
            beat = bs["beat"]
            p = os.path.join(tmp, f"cap_{beat['id']}.png")
            acc = None
            if cap_style == "paper":              # only the paper style uses a per-beat keyline
                kf = next((s["keyframe_path"] for s in (beat.get("shots") or [beat])
                           if s.get("keyframe_path") and os.path.exists(s["keyframe_path"])), None)
                acc = text_overlay.accent_color(kf) if kf else None
            text_overlay.render_caption(beat["narration"], p, W, H, accent=acc, style=cap_style)
            cap_pngs.append(p)
    wm_png = text_overlay.render_watermark(
        wm_text, os.path.join(tmp, "wm.png"), W, H, language=doc.get("language"))

    # ---- 4) overlay captions+wm, mix narration/source audio, duck BGM ----
    timings["captions_seconds"] = round(time.perf_counter() - stage_started, 3)
    stage_started = time.perf_counter()
    nb = len(beat_spans)
    ncap = len(cap_pngs)                        # 0 when captions are off
    inputs = ["-i", body]                       # 0
    for p in cap_pngs:
        inputs += ["-i", p]                     # 1..ncap
    inputs += ["-i", wm_png]                    # ncap+1
    narr_base = ncap + 2
    for bs in beat_spans:
        inputs += ["-i", bs["beat"]["narration_audio"]]   # narr inputs
    sfx_idx = narr_base + nb
    has_source_audio = bool(source_audio_path and os.path.exists(source_audio_path))
    if has_source_audio:
        inputs += ["-i", source_audio_path]
    bgm_path = resolve_project_path(project_dir, doc.get("bgm_path"))
    has_bgm = bool(bgm_path) and os.path.exists(bgm_path)
    if bgm_path and not has_bgm:
        print(f"[assemble] configured background track is missing: {bgm_path}")
    bgm_idx = sfx_idx + int(has_source_audio)
    if has_bgm:
        loop_short_tracks = bool((pipeline_config().get("music_library") or {}).get("loop_short_tracks", True))
        bgm_duration = probe_dur(bgm_path)
        should_loop_bgm = loop_short_tracks and bgm_duration > 0 and bgm_duration < total - 0.25
        if should_loop_bgm:
            inputs += ["-stream_loop", "-1"]
            print(f"[assemble] looping short background track ({bgm_duration:.1f}s) to cover {total:.1f}s")
        inputs += ["-i", bgm_path]
    else:
        pipeline_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "pipeline.json")
        try:
            with open(pipeline_path, encoding="utf-8-sig") as handle:
                music_dir = (json.load(handle).get("music_library") or {}).get("path")
        except (OSError, ValueError, TypeError):
            music_dir = None
        if music_dir:
            print(f"[assemble] no bgm configured — choose a track from {music_dir} and set bgm_path in beats.json")
        else:
            print("[assemble] no bgm — narration mixed with source audio when available")

    chain, prev = [], "[0:v]"
    for i, bs in enumerate(beat_spans[:ncap]):
        s, e = bs["start"] + 0.2, bs["start"] + bs["dur"] - 0.1
        lbl = f"[v{i+1}]"
        chain.append(f"{prev}[{i+1}:v]overlay=0:0:enable='between(t,{s:.2f},{e:.2f})'{lbl}")
        prev = lbl
    if captions_from_srt:
        subtitle_file = os.path.basename(caption_ass_path or os.path.join(project_dir, "final.srt"))
        chain.append(f"{prev}subtitles=filename='{subtitle_file}'[vsrt]")
        prev = "[vsrt]"
    chain.append(f"{prev}[{ncap+1}:v]overlay=0:0[v]")

    # per-beat narration delayed to its start, then mixed
    nlabels = []
    for i, bs in enumerate(beat_spans):
        ms = int(bs["start"] * 1000)
        chain.append(f"[{narr_base+i}:a]adelay={ms}:all=1[n{i}]")
        nlabels.append(f"[n{i}]")
    chain.append(f"{''.join(nlabels)}amix=inputs={nb}:normalize=0:duration=longest,volume={voice_vol},apad,atrim=0:{total}[narrmix]")
    # a filter-output label can only be consumed once -> split narration in two
    if has_bgm:
        chain.append("[narrmix]asplit=2[narrA][narrB]")
        chain.append(f"[{bgm_idx}:a]atrim=0:{total},volume={music_vol},afade=t=out:st={max(total-2,0):.2f}:d=2[bgt]")
        chain.append("[bgt][narrA]sidechaincompress=threshold=0.02:ratio=12:attack=5:release=350[bgd]")

    if has_source_audio:
        chain.append(f"[{sfx_idx}:a]volume={source_audio_vol:.3f},atrim=0:{total},"
                     "asetpts=PTS-STARTPTS[sfxmix]")
        if has_bgm:
            # Keep the stereo bed first so a mono narration track does not force
            # the final mix to mono.
            chain.append(f"[bgd][narrB]amix=inputs=2:normalize=0:duration=longest,"
                         f"volume=1.4,atrim=0:{total}[musicmix]")
            bed = "[musicmix]"
        else:
            chain.append("[narrmix]pan=stereo|c0=c0|c1=c0[narrst]")
            bed = "[narrst]"
        chain.append(f"{bed}[sfxmix]amix=inputs=2:normalize=0:duration=longest,"
                         f"alimiter=limit=0.95:level=false,atrim=0:{total}[a]")
    elif has_bgm:
        # Keep the stereo bed first so a mono narration track does not force
        # the final mix to mono.
            chain.append(f"[bgd][narrB]amix=inputs=2:normalize=0:duration=longest,"
                         f"volume=1.4,atrim=0:{total}[a]")
    else:
        chain.append("[narrmix]anull[a]")
    filt = ";".join(chain)

    final = os.path.abspath(output_path) if output_path else os.path.join(project_dir, "final.mp4")
    encode = renderer_config()
    video_codec = encode.get("video_codec") or "libx264"
    audio_codec = encode.get("audio_codec") or "aac"
    encode_args = ["-c:v", video_codec, "-pix_fmt", "yuv420p"]
    if video_codec == "libx264":
        encode_args += ["-preset", str(encode.get("video_preset") or "fast"),
                        "-crf", str(encode.get("video_crf", 20)), "-threads:v", "2"]
    elif video_codec == "h264_nvenc":
        encode_args += ["-preset", str(encode.get("video_preset") or "p4"),
                        "-cq", str(encode.get("video_cq", 20))]
    audio_bitrate = encode.get("audio_bitrate")
    if audio_bitrate:
        encode_args += ["-b:a", str(audio_bitrate)]
    if encode.get("faststart", True):
        encode_args += ["-movflags", "+faststart"]
    ff(["-filter_complex_threads", "2", *inputs, "-filter_complex", filt, "-map", "[v]", "-map", "[a]",
        *encode_args, "-c:a", audio_codec, "-shortest", final], cwd=project_dir)
    timings["final_encode_seconds"] = round(time.perf_counter() - stage_started, 3)
    print("FINAL:", final, f"(~{total}s, {len(segs)} shots)")
    if doc.get("pipeline") == "local" and not captions_from_srt:
        from export_srt import run as write_srt
        write_srt(project_dir, beat_spans, W, H)
    timings["total_seconds"] = round(time.perf_counter() - started, 3)
    with open(final + ".timing.json", "w", encoding="utf-8") as handle:
        json.dump({"stills_renderer": stills_renderer if use_revideo else None,
                   "video_codec": video_codec, "video_seconds": total,
                   "timings": timings}, handle, indent=2)
    print("[assemble] wall timing:", json.dumps(timings))


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "tang-30s")
    output = next((arg for arg in sys.argv[2:] if not arg.startswith("--")), None)
    reuse = "--reuse-video" in sys.argv[2:]
    reuse_audio = "--reuse-source-audio" in sys.argv[2:]
    force_video = "--force-video" in sys.argv[2:]
    reuse_revideo = "--reuse-revideo" in sys.argv[2:]
    stills_renderer = next((arg.split("=", 1)[1] for arg in sys.argv[2:]
                            if arg.startswith("--stills-renderer=")), None)
    run(os.path.abspath(proj), output_path=output, reuse_video=reuse,
        reuse_source_audio=reuse_audio, force_video=force_video,
        reuse_revideo=reuse_revideo, stills_renderer=stills_renderer)
