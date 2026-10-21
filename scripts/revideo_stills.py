#!/usr/bin/env python3
"""Render an episode's still keyframes as a moving, softly transitioned film with Revideo."""
import json
import os
import shutil
import subprocess
import sys

from cache_keys import file_fingerprint, stable_hash

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUNNER = os.path.join(ROOT, "scripts", "revideo_render.mjs")


def render_cache_fingerprint(project_dir, segments, width, height, fps):
    """Hash every visual input and render setting that can change the Revideo MP4."""
    config_path = os.path.join(ROOT, "config", "pipeline.json")
    with open(config_path, encoding="utf-8-sig") as handle:
        pipeline = json.load(handle)
    revideo = pipeline.get("revideo") or {}
    revideo_root = os.environ.get("REVIDEO_ROOT") or revideo.get("root") or r"D:\Coder\Revideo"
    tool_files = [
        __file__,
        RUNNER,
        config_path,
        os.path.join(revideo_root, "package.json"),
        os.path.join(revideo_root, "package-lock.json"),
    ]
    inputs = []
    for segment in segments:
        image = segment.get("image")
        if not image or not os.path.isfile(image):
            raise SystemExit(f"Keyframe not found for render fingerprint: {image}")
        inputs.append({
            "image": file_fingerprint(image, include_content=True),
            "duration": float(segment["dur"]),
            "camera": segment.get("camera") or "locked-off",
            "beat_id": segment.get("beat_id", ""),
            "shot_id": segment.get("shot_id", ""),
        })
    return stable_hash({
        "schema": 1,
        "project": os.path.abspath(project_dir),
        "size": {"width": int(width), "height": int(height), "fps": int(fps)},
        "revideo_config": revideo,
        "segments": inputs,
        "renderer_files": [file_fingerprint(path, include_content=True) for path in tool_files],
    })


