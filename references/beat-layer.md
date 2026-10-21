# Beat and shot design for channel documentaries

Use the active imagegen/local FFmpeg workflow (optional Revideo): continuous off-screen narration, a researched visual bible, references for recurring characters and suitable related full-image reuse. Follow [image reuse](image-reuse.md); no cropping/enlargement creates alternate views. Legacy collage/poster arcs are archived, not current story defaults.

Write and review full narration before mapping beats. A beat changes understanding through this channel's documented event, real flow, tactical action or human-system comparison rather than filling a fixed duration. Follow the approved question, evidence-led progression, answer and relevant consequence. Structure and carrier follow the topic; no assignment, intervention, traveler or fixed chapter count is required.

Distinguish documented events, supported reconstruction and clearly illustrative examples. Only when a hypothetical scenario has been explicitly selected, distinguish its baseline, divergence and conditional consequences. Use `scenario_context` on beats/shots when needed to carry layer/branch/basis/uncertainty into prompts; see [evidence boundaries](historical-fiction.md). Never stage an illustration or hypothetical result as archival proof.

## Map narration to shots

After the narration is approved, divide it into beats. Preserve the approved story's order and distinguish invented encounters from documented historical events; a scene can map to several beats and shots. A beat may contain multiple shots when the visual needs another action or point of view. A scene is not the same as a shot, and neither is tied to a fixed duration. Keep the narration intact; do not squeeze it into clip duration. Every shot receives a duration within the configured 3–10 seconds and a readable primary idea: action, scale, mechanism, state or consequence. Read narration spans and neighboring context; a scene may serve several sentences without a character, and a complex idea may need several images.

Use [visual DNA](visual-dna.md), [visual direction skill](../skills/vox-visual-direction/SKILL.md) and optional [sequence notes](templates/visual-sequence.md). No fixed ratio, universal illustration template or compulsory protagonist applies. For each shot, specify useful fields:

- `scene`: location, focal subject, and the visual idea.
- `visual_intent` (optional): scene purpose, primary subject, representation and continuity rationale; these are open descriptive choices.
- `people_policy` (optional): no people, listed cast or authored contextual inhabitants; never insert the protagonist automatically.
- `characters` (optional): recurring character IDs visible in the shot; attach their approved reference images when generating the still.
- `in_scene_text`: exact, verified short wording for a natural sign, object, or map label; scene text is enabled by default. Use the channel language for explanatory labels and researched period-appropriate wording for actual signs or objects.
- `text_placement`: where and how the wording appears, readable at phone size and within the camera crop. Set `image_text_policy: none` on a shot when text would distract.
- `animation.start`: initial pose or state.
- `animation.keyframe` (optional): the frozen image moment for an important action that must be visible, such as marching or a bomb in descent. The still renderer applies camera movement and transitions only; the still itself must show the action.
- `animation.action`: the observable action/process or explanatory focus. A landscape or diagram may hold a meaningful state/relationship instead of character acting.
- `animation.end`: the outcome or payoff.
- `animation.camera`: one purposeful camera move or a locked camera.
- `animation.continuity`: identity, props, geography, or screen direction to preserve.
- `animation.framing` (optional): shot size and composition.
- `dur`: exact target clip length within the configured range.

Prefer previously created related full images using `reuse_image_from` and `reuse_reason` (see `image-reuse.md`). Generate a new still with the Codex imagegen skill when action, expression, setting, characters or visible facts change. Reused shots keep the original image and its baked text; no cropped or enlarged alternate views. Use `animation.keyframe` when an important action needs to be visible in the frozen frame; otherwise use the opening moment. The still renderer later applies camera movement and transitions to that still; it does not animate the people or objects. An authored scientific/state comparison can use an explanatory layout when needed; do not accidentally turn an actor's action sequence into a before-and-after storyboard. Choose a camera move that follows a decision, reveals geography, or brings a consequence into view. Keep shot directions concise and observable. Create/review references for recurring cast only when needed, before shots where they appear. Character identity does not fix composition, distance, pose or camera. Character-free maps, mechanisms and environments share the visual world independently.

## Keep the visuals connected to the evidence

The narrator is normally off-screen. A clearly illustrative person can make a decision or system easier to follow, but does not replace historical evidence. Use maps and simple visual explanations for geography, movement, supply, and chronology. Keep units, dates, direction, and cause/effect consistent across shots. Separate documented events, scientific conditions, scenario inputs, inferred results and reconstruction; preserve branch continuity through the aftermath.

For every documentary shot, check that:

1. The image serves its narration span and scene objective, with the discussed subject leading rather than a decorative protagonist.
2. The focal action and its result are readable, with concise in-scene text supporting the image; verify spelling, historical accuracy, and readability.
3. The action/state fits the researched baseline or explicitly hypothetical branch, with scale/time consistency; it does not fabricate testimony or treat conditional outcomes as fact.
4. Selected visual medium, color/exposure/texture, props, map orientation, object/branch state and transitions match the visual world; cast identity is checked only when visible.
5. The depiction is non-graphic and respectful; violence is not used as spectacle.
6. The camera movement helps explain the action and leaves enough time for the payoff.
7. Narration pace remains natural even if more shots are needed.

After imagegen creates the stills and the still renderer renders the shots, inspect them against these checks before registration and final assembly. A prompt or successful file export alone does not establish historical or visual accuracy.
