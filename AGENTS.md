# Vox Director — Agent Guide

This repository is an **agent skill**: a self-contained workflow that turns one
topic into a finished Vox-style paper-collage video (script → collage keyframes →
motion → voice-over → music → captions). It is not tied to any single assistant —
any coding agent that can read instructions and run scripts can drive it.

## How to use it (for the agent)

1. Read **`references/local-pipeline.md`** first. This checkout does not call
   Atlas for stills, video, or narration.
2. Pick the channel before any writing. The roster is **`config/channels.json`**.
   Bind it with `python scripts/channels.py bind <channel-id> <slug>`.
   The episode folder is `D:\Vox-Video\<channel>\<slug>`. Do not write under `out/`.
   Narration language, promise, lanes, avoid list, and VoiceStudio profile all
   come from that channel. Do not mix channels in one film.
3. Research the episode before writing it. `python scripts/research_youtube.py`
   reads `YOUTUBE_API_KEY` from `.env` and saves a public search scan in that
   episode's `research/` folder. Read the report for the question, the opening,
   and the gap. Do not copy titles, scripts, or thumbnails, and do not treat
   views as evidence. Verify facts with primary sources. Steps:
   `references/topic-research.md`.
4. Read **`SKILL.md`** for the beat map, the two human approval gates, and the
   collage prompt rules. (`SKILL.zh.md` is the same skill in Chinese.)
5. Before writing any prompt, read **`references/`** (prompt structures, the
   vocabulary/theme bank, and the narrative-beat library).
6. Work one episode at a time in its `D:\Vox-Video\<channel>\<slug>` folder, driven by
   `beats.json` with `"pipeline": "local"` and a `channel_id`. First
   `plan_runtime.py --minutes <7-20>`, then media stages:
   `codex_prompts.py` (Codex renders the stills) → `muse_pack.py` (you animate
   in Muse.ai) → `voicestudio_tts.py` → `assemble.py` (also writes `final.srt`)
   → `research_packaging.py` (titles, thumbnails, description openings, tag pool)
   → `export_youtube.py` (Codex renders thumbnails, then the upload package).
   Packaging rules: `references/packaging-research.md`. Do not copy titles or thumbnails.

## Requirements

- Codex (or another agent) that can generate images and save them to disk
- Muse.ai, used by hand for image-to-video
- VoiceStudio open on this machine — local API at `http://localhost:3900`
- `ffmpeg` + `ffprobe`
- Python 3 with `pillow`

## Agent notes

- **Claude Code** auto-loads this as a skill from `SKILL.md`'s frontmatter — just
  ask for a "vox video".
- **Codex / other agents**: follow `SKILL.md` as your instructions; this
  `AGENTS.md` is your entry point.
