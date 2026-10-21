# Topic identity and live authoring context

Keep channel identity, current DNA, selected subject and approved production separate. The user's selected topic governs this episode. Pilots, playlists, discovery results, old narration and cached DNA do not select another subject.

## New topic

Before selecting a topic, use `python scripts/channels.py scout <channel-id>` and references/topic-selection.md. This read-only discovery context exposes the live channel lens, exact audience language/region, allowed question shapes and recommendation requirements without a slug or folder. Keep candidate ledgers separate; bind only a selected question. `show` and episode `context` also expose live topic_discovery; `context` exposes question_design independently of recorded production.

Use a new slug/folder with fresh research, story card and narration review. Apply the selected active channel's documentary DNA, voice route and visual grammar; do not copy the last plot or conclusion.

```text
python scripts/channels.py bind vi-sao-noi-nay <new-slug> --topic "<selected question or topic>"
python scripts/channels.py context vi-sao-noi-nay <new-slug>
```

`bind --topic` refuses a conflicting topic before writing. Binding without a topic is supported, but `context` refuses an empty topic before drafting. Do not use rebind to reset an existing episode or silently assign a new topic to unidentified production.

## Continue an existing episode

Read `brief.json`, `PROJECT_HANDOFF.md` when present, `beats.json` and approved narration. Run `channels.py context` for the selected slug; reconcile contradictory identity before editing. A subtitle, TTS or packaging follow-up does not discard the episode.

`context` is read-only. It combines selected topic with live shared DNA, topic_scope, editorial_revision and localized direction. `story_premise` is the current authoring scaffold; `recorded_story_premise` shows the saved production premise separately. Plot fields are reused only when the saved DNA revision, editorial revision and format match the selected live channel. An incompatible or unversioned premise contributes only period/place; opening, sequence, mechanisms, answer, consequences and optional scenario are not silently carried forward. A nonempty `exception_reason` preserves a specific requested format exception. Recorded production history is not an instruction for new authoring; approved words and media remain intact on disk.

New binding seeds the selected channel's `story_format`, the current documentary revision, central question, promise, opening, evidence anchors, sequence, mechanisms, answer, consequences and uncertainty. Hypothetical scenarios are optional. Archived channel IDs resolve recorded legacy production but cannot start a new episode. New episodes use D:\Video; old approved narration and media remain at their recorded locations until a requested revision is approved.

## Review boundary

Record topic, slug, current revision and actual version in the story card. Compare passages and source ledger against this identity. A different subject starts fresh research and review; approval does not transfer. The CLI checks identity and resolves defaults, not truth, causal plausibility, humor or authoring readiness. Read the actual narration and perform the two editorial passes.
