# Approved speech, listening copy and caption review

Use this after narration review and at TTS/render continuation. This implements the existing user-approval requirement; a score or generated manifest cannot grant approval.

## Record the version the user actually approved

New `channels.py bind` projects require a narration record. After the user approves the specific text, record the continuous speech before creating beats:

```powershell
python scripts/narration_lock.py record "D:\Video\<channel>\<slug>" --source "D:\Video\<channel>\<slug>\research\narration-approved.md" --section "Lời dẫn" --approval-note "<actual user approval reference>"
```

`--section` selects the exact Markdown heading and stops at the next heading of the same or higher level. Omit it for speech-only plain text. No source ledger, editorial directions or review notes belong in the selected speech. The command refuses mismatching existing beats. For a revision, keep the candidate separate; after its actual approval update the beats and record the new version with `--replace`. Do not use a generic “fix the workflow” instruction as approval of a subsequently written narration.

`check <episode_dir>` compares channel, episode, effective speech language, the approved source and joined beat narration. Only whitespace differences are ignored. A record can be made before beats, but an empty beat map cannot pass the production check. Source notes outside the selected heading can change without invalidating speech approval.

TTS, caption generation and local assembly check this record. TTS caches also store normalized speech SHA-256 and WAV content SHA-256. Assembly refuses a changed WAV or changed beat text. On an existing cache, the TTS runner may add these receipts only after its full text/voice/settings fingerprint matches; this reuses the WAV without `--redo`.

Existing projects without a record retain their production state and print `legacy_unrecorded`; inspect their brief/handoff and actual approval. That warning does not prove they were unapproved. Never auto-enroll them from a draft label, self-review score, old export or status flag. A present but mismatched record always stops production, including for legacy projects.

## Listen before producing all images

After TTS the runner automatically creates `review/narration/review.html`, a complete `audio-review.wav` and opening/middle/ending WAV samples. These use current speech verbatim, without BGM, stretching or added silence. The default middle is a convenience sample, not an automatic judgment of the most difficult explanation. Select the mechanism beat explicitly when it is known:

```powershell
python scripts/narration_review.py "<episode_dir>" --output-dir "<episode_dir>\review\mechanism-check" --audio --middle-beat B11
```

Listen for actual comprehension and repetition across the full narration. Inspect the opening, essential mechanism and final answer in context; an attractive first minute cannot validate the middle. Keep the approved voice, synthesis speed and 0.8-second pauses. If the wording needs changing, stage it for narration approval; do not repair pacing by stretching audio or silently shortening pauses.

The listening copy joins WAV frames directly. It has a different clock from the final video, which includes visual tails. The HTML explicitly separates these clocks and labels old production speech versus a pending script candidate. Generated files always start with `listening_review_status: pending`; successful export does not certify listening quality.

## Review captions at their actual video times

The same command exports estimated-alignment ranges and individual fast-reading cues from the existing `captions-timeline.json`, with video seek buttons. It records the report fingerprint and whether caption text still matches current beats. This is a review queue, not a fresh alignment or an automatic pass. Zero structural errors can coexist with `needs_review`.

To investigate an unavailable or disabled alignment backend, enable it in an isolated copy:

```powershell
python scripts/stage_caption_alignment.py "<episode_dir>" --output-dir "<new review copy directory>"
```

This writes candidate SRT/ASS and before/after QA, reads the original WAVs, and leaves the source episode override, final video and caption files intact. A disabled `device: none` is replaced with `auto` in the copy. Check the resulting backend reason; importing WhisperX alone does not establish that its model/dependencies work. Do not loosen coverage limits to remove warnings or regenerate delivered TTS to obtain alignment anchors.

After listening/visual review, accepted caption changes must be applied through the shared timeline and SRT/ASS exporters. The existing video's burned captions stay old until the final video is rebuilt and checked. Never report a staged subtitle file as an updated delivered video.
