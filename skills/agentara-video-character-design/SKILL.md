---
name: vox-character-reference
description: Design an approved recurring character specification and episode-style reference sheet for a narrated Vox-Deretor episode. Use when a character appears across multiple scenes, or when the user asks for character consistency, a turnaround, or a character sheet.
metadata:
  source: agentara/skills video-character-design, adapted for Vox-Deretor
---

# Vox-Deretor Character Reference

This project uses an off-screen narrator over original Chibi 2D educational stills and explanatory graphics. A recurring character is one possible visual anchor, never a compulsory subject or presenter. Read [visual DNA](../../references/visual-dna.md); identity consistency applies only when the character is visible.

## When to use

Use this skill when a character returns across multiple shots or when stable identity is important to the episode. For a one-off figure, use the episode's `visual_bible` without creating a separate sheet. New episode references use the live channel's original Chibi 2D proportions, with period/place-specific clothing and props supported by research. Preserve recorded legacy styles. The production target is a needed imagegen character reference followed by only missing original imagegen stills and suitable related full-image reuse, animated by FFmpeg/NVENC by default (optional Revideo).

## Workflow

1. Wait until the continuous narration is approved. Read the approved story and inspect the episode's existing character specs and storyboard assets, plus any relevant reference images supplied by the user.
2. Reuse an existing approved character spec or sheet when it matches. Do not redesign an established character without a reason.
3. Draft `characters/{slug}.md` in the channel's language. Include the character's story role, whether the person is fictional or documented, observable identity and proportions, hair and face, wardrobe and palette, useful expressions and poses, recurring props, continuity rules, references, and any uncertain details. Mark hypothetical traits as design choices, not facts about a real person.
4. Include a short identity description and relative `reference_image` path in the episode's `visual_bible.characters` entry. Make the spec part of the story brief/visual bible approval gate; do not generate a reference sheet before the design is approved.
5. After approval, reuse a user-approved reference sheet if one matches the spec. Otherwise use the Codex `imagegen` skill to create a consistent turnaround with front, three-quarter, side, and back views plus relevant expressions or props; use a plain background and omit labels, text, and decorative layout.
6. Inspect the sheet against the approved spec. Correct identity, proportions, outfit, or prop mismatches before using it as a reference for scene stills. Save the approved sheet at the character's `reference_image` path inside the episode folder.
7. Keep the prompt files and approved reference asset under the episode folder, never in the repository's `out/` directory. Do not overwrite an approved sheet without a requested revision; use a versioned filename for alternatives.

## Continuity rules

- Match face, hair, silhouette, body proportions, clothing, palette and meaningful props across appearances. Do not copy the reference pose, camera, frame occupancy or layout; vary these for each scene's purpose.
- Attach the approved character reference only to imagegen shots where that character actually appears. A map, environment or mechanism-only shot does not inherit cast specs or a character reference. Use it only for identity; generate the scene composition from the shot prompt.
- Do not invent historical clothing, insignia, or cultural details. Follow the episode research and mark reconstructions in the visual bible.
- A character sheet improves continuity but cannot guarantee perfect identity across every frame. Inspect every still before registering it in `beats.json`.

## Source and adaptation

This project-local skill adapts Agentara's `video-character-design` skill. The upstream copy and MIT notice are kept beside this file; project requirements above take precedence for Vox-Deretor episodes.

## Documentary cast and optional scenarios

Follow [channel documentary DNA](../../references/scripting-dna.md) and [evidence boundaries](../../references/historical-fiction.md). Design only the people the approved narration needs: documented participants for supported actions, or explicitly illustrative people for explaining a verified process or rule. A system-led story needs no recurring person. Do not invent backstory, private thoughts, dramatic encounters or testimony for real participants. A fictional operator or traveler belongs only to a specifically selected hypothetical story. Research clothing and props; distinguish reconstruction from observed evidence. Topic changes do not automatically reuse an earlier role, plot or setting.
