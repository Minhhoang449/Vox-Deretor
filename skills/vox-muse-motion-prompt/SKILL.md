---
name: vox-muse-motion-prompt
description: >
  Maintain explicitly requested Muse text/reference-to-video projects with Chibi
  scene prompts, causal action, camera direction and approved character references.
  This legacy backend does not define new-episode storytelling DNA.
---

# Vox Muse Motion Prompt

> Legacy backend only: current production uses Codex imagegen stills and FFmpeg/NVENC movement by default (Revideo optional). Use Muse only for an existing Muse project or an explicit request. Current content follows `references/scripting-dna.md`; this backend does not supply a separate story format.

Use this skill only within that selected legacy backend. The repository's `scripts/animation_prompts.py` is the prompt composer and `scripts/muse_pack.py` exports the episode package. Muse generation is manual; do not claim the scripts create or inspect the media.

## Required inputs

Before composing, confirm the approved narration, researched visual bible, shot's role in the narration, exact `dur` (3–10 seconds by default), visible character IDs, and approved character references. The episode must use `animation_style: chibi-2d` unless project configuration explicitly expands the supported styles.

Apply [visual DNA](../../references/visual-dna.md): landscapes, maps, cutaways, processes and consequences can be the primary subject. Empty visible-cast IDs require no character stage, even if unused characters exist in the bible. Only visible cast enter prompts and reference requirements. `visual_intent` and optional `people_policy` carry the authored choice; no quota or per-sentence template applies.

The shot data needs:

- `scene`: what the viewer sees and why it belongs at this point in the story.
- `characters`: only the recurring characters visible in the shot.
- `animation.start`: the stable initial pose/state.
- `animation.action`: one observable action; name what moves, direction, cause, and sequence.
- `animation.end`: the readable result or payoff.
- `animation.camera`: one move and what it follows/reveals, or locked-off.
- `animation.continuity`: identity, props, location, geography, and screen direction to preserve.
- `dur`: exact clip duration.

For recurring characters, follow `skills/agentara-video-character-design/SKILL.md`. Generate and approve the Muse character reference sheet before exporting shot prompts. The shot prompt should name only relevant reference assets and say to use them for identity while designing a new scene. Do not use a scene keyframe; Muse creates the setting, composition, and motion from text plus character references.

## Prompt construction rules

1. Write one continuous shot around a primary idea: action, process, explanation or readable hold. Use scene purpose and reading time to decide whether causal steps need separate clips or one authored diagram; do not split every narration sentence automatically.
2. Make motion specific and physically legible: actor/object, start state, direction, interaction, and settled end state. Avoid vague verbs such as “moves dramatically.”
3. Give one camera instruction that supports the explanation: follow a moving object, reveal a map route, pan between a blocked and open path, push in on a documented choice, or hold. Do not add arbitrary shake, zooms, drift, or a second move.
4. Describe Chibi identity plainly: rounded oversized head, compact body, bold clean outline, expressive simple face, flat color, restrained cel shading. Lock the approved face, hair, proportions, clothing, palette, and props.
5. Ground actual clothing, tools, landscapes and map direction in research. Mark uncertain reconstruction and hypothetical branch details. Use `scenario_context` for baseline/intervention/aftermath when needed; do not fabricate real-person testimony or present inference as fact.
6. Keep war depiction non-graphic and respectful. Do not glorify weapons, turn victims into a hook, or stage an explosion as spectacle. Prefer the relevant decision, movement, terrain, logistics, civilian consequence, or aftermath.
7. Require a silent clip: no speech, lip-sync, narration, or music. Preserve exact authored `in_scene_text` / `text_placement` or an explicit text-free policy; labels must not masquerade as archival evidence.
8. State exact duration and aspect ratio. Do not ask for loops, extra edits, extensions, montage, or default-length padding.

## Export and review

Run `python scripts/muse_pack.py <episode> --characters-only` to produce the character reference prompts. After generating and approving the references in Muse, save them at the paths in `muse/characters/INDEX.md` or record Muse asset IDs in `beats.json`. Then run `python scripts/muse_pack.py <episode>` to export shot prompts and metadata.

Before registration, inspect every generated clip against the prompt, visual bible, historical sources, duration, and silent-audio requirement. Regenerate any clip with identity drift, unclear action, incorrect geography, invented evidence, graphic treatment, or wrong duration. A prompt cannot guarantee the generated result.

See `references/animation-direction.md`, `references/beat-layer.md`, and `references/war-storytelling.md` for the project-wide standards.
