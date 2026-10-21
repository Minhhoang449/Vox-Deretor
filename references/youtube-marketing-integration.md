# YouTube marketing specialist — six-channel adaptation

Adopted 2026-10-16 from https://github.com/adityaarsharma/youtube-marketing-skills.
Installed skill: `$CODEX_HOME/skills/youtube-marketing/SKILL.md` (default Windows location: `C:/Users/Admin/.codex/skills/youtube-marketing/SKILL.md`). Read that entry and the relevant `sub-skills/*.md` before using it. The upstream frontmatter name is `youtube`; its installation folder is `youtube-marketing`. Installation does not connect analytics, DataForSEO or a YouTube account.

This is an adapted specialist, subordinate to the user's request, AGENTS.md and the live channel profile. It supplies research and packaging methods, not narration approval or a new channel identity. Apply to all six active channels using their own language, lanes, writing_contract and packaging_direction. Do not revive retired channels or V2 samples.

## Routing

Apply [script-packaging-coordination.md](script-packaging-coordination.md) for an early concept pass using thumbnail/seo methods before long narration, together with the two topic treatments. Recheck actual speech and the provisional package before approval. The after-story-lock routing below is finalization, not the first time titles and thumbnails are considered. Artwork retains existing approval/audio gates.

| Stage | Upstream sub-skills | Project contract |
|---|---|---|
| Before topic selection | ideate.md, competitor.md | topic-research.md, channel-benchmarking.md, live lanes and writing_contract |
| Before long narration; recheck after story lock | thumbnail.md, seo.md | script-packaging-coordination.md, channel-packaging-dna.md, packaging-research.md, live packaging_direction |
| After measured final timeline | metadata.md | packaging-research.md, playlist-catalog.md, export_youtube.py |

### Topic search

Apply all four decision checks in topic-selection.md: plain-language curiosity before deep research; two genuinely distinct short treatments of the leading viable subject; an explicit critical pass before final recommendation; and sourced append-only decision/outcome memory via topic-memory.md. These are editorial checks, not measured viewer preference. Do not invent comments, analytics or an independent reviewer.

Before selection use [topic-selection.md](topic-selection.md) and `python scripts/channels.py scout <channel-id>`. Use both audience-question leads and authoritative objects/practices. Separate curiosity, supported-answer feasibility and dated market evidence; do not turn them into a forecast or automatic weighted score. Compare direct/adjacent long-form separately from Shorts, unrelated or wrong-language results and possible own-channel/reupload contamination. A weak query is not an empty market. Inspect real original-language passages before making claims about a competitor's script; metadata access must remain labeled. Recommendations include a substantively different alternative, rejected/deferred reasons and the evidence that would change the decision.

Read `channels.py show <id>` first and resolve that profile's `youtube_research.relevance_language` and `region_code` before writing any query. Research each candidate topic with topic-specific queries in the primary audience language and configured region: English channels use English, the Japanese channel uses Japanese, and the Vietnamese channel uses Vietnamese. Declare `--query-language` and `--relevance-language` to match the actual query text, and use `--region-code` for the configured market. Do not use Vietnamese queries to research topics intended for English or Japanese audiences. Keep any deliberate cross-language scan supplemental, label its separate question and reason with `--cross-language-note`, and never let it replace the primary-language scan. Use `research_youtube.py` for public discovery where configured, browser/web sources for verification, and independently verify the actual mechanism through authoritative sources.

Create a manageable shortlist (normally 3–5) with: viewer question, channel fit, dated public reference URLs and observations from the matching-language market, evidence availability, distinctive answer, visual feasibility, overlap with existing episodes and principal uncertainty. Research candidates individually; a scan for one selected topic does not represent the other candidates. Rank editorially with explicit reasons; a missing quantitative signal stays unknown. Select a fresh subject and new slug. Launch candidates are not approvals. Save each topic's dated queries, language/region, source type and limitations with the topic brief/dossier.

### Thumbnail and title

Before long narration, compare two distinct title/thumbnail/opening concepts with the two treatments around the supported answer. Record subject wording, search intent, visual hypothesis, optional exact localized text, focal state and opening payoff. Before narration approval recheck against actual speech. After story lock finalize 1–3 substantive candidates from this work. Use the channel's editorial approach rather than a compulsory result/before-after/bold-claim trio.

Generate original 1280x720 artwork using the selected channel's configured visual style and imagegen route; all six channels use original Chibi 2D. Explanatory diagrams may stay graphic. Preserve recorded styles for existing episodes. Inspect the actual image at phone size and planned crops; check spelling, truthful scale/state, focal clarity and timestamp overlap. Do not present generated images as authentic archival records. Logos, faces, dark backgrounds, fonts and layouts are not mandatory. Do not predict CTR percentages. Compare hypotheses through available real test evidence; use watch-time share, traffic-source CTR and retention together, not a universal 500-impression switch rule.

### Metadata

Prepare episode-specific localized title, description, relevant tags/hashtags, chapters, existing catalog playlist selections and upload defaults using the existing exporter schema. Follow packaging-research.md rather than the upstream WordPress product template. Chapters use measured final timing, never estimated narration timestamps presented as final. Keep draft timing explicitly provisional until rendered timing is available. Use the configured category/language and record unresolved Studio settings as unresolved; never invent platform IDs, publication dates or account state.

Return a local reviewable package via `export_youtube.py`; inspect its output. This task does not authorize upload, publication, comment posting, OAuth setup or external account changes. Do not run upstream write tools automatically.

## Evidence and upstream exceptions

- Public views, search rank and upload age describe observed public performance, not private retention, CTR, audience demand or causality. An old high-ranking video is a research lead, not proof that a newer video will win.
- Use DataForSEO only if actually available and authorized. Record the dataset, geography, language, date and whether volume measures Google or YouTube. Do not multiply Google search volume into purported YouTube volume or forecast views. Without that tool, mark keyword volume unavailable and provide a qualitative draft based on observed public evidence; do not claim the upstream quantitative SEO step was completed.
- Private analytics require actual authorized data. Missing analytics remain unavailable. Never use the upstream example company's subscribers, products, discounts, links, benchmarks or posting times as ours.
- Ignore unsupported numeric uplift claims, keyword-indexing claims and fixed CTR targets in the upstream examples. Verify any platform rule needed for a decision through current official documentation. Project packaging rules govern tag count, hashtags, chapters and limits.
- No automatic year suffix, product keyword, sales CTA, seven-link block, twenty-tag quota, ten hashtags or forced English. No copied publisher thumbnail identity. Topic/title/thumbnail must pay off in the approved opening and episode.

## Review record

Keep `marketing-research.md` in the episode research directory: date; channel/profile; upstream modules used; available/unavailable tools; query/source ledger; shortlist and selection rationale; title/thumbnail hypotheses and actual image QA; metadata review and unresolved fields. Reference existing source ledgers rather than duplicating facts. Label editorial judgments and text-only checks honestly. There is no audience-performance guarantee.

## Public description standard — 20/10/2026

Use the live metadata_direction. Do not append Sources, Research or References sections or internal ledgers by default. Write a natural localized introduction and concise scope; relevant tags, zero to three hashtags and optional measured chapters. Preserve required asset/license attribution or an explicit user request. Reference videos guide craft only; no copied characters, titles or layouts.
