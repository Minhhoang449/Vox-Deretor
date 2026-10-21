# Imagegen stills workflow

Revision: imagegen-stills-v1. User instruction dated 2026-10-19. This is the default visual workflow for new episodes across all six active channels. It replaces the Montage/video retrieval stage for new work. Existing projects retain their recorded visual settings unless a visual revision is requested.

## Scope

- Build the episode from still images generated with Codex imagegen in the same shared Chibi 2D prompt/look across all six channels: bold clean dark outlines, warm luminous colors, gentle painterly texture, restrained cel shading and clear staging. Use compact expressive Chibi characters when they explain meaningful action, and keep objects, environments, maps and diagrams in the same illustrated finish. Adapt scenes and palette to episode evidence; a reference image sets style only, not a reusable composition. Do not search for or use video clips or video montage.
- Use researched evidence to ground each image's place, period, physical details and visible action. Imagegen creates illustrative reconstructions; it does not create evidence or prove that a depicted event occurred.
- Use clear sourced maps, cross-sections or mechanism diagrams when they explain something a photograph cannot show. Do not invent data, archival marks, quotations, documents, signage or evidence.
- Text and diagram labels remain supported when they help explain the scene. Put every intended phrase in `in_scene_text` with its `text_placement`; keep it concise, localized, sourced and exact. Use `image_text_policy: none` when text would distract. Do not ask imagegen to invent wording or data.
- Do not add user-visible AI/illustration disclosure labels to generated stills or rendered video. Record factual role and provenance in internal research and asset records instead. This does not prohibit useful, sourced text in maps, signs or diagrams.
- Keep the approved story and actual narration as the source of the beat map. A prompt is not an image; inspect the generated still itself.

## Order of work

1. Research and select a fresh topic. Draft continuous narration, complete story and retention review, secure approval of the actual wording and record approval.
2. Build the visual bible and beat map from the approved narration. Plan meaningful passage changes, geographic orientation, mechanisms and supported actions. Do not invent actions absent from the record.
3. Generate approved native-speed narration, measure its duration and listen to the review copy before generating episode stills.
4. Use `python scripts/codex_prompts.py "<episode>"` to export image prompts and a manifest. The workflow performs no Montage or footage searches. Generate with Codex imagegen in the channel's configured style; preserve the exact prompt/manifest mapping and save paths. Chibi still frames do not animate physical action; keyframe changed actions as distinct images.
5. Review each still for factual grounding, representation, natural anatomy, materials, geography, time and action. For planned text and diagrams, visually check exact spelling, labels, data, placement, phone-size readability and the intended camera crop; this is a human visual check, not automated OCR. Revise prompts/images that imply unsupported evidence or events. Do not stretch or animate physical action that is not present in the image.
6. Register and inspect the images using the existing image registration command, then review full-image reuse limits in `image-reuse.md`. Keep disclosure in internal provenance records; do not render AI/illustration disclosure labels over the images or video.
7. Assemble with `pipeline: local` and `visual_mode: revideo_stills`, using the existing FFmpeg/NVENC still renderer, two workers, balanced camera, content cache and caption QA. Camera movement may direct attention but cannot add a physical event.
8. Inspect the rendered sequence for visual fit, sourced diagram text, transitions, crop, captions, audio and cache correctness. Record remaining limits before delivery.

The former `footage-first.md`/Montage route remains only for existing episodes whose saved workflow explicitly uses it. It does not govern new bindings.