def write_project(project_dir, segments, width, height, fps):
    render_dir = os.path.join(project_dir, "revideo")
    src_dir = os.path.join(render_dir, "src")
    os.makedirs(src_dir, exist_ok=True)
    image_dir = os.path.join(project_dir, "keyframes")
    timeline = []
    current = 0.0
    last_beat = None
    for index, seg in enumerate(segments):
        beat_id = seg.get("beat_id", "")
        timeline.append({
            "index": index,
            "image": os.path.basename(seg["image"]),
            "start": round(current, 6),
            "duration": float(seg["dur"]),
            "camera": seg.get("camera") or "locked-off",
            "beatId": beat_id,
            "beatStart": beat_id != last_beat,
        })
        current += float(seg["dur"])
        last_beat = beat_id
    config_path = os.path.join(ROOT, "config", "pipeline.json")
    with open(config_path, encoding="utf-8-sig") as f:
        render_config = json.load(f).get("revideo", {})
    data = {"width": int(width), "height": int(height), "fps": int(fps),
            "transitionSeconds": float(render_config.get("transition_seconds", 0.46)),
            "beatTransitionSeconds": float(render_config.get("beat_transition_seconds", 0.68)),
            "duration": round(current, 6), "segments": timeline}
    with open(os.path.join(src_dir, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    scene = r'''import {makeScene2D, Node} from '@revideo/2d';
import {waitFor} from '@revideo/core';
import data from './timeline.json';

type Segment = {index: number; image: string; start: number; duration: number; camera: string; beatId: string; beatStart: boolean};
const timeline = data as {width: number; height: number; fps: number; duration: number; transitionSeconds: number; beatTransitionSeconds: number; segments: Segment[]};
const clamp = (v: number) => Math.max(0, Math.min(1, v));
const smooth = (v: number) => {const p = clamp(v); return p * p * (3 - 2 * p);};

class StillFilm extends Node {
  private imageCache = new Map<number, ImageBitmap>();
  private pendingImages = new Map<number, Promise<ImageBitmap>>();

  constructor(private clock: () => number) {super({});}

  private async getImage(index: number): Promise<ImageBitmap> {
    const cached = this.imageCache.get(index);
    if (cached) {
      this.imageCache.delete(index);
      this.imageCache.set(index, cached);
      return cached;
    }
    const pending = this.pendingImages.get(index);
    if (pending) return pending;

    const segment = timeline.segments[index];
    const loading = (async () => {
      const response = await fetch('/' + encodeURIComponent(segment.image));
      if (!response.ok) throw new Error('Could not load still image: ' + segment.image);
      return createImageBitmap(await response.blob());
    })();
    this.pendingImages.set(index, loading);
    try {
      const bitmap = await loading;
      this.pendingImages.delete(index);
      this.imageCache.set(index, bitmap);
      while (this.imageCache.size > 3) {
        const oldest = this.imageCache.keys().next().value;
        if (oldest === undefined) break;
        const evicted = this.imageCache.get(oldest);
        this.imageCache.delete(oldest);
        evicted?.close();
      }
      return bitmap;
    } catch (error) {
      this.pendingImages.delete(index);
      throw error;
    }
  }

  protected async draw(ctx: CanvasRenderingContext2D) {
    const t = Math.max(0, Math.min(timeline.duration, this.clock()));
    const segments = timeline.segments;
    let index = segments.length - 1;
    for (let i = 0; i < segments.length; i++) {
      if (t < segments[i].start + segments[i].duration) {index = i; break;}
    }
    const current = segments[index];
    ctx.save();
    ctx.translate(-timeline.width / 2, -timeline.height / 2);
    ctx.fillStyle = '#171713';
    ctx.fillRect(0, 0, timeline.width, timeline.height);

    const transitionDuration = current.beatStart ? timeline.beatTransitionSeconds : timeline.transitionSeconds;
    const sinceCut = t - current.start;
    if (index > 0 && sinceCut >= 0 && sinceCut < transitionDuration) {
      const prior = segments[index - 1];
      const progress = smooth(sinceCut / transitionDuration);
      const priorImage = await this.getImage(prior.index);
      const currentImage = await this.getImage(current.index);
      this.drawShot(ctx, prior, priorImage, prior.duration, 1, 0);
      this.drawShot(ctx, current, currentImage, sinceCut, progress, (1 - progress) * 0.014);
    } else {
      const currentImage = await this.getImage(index);
      this.drawShot(ctx, current, currentImage, t - current.start, 1, 0);
    }

    const fadeIn = smooth(t / 0.48);
    const fadeOut = 1 - smooth((t - (timeline.duration - 0.58)) / 0.58);
    const opacity = Math.min(fadeIn, fadeOut);
    if (opacity < 0.999) {
      ctx.globalAlpha = 1 - opacity;
      ctx.fillStyle = '#10100e';
      ctx.fillRect(0, 0, timeline.width, timeline.height);
    }
    ctx.restore();
  }

  private drawShot(ctx: CanvasRenderingContext2D, segment: Segment, image: ImageBitmap,
                   localTime: number, alpha: number, transitionZoom: number) {
    if (!image) return;
    const p = clamp(localTime / Math.max(0.001, segment.duration));
    const camera = segment.camera.toLowerCase();
    let fromZoom = 1.025, toZoom = 1.055, dx = 0, dy = 0;
    if (/locked|hold|static/.test(camera)) {fromZoom = 1; toZoom = 1;}
    else if (camera === "gentle zoom-out") {fromZoom = 1.055; toZoom = 1.025;}
    else if (camera === "gentle zoom-in") {fromZoom = 1.025; toZoom = 1.055;}
    else if (/pull.?back|pull out|crane up|reveal/.test(camera)) {fromZoom = 1.065; toZoom = 1.025;}
    else if (/push.?in|zoom/.test(camera)) {fromZoom = 1.018; toZoom = 1.072;}
    else {fromZoom = 1.025; toZoom = 1.052;}

    const eased = smooth(p);
    const distance = Math.min(34, timeline.width * 0.018);
    if (/left to right|pan right|track right|lateral|follow|arc/.test(camera)) dx = -distance * eased;
    else if (/right to left|pan left|track left/.test(camera)) dx = distance * eased;
    else if (/pan|track/.test(camera)) dx = -distance * 0.65 * eased;
    if (/tilt down|camera down|lower/.test(camera)) dy = -distance * 0.55 * eased;
    else if (/tilt up|crane up|camera up/.test(camera)) dy = distance * 0.55 * eased;

    const zoom = fromZoom + (toZoom - fromZoom) * eased + transitionZoom;
    const cover = Math.max(timeline.width / image.width, timeline.height / image.height);
    const drawWidth = image.width * cover * zoom;
    const drawHeight = image.height * cover * zoom;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.translate(timeline.width / 2 + dx, timeline.height / 2 + dy);
    ctx.drawImage(image, -drawWidth / 2, -drawHeight / 2, drawWidth, drawHeight);
    ctx.restore();
  }
}

export default makeScene2D('StillFilm', function*(view) {
  view.add(new StillFilm(() => view.globalTime()));
  yield* waitFor(timeline.duration);
});
'''
    project = r'''import {makeProject} from '@revideo/core';
import scene from './scene';
import data from './timeline.json';

export const project = makeProject({
  name: 'VoxDirectorStillFilm',
  scenes: [scene],
  settings: {
    shared: {background: '#171713', range: [0, data.duration], size: {x: data.width, y: data.height}},
    preview: {fps: data.fps, resolutionScale: 1},
    rendering: {exporter: {name: '@revideo/core/ffmpeg'}, fps: data.fps, resolutionScale: 1, colorSpace: 'srgb'},
  },
});
export default project;
'''
    with open(os.path.join(src_dir, "scene.ts"), "w", encoding="utf-8") as f:
        f.write(scene)
    with open(os.path.join(src_dir, "project.ts"), "w", encoding="utf-8") as f:
        f.write(project)
    return render_dir, image_dir


def render(project_dir, segments, width, height, fps, output_path):
    if not segments:
        raise SystemExit("Revideo needs at least one registered keyframe.")
    for seg in segments:
        if not os.path.isfile(seg["image"]):
            raise SystemExit(f"Keyframe not found: {seg['image']}")
    project_dir = os.path.abspath(project_dir)
    render_dir, image_dir = write_project(project_dir, segments, width, height, fps)
    config_path = os.path.join(ROOT, "config", "pipeline.json")
    with open(config_path, encoding="utf-8-sig") as handle:
        revideo_config = json.load(handle).get("revideo") or {}
    revideo_root = os.environ.get("REVIDEO_ROOT") or revideo_config.get("root") or r"D:\Coder\Revideo"
    node = os.path.join(revideo_root, ".tools", "node-v22.23.3-win-x64", "node.exe")
    if not os.path.isfile(node):
        node = "node"
    env = os.environ.copy()
    ffmpeg_setting = str(revideo_config.get("ffmpeg_path") or "ffmpeg")
    ffprobe_setting = str(revideo_config.get("ffprobe_path") or "ffprobe")
    env.update({
        "REVIDEO_ROOT": os.path.abspath(revideo_root),
        "REVIDEO_PROJECT_ROOT": render_dir,
        "REVIDEO_PUBLIC_DIR": image_dir,
        "REVIDEO_OUT_FILE": os.path.abspath(output_path),
        "REVIDEO_WORKERS": os.environ.get(
            "REVIDEO_WORKERS", str(revideo_config.get("workers", 2))
        ),
        "REVIDEO_GPU_ACCELERATION": "true" if revideo_config.get("gpu_acceleration", True) else "false",
        "REVIDEO_FFMPEG_PATH": shutil.which(ffmpeg_setting) or ffmpeg_setting,
        "REVIDEO_FFPROBE_PATH": shutil.which(ffprobe_setting) or ffprobe_setting,
        "REVIDEO_VIDEO_CODEC": str(revideo_config.get("video_codec") or "h264_nvenc"),
        "REVIDEO_VIDEO_PRESET": str(revideo_config.get("video_preset") or "p4"),
        "REVIDEO_VIDEO_CQ": str(revideo_config.get("video_cq", 20)),
        "DISABLE_TELEMETRY": "true",
        "PUPPETEER_CACHE_DIR": os.path.join(os.path.abspath(revideo_root), ".cache", "puppeteer"),
        "TEMP": os.path.join(render_dir, ".cache", "tmp"),
        "TMP": os.path.join(render_dir, ".cache", "tmp"),
    })
    os.makedirs(env["TEMP"], exist_ok=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"[revideo] rendering {len(segments)} stills at {width}x{height}/{fps}fps")
    subprocess.run([node, RUNNER], cwd=render_dir, env=env, check=True)
    if not os.path.isfile(output_path):
        raise SystemExit(f"Revideo completed without producing {output_path}")


if __name__ == "__main__":
    raise SystemExit("Call render() through scripts/assemble.py so the approved beat timing is preserved.")
