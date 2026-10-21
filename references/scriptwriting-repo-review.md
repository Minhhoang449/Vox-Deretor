# Open-source scriptwriting repo review

> **Dated workflow research, not a writing specification.** Documentary/Muse wording below describes the project at the review date. Current narration follows `scripting-dna.md` and `config/channels.json`; current production follows `local-pipeline.md`. Do not inherit this review's former tone or model defaults.

Reviewed 2026-10-09 for the Vox-Deretor war-history narration workflow. This is a fit review of public repository documentation and licenses, not a code audit or a claim that any writing tool improves audience retention.

## What this project needs

The output is a 14–30 minute researched documentary narration in a channel's language, later mapped to `beats.json` and Muse video prompts. The source of truth needs claim/source tracking, a causal beat outline, revisions, retention review, and readable continuous narration. It does not need dialogue-heavy feature-screenplay pagination as its primary format.

## Candidates

| Repository | Useful parts | Fit and limitation |
|---|---|---|
| [Narrative Engine](https://github.com/fernandoportal/narrative-engine) | Modular progression from logline and characters through beat sheet to selected scenes; explicit cause/effect and versioned writing files. MIT license. | Best structural inspiration for this project. It is a small, Antigravity-oriented framework, not a mature documentary research system; adapt its modularity, not its assumptions or templates wholesale. |
| [FountainPad](https://github.com/grahaminman/FountainPad) | Windows-compatible desktop editor; Fountain text, project binder, canon/beat/card notes, beat board, index cards, and card/beat packs. MIT license. | Best planning/editorial interface if a visual beat board is wanted. The project already uses Markdown and `beats.json`, so installing a separate app would add a parallel source of truth. |
| [OpenDraft](https://github.com/Proteus-Technologies-Private-Limited/OpenDraft) | MIT-licensed screenwriting app with beat boards, character profiles, version history, and Fountain import/export; the repository showed 591 commits at review time. | Strongest actively developed screenplay application in this shortlist, but its main job is screenplay drafting/collaboration. It does not replace our evidence ledger, documentary narration edit, or retention audit. |
| [Scriptum](https://github.com/argocine/Scriptum) | MIT, local-first, cross-platform screenplay editor; imports/exports Fountain and Final Draft and keeps richer planning/revision data in its native format. | Good for standard screenplays and revisions. Its project format and page-oriented screenplay workflow are unnecessary for the continuous narration used here. |
| [BetterFountain](https://github.com/piersdeseilligny/betterfountain) | MIT VS Code extension for Fountain with outline, notes/synopses, PDF export, character/scene completion, and duration estimates. | Lightweight if a writer wants screenplay formatting inside VS Code; it is an editor aid, not a historical research or story-editing method. |

Repository details and activity can change. Feature and license descriptions above are based on each project's own GitHub repository pages at the review date. No external source code or templates are copied into this repository.

## Decision for Vox-Deretor

No reviewed repository handles the full combination of sourced war history, native-language documentary narration, separate story and retention passes, Chibi character continuity, and Muse handoff. Add a project skill that combines the useful *workflow* ideas: Narrative Engine's modular progression and cause/effect checks; FountainPad's separation of project notes, beats, and character references; OpenDraft/Scriptum's explicit revision and alternate-version discipline. Keep the continuous narration in Markdown and the approved visual plan in `beats.json`. Do not make a screenwriting application or Fountain parser a runtime dependency.

### Implementation follow-up — 2026-10-11

The shared historical-writing workflow is now implemented in `skills/vox-history-storywriting/SKILL.md`, with `skills/vox-war-scriptwriting/SKILL.md` retained as a specialist route. The active production path has since moved to imagegen stills and Revideo; the Muse handoff described in this dated review is historical context, not the current pipeline.

If the team later wants a visual planning/editor application, evaluate FountainPad for its project binder and beat board, or OpenDraft for a more complete screenplay editor. Neither is required to use the skill.
