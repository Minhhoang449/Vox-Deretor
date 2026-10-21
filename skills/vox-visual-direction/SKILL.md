---
name: vox-visual-direction
description: Direct channel-configured image generation and explanatory graphics using the selected channel visual grammar.
---

# Documentary Visual Direction

Use [visual DNA](../../references/visual-dna.md), [channel documentary DNA](../../references/scripting-dna.md) and the live profile's visual_grammar. Select the representation from the researched question and this channel's format. For new episodes use [imagegen stills](../../references/imagegen-stills.md) and the live `visual_dna`: all six channels use original Chibi 2D frames. Follow [chibi historical visual direction](../../references/chibi-historical-visual-dna.md) for those overrides; no compulsory mission, traveler or hypothetical branch.

Use [viewer guidance](../../references/viewer-guidance.md) to align the opening frame with the title/thumbnail promise and to mark meaningful changes in the viewer's understanding. Let maps, stills and diagrams clarify the narrated state; do not create arbitrary interrupts, visual claims or motion that the evidence and narration do not support.

Read actual narration spans and neighboring context before choosing images. Identify the scene's job and the subject that explains it. A scene may span several sentences or reveal a relationship; do not illustrate each sentence literally. Favor the discussed geography, mechanism, transformation or aftermath when that is the information. Use cast only for meaningful action, emotion, viewpoint or story value. No fixed character ratio, mandatory sequence of visual types or universal composition applies.

Vary viewpoint, distance, layout and detail for each purpose while preserving geography, objects, time and factual state and maintaining visual continuity across generated stills. People use the live original Chibi proportions in new episodes. Identity consistency does not lock pose/composition or require appearances; do not put the whole cast roster into every prompt. For recurring cast use [character design](../agentara-video-character-design/SKILL.md) only for their relevant scenes.

Record useful decisions with [sequence notes](../../references/templates/visual-sequence.md), then [beat layer](../../references/beat-layer.md) and [animation direction](../../references/animation-direction.md). Optional `visual_intent` carries purpose/subject/representation. `characters` and optional `people_policy` describe actual human presence; `scenario_context` preserves factual versus conditional branches. Baseline or future maps are not measured projections merely because they look precise.

Follow [local pipeline](../../references/local-pipeline.md): approved narration, beats/visual bible and measured TTS before production images. Explicitly authorized shortened QA samples are non-production tests. Export prompts through codex_prompts.py and use Codex imagegen in the configured channel style; new episodes do not search for or use video montage. Ground every scene in verified research. Keep provenance internal; do not add user-visible AI/illustration disclosure labels. Attach relevant references, preserve full-image reuse rules and inspect actual outputs. Reuse may account for no more than 35% of an episode's scene shots: count shots with `reuse_image_from` over all scene shots, rounding the maximum down to a whole shot. Reuse any one original image no more than twice after its first appearance, counting every shot that resolves to that original source, including reuse chains. Existing approved images are not regenerated merely because this guidance changes.

Review the sequence for meaningful rhythm, explanatory clarity, subject accuracy, text/phone readability, style and transition continuity. Justify a character's value instead of counting appearances. Distinguish prompt export, inspected stills and tested rendered motion in the report. Do not claim quality from metadata or successful file creation alone.

## Stills that explain the change

Choose framing for the information needed: orient the place, expose a hidden relationship, show a supported action/state, or reveal its consequence. This is not a compulsory sequence. A new still must contribute information; camera movement directs attention but cannot supply a missing physical change. Use the configured style for scene reconstruction, clear graphics for diagrams, approved image-reuse rules and balanced still camera. The renderer adds camera movement but does not animate physical action or character motion. Use the stills renderer for new episodes and inspect actual output text. Preserve recorded styles in existing approved episodes.
