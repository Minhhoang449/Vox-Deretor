# Legacy route: footage first, then missing stills

Historical user authorization: 18/10/2026. Superseded for new episodes on 19/10/2026 by `imagegen-stills.md`. Keep this route only for existing episodes whose saved workflow explicitly uses it. Canonical configuration for new bindings is `config/pipeline.json` → `visual_dna` / `visual_workflow`; existing episode settings are preserved.

## Order of work

1. Research the selected topic in the channel's audience language/market, write and obtain approval of the actual narration. Plan meaningful passages/shots, generate approved TTS, measure duration and listen to the review copy before producing visual assets.
2. Run `python scripts/visual_sources.py "<episode>" --init`. This adds unresolved `visual_source` slots and exports `research/montage-requests.md`. It performs no search, download or image generation. Read the current Montage guide at `D:\Coder\Montage` and run its provider preflight before retrieval. Use Montage as a retrieval tool from the Vox project; keep the episode at its recorded destination. Use the approved shot needs, not Montage's short no-narration documentary template or its own script/TTS stages.
3. Search and inspect relevant video first. Prefer credible official/event records where the actual event matters; use source-native archive terms as a documented supplement to primary audience-language queries. NARA and configured stock providers such as Pexels/Pixabay are candidate sources, not promises of available footage. Check actual provider access without exposing credentials. An environment-only key check does not establish what Montage loads from its local secrets files.
4. Record the actual query, query language, provider, access date, outcome, source link, rights and visual fit. Inspect a clip's contents, not just its title/thumbnail. Generic river, rain or road footage can illustrate a passage; a visibly different dam, battle, reading or destroyed structure cannot prove the named event. Keep `event_record` and `illustrative` roles explicit. Check rights per item, including third-party material in archive holdings; keep a usable rights/reference URL and required attribution.
5. Download chosen clips to the episode's `footage/` folder. Set `clip_path` and `source_in_seconds` on each video shot. Choose a range long enough for the final measured slot at native speed. Record one decision per shot: `video`, `ai_reconstruction`, `diagram` or `reuse`. Explain why footage fits or why a still/diagram is required. A map/cutaway exposing an invisible mechanism can be planned directly from verified sources; it needs no irrelevant stock search. Related still reuse follows `image-reuse.md`.
6. Run `python scripts/visual_sources.py "<episode>" --check`. The image prompt exporter and assembler repeat this structural gate for new workflow episodes. It requires actual search records and downloaded clips before reconstruction prompts, plus source/rights records. Structural checks cannot certify the truth of manual entries; inspect the source and media.
7. Export image prompts with `codex_prompts.py` only for remaining stills. Scene reconstructions use `documentary-realistic`; shots selected as `diagram` use readable explanatory graphics. Match the selected footage's color, lighting and texture. Generate/review/register those originals with Codex imagegen. The manifest lists video shots separately and requests no image for them.
8. Assemble locally with `visual_mode: hybrid`. Montage supplies source clips; Vox preserves approved speech, native-speed TTS, BGM and caption alignment. The mixed FFmpeg route uses two workers, per-shot content caches and clean cuts; it trims video at its source in-point without slowing, looping or freezing it. Stills use the existing balanced camera renderer. Short footage stops rendering and requires another range/clip or a reviewed timing change. Original clip audio is muted; deliberate sourced sound can be prepared as separately reviewed `sfx_path`.
9. Inspect the actual sequence for factual fit, natural anatomy, color continuity, rights/credits, crop, motion, audio and captions. Do not add visible AI/illustration disclosure labels to images or video. Keep factual role and provenance in internal records. Record remaining limits. An exported request pack is not completed retrieval; a prompt is not an image; a successful render is not completed editorial QA.

## Source fields

Store each shot's record in `visual_source`. Keep detailed candidate/query notes in `research/`. The example is a schema illustration, not verified research or a permission grant:

```json
{
  "decision": "video",
  "reason": "Why this range serves the narration span",
  "searches": [{"provider": "nara", "query": "actual query", "query_language": "en", "accessed_on": "YYYY-MM-DD", "outcome": "Actual result and limitations"}],
  "source_url": "catalog item URL",
  "accessed_on": "YYYY-MM-DD",
  "rights_url": "item rights or applicable license URL",
  "rights_status": "verified",
  "rights_note": "Actual terms, restrictions and attribution checked",
  "factual_role": "illustrative",
  "verification_note": "What was inspected, depicted place/time and why it fits",
}
```

`ai_reconstruction` needs an actual search ledger, explanation, research `source_url` and `accessed_on`. `diagram` needs `reason`, research `source_url` and `accessed_on`. `reuse` needs `reason`, `reuse_image_from` and `reuse_reason`; it inherits the original image's internal provenance. `video` needs all example fields, an existing shot `clip_path`, and optional finite nonnegative `source_in_seconds` (default 0). At least one search must use the channel language; supplemental archive-language searches need `cross_language_note`. Genuine event records must have verification supporting the event/location/date claim. Keep internal factual_role and source metadata for editorial accuracy, but do not render disclosure labels.

Do not apply AI/illustration disclosure overlays in the hybrid renderer. Metadata and credits must accurately describe footage and reconstruction where relevant.

## Continuations and boundaries

Existing episodes keep approved media and settings. For a requested visual revision, inspect `brief.json`, `PROJECT_HANDOFF.md` and `channels.py context`, preserve actual speech approval, then explicitly adopt the new visual workflow. Keep channel/topic/slug. Never read or recover V2. No provider access, asset rights or search result is inferred from this guide; check at production time. Never print secrets or request API keys in chat. Workflow changes do not authorize new narration or publication.
