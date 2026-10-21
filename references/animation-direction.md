# Animation direction for channel documentary worlds

Read [visual DNA](visual-dna.md) and use [vox-visual-direction](../skills/vox-visual-direction/SKILL.md). For new episodes follow [imagegen stills](imagegen-stills.md): all six active channels use original Chibi 2D after narration approval and audio review; do not use video montage. Actively plan meaningful human action where it explains the passage; objects, maps and diagrams can lead when clearer. No fixed character ratio applies. The still renderer moves the camera but does not animate physical action or character motion.

Ground prompts in the researched evidence, then use Codex imagegen for original stills and needed references. Suitable related shots reuse full images under [image reuse](image-reuse.md), without cropped/enlarged alternate views. FFmpeg/NVENC adds camera movement and transitions by default; Revideo is optional. The prompt exporter does not call imagegen or certify quality.

## Visual world before cast

After narration approval, define generated-still color, exposure, texture, geographical/object/time continuity and scale rules in `visual_bible`. Detail density, viewpoint and illustration type may vary. Landscape, map, cutaway, built system or ecosystem scenes are complete subjects, not backgrounds waiting for a character.

Define stable IDs/specs/references only for recurring cast used by the story. Historical traits need sources or reconstruction status; invented cast follow [fiction boundaries](historical-fiction.md). Reuse an approved reference or create/review one before scenes in which that cast appears. References establish identity, never required presence, pose, frame occupancy or composition. A character-free sequence requires no character-reference stage. A one-off figure can use its visual-bible specification without a separate turnaround.

## Author a state or relationship plus a camera plan

One readable idea can be an action, geography, mechanism, comparison, natural process or consequence. A scene may span multiple sentences; do not map every spoken sentence to a new image or reaction shot. Use [sequence notes](templates/visual-sequence.md) when useful, then fields appropriate to the shot:

- `scene`: actual primary subject/state and relevant context.
- `visual_intent` (optional text/object): purpose, subject, representation, hierarchy/detail and transition rationale. Types are descriptive choices, not a fixed enum/template.
- `characters`: recurring IDs actually visible. Optional `people_policy`: `none`, `listed` or `contextual` for explicitly described anonymous inhabitants. Empty/missing IDs keep legacy character-free behavior unless contextual people are authored.
- `scenario_context`: evidence/reconstruction notes where useful; baseline/divergence/conditional aftermath only for an explicitly selected hypothetical scenario.
- `in_scene_text` / `text_placement`: exact useful wording and readable placement, or shot `image_text_policy: none` when text distracts.
- `animation.start` / `keyframe`: authored state/relationship or precise frozen action. Anatomy and body-language requirements apply only when people appear.
- `animation.action` / `end`: the process/focus and visual payoff; a hold or revealed relationship is valid for explanation. Still camera motion does not animate roots, water, construction or vegetation changing over time.
- `animation.camera` / `framing` / `continuity`: appropriate move/hold, viewpoint/distance, world/object state and nearby-scene connection; character identity only when present.
- `dur`: within configured 3–10 seconds. Narration pace and image-reading time determine the number of shots.

### Balanced still camera movement

The default FFmpeg renderer keeps pan/zoom available but chooses generic camera plans from the scene purpose, readable layout and authored direction rather than a fixed shot-index cycle. Scene/framing text can steer a wide street or room toward pan, a tall facade or stair toward tilt, and a close-up/document toward hold. These are text hints, not semantic image detection; inspect the actual crop and motion before delivery. Alternate directions, keep movement subtle, and give dense scenes reading time. Parallax is not enabled; it requires separately prepared image layers.

For new shots, set `animation.camera: "auto"` when this balanced selection is suitable. Specific authored camera strings are preserved; only `auto` and the four recognized generic legacy templates are balanced automatically. Set `animation.camera_policy: "preserve"` to retain any original direction, or `"balanced"` to explicitly let the renderer select a move for that shot. A project-wide `renderer.stills_camera_policy: "preserve"` disables automatic balancing unless a shot explicitly requests it. The visual render report records the effective camera for each shot.

For a map or cutaway, author a readable relationship and use a calm hold when the viewer needs to read it. For a landscape, a subtle move can reveal extent. Character shots can use any suitable distance or angle; their reference sheet does not set the camera. These choices come from purpose rather than a repeating scene-template cycle.


Plan related full-image reuse with `reuse_image_from` and `reuse_reason` (see `image-reuse.md`). Export one still prompt per original image with `python scripts/codex_prompts.py <episode>`. Use the Codex `imagegen` skill / `image_gen` tool to create the frame, attach the approved character reference listed in the manifest, and save the image at the exact `save_as` path. For action-led shots, set `animation.keyframe` so the still freezes the most readable instant of the action. The image depicts one authored state/relationship. An explicitly designed comparison or cutaway may show explanatory states; do not accidentally combine multiple actor moments into a storyboard. The still renderer later applies only the camera move and transition. Do not ask the image generator to render a full sequence or video.

For all war visuals, keep harm non-graphic and respectful. Do not glorify weapons or depict an explosion as spectacle. Show historically relevant decisions, movement, terrain, logistics, or consequences; distinguish documented events from reconstruction. Avoid fake archival documents, invented insignia, subtitles, logos, watermarks, or generated speech/music. Include brief verified in-scene text by default, with exact wording in `in_scene_text`; do not present illustrative labels as authentic quotations or archival evidence. Render only the specified text and inspect spelling and readability before approval. Use the channel language for explanatory labels and researched period-appropriate wording for actual signs or objects.

## Inspect and register

Check each generated still against its scene purpose, actual primary subject, shared visual world, scale/branch, explanatory readability and text rules. Check character identity only when the character is visible; also inspect unwanted appearances and sequence transitions. Regenerate any mismatch. After approved stills are saved to the manifest paths, run `python scripts/codex_prompts.py <episode> --register`, then assemble new episodes with visual_mode: revideo_stills. Existing projects retain their recorded route. Inspect continuous playback of the still render for motion artifacts, awkward crops, transitions and timeline coverage. A valid prompt or successful file export alone does not establish historical or visual accuracy.


Purpose-led camera fields and reuse QA are specified in [render defaults](render-defaults.md#camera-theo-mục-đích-và-qa-tái-dùng--16102026). Read/compare/orient default to hold; follow needs direction; explicit camera instructions remain available. Motion is not a substitute for a new physical state.
