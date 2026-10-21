# Visual sequence review — Sahara, mission-visual-v1

Reviewed 2026-10-13. Source: [master narration v1.2](../sahara-mission/master-narration.md) and its [research dossier](../sahara-mission/research-dossier.md). This is a shortened non-production direction/prompt acceptance case, explicitly requested by the user. No narration edit, production approval, timed audio, registered still or motion render is implied.

## Scene decisions and rhythm

1. **S01 — subject opening, extreme-wide high oblique landscape.** Lake shapes and dry extent establish the surprising actual subject before the task. People add no explanation. A sparse wide view gives the blue water motif space; it is an illustrative Ounianga-inspired vista, not an exact surveyed recreation.
2. **S02 — source mechanism, close schematic cutaway.** The hidden water-to-lake connection becomes visible through a connected layer and flow arrows. A narrator or engineer pointing at the lake would leave the mechanism hidden. Detail is reduced and a hold gives the label time. The cutaway is not a measured aquifer profile or proof of unlimited replenishment.
3. **S03 — intervention choice, medium three-quarter action.** Minh prioritizes the water map above seedlings. This is where a person's agency makes the audit decision tangible. Their expression/hands support the map, rather than a giant portrait replacing it. Minh is a one-off fictional design in this sample; no recurring-character sheet is required, and the cast spec appears only in this prompt.
4. **S04 — scale and cap, sparse quantity diagram.** The illustrative 100 km² × 0.3 m = 30 million m³/year relationship and bounded cap make lack of headroom legible. No figure is added for size or reaction. Assumption status and excluded additional costs remain explicit. A generous hold and clear unit diagram support several sentences instead of one image per number.
5. **S05 — persistent aftermath, quiet ground-level wide view.** Closed valve, installed pipe and stopped site show what does not reset after cancellation. They are the subject; a sad protagonist would shift attention from the infrastructure and obligation. The scene belongs to hypothetical branch A, without measured ecological-damage claims. The blue line now ends at a closed valve.
6. **S06 — connected systems, regional map/ecological pathway.** Narration first reorients into the separate B1 conditions. The map then shows the established Sahara-to-Amazon dust/nutrient link that must be considered, not a certain future change or failure causing this transport. Regional layout, pathway and olive receiving canopy widen the view beyond a local pipe. It does not depict a dying Amazon, a modern-monsoon forecast or precise future percentages.

The different views serve curiosity → mechanism → agency → scale → persistent state → wider-system understanding. They are not a required six-part recipe. Only one scene uses a person because only that decision needs visible agency here; the number is an observation, not a target ratio. Other topics may need very different cast usage, distances, densities and representations.

## Connections and knowledge checks

Water remains teal, terrain ochre and receiving vegetation olive; dark rounded contours and restrained cel shading define the shared Q-Version 2D world. The water motif links vista, section, allocation map, budget and closed valve. Before the ecological map, narration explicitly reorients the branch/scale; proximity in the edit is not claimed as a causal link. Geography and scale are checked at prompt level; generated accuracy is still untested.

Cast filtering is tested through both still and motion builders. Altering an absent cast spec does not change a prompt/fingerprint; a visible identity does. Environment-only exported scenes require no character stage or unavailable reference. `people_policy: contextual` can describe anonymous inhabitants without importing the protagonist; full-image reuse cannot erase people by switching to `none`.

## Validation status and limits

- Six actual compiler-generated prompt files and a [sample manifest](sample-manifest.json) exist, linked to the narration spans and primary subjects. They include varied framing, density, illustration type and purposeful hold/move plans.
- Eleven new functional tests pass, and the whole repository suite passes 81 tests. These validate routing, metadata, scoping and export behavior, not aesthetic quality.
- **Actual image generation is blocked:** the built-in imagegen tool returned HTTP 429 `usage_limit_reached`. No generated images are saved or claimed; all six assets remain `not_generated` in the manifest.
- Phone-size text/geography/style QA and continuous-motion QA have **not** run. In particular, S04's equation needs image-level readability checks, and S06's continent shapes/direction need visual inspection. A prompt's negative constraints do not establish that the image model follows them.
- The 3–10-second sample shot plans are visual QA planning bounds, not measured narration timing or a complete production edit. Develop the actual beat count/durations after approved TTS if this becomes an episode.
