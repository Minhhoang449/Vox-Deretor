# Finding and recommending documentary topics

Active workflow: topic-selection-v3-2026-10-21. Read live `narration_dna.topic_scope`, `question_design` and the channel lens through `python scripts/channels.py scout <channel-id>`. This read-only command needs no slug or episode folder. The live six profiles and their audience languages govern; this workflow selects questions, not episodes for production. Consult decision history before proposing repeats, test curiosity before deep research, compare two treatments of strong finalists and challenge the recommendation before presenting it.

## Find a viewer question, not just a historical noun

Start from two directions and let them meet:

- **Audience curiosity:** a recognizable action, habit, pleasure, inconvenience or contrast that someone could wonder about without knowing the archaeological term. In the primary market, inspect relevant long-form topics, nearby questions and genuinely available comments/analytics. Public questions are leads, not factual claims or representative surveys.
- **Evidence:** a dated object, site, text, experiment or documented practice with something concrete to explain. Ask what it lets a viewer understand about lived experience. A museum catalog can establish the object, but its existence alone does not establish demand or enough material for a full episode.

A small task is the default. A connected set of routines is also legitimate when each answers part of one central question in a bounded community. A day is a possible narrative carrier, not a compulsory dawn-to-night checklist. Keep food, tools, daily life, shared rules, Japanese human history and Vietnamese geographical adaptation distinct. Do not copy the same topic to six channels or translate a successful title into a strategy without local research.

Generate a varied working pool rather than ten paraphrases of the first competitor title. Mix evidence-led and question-led leads, and include a different narrative shape where the evidence warrants it. Before spending API quota, remove the borrowed exclusions (including translations/narrow variants), later-period subjects without an explicit exception, false absence/first-ever premises, duplicate existing projects and candidates outside the channel lens. Existing approved work is not invalidated by this screening.

## Curiosity check before deep research

For each surviving lead, write one plain question in the audience's language and one sentence explaining why its answer is worth hearing. Identify the recognizable action/object, the truthful gap or surprising relationship and what the viewer will gain. An artifact's rarity, a specialist name, a dramatic adjective or a high-view competitor title is not a substitute for this reason.

Use `continue`, `reframe` or `defer` as a qualitative working judgment, with a reason. Do not ask viewers hypothetical survey questions and present imagined answers as demand. A source-led lead can pass after its ordinary-life meaning is made clear. If the appeal depends on an unverified absence, first-ever claim or crisis, verify or reframe that premise before spending effort on a full dossier. This is an editorial screen, not measured interest or a score threshold.

## Research a manageable finalist set

Normally develop 3–5 finalists per requested channel; do not manufacture a quota if fewer survive. Keep a separate ledger for every candidate. For multi-channel work, state which channels/candidates actually received primary-market research rather than passing one scan off as a six-market study.

1. Write the ordinary viewer question, bounded place/period/social position and supported answer currently expected. Separate the audience-facing question from the specialist search term; exact site names can hide adjacent interest.
2. Search in the configured audience language/region. Start with the understandable question and an appropriate adjacent formulation; use a site/artifact term when needed for relevance. Do not turn query expansion into an automatic grid. Read results, diagnose the missing slice, then make a purposeful follow-up. Record query text, language, region, date, order, returned pages and coverage. `relevance` is a useful first slice; date/viewCount can answer different questions but do not create demand measurements. Record them separately if used.
3. Classify results before comparing: direct long-form, adjacent long-form, short-form, wrong language, unrelated, compilation/reupload or possible own-channel result. Verify uncertain identities where material. A language filter does not guarantee spoken language. Exclude irrelevant, duplicate and own-channel results from independent-competitor claims; do not discard a low-view relevant result because it is inconvenient.
4. Inspect a small meaningful comparison set, including a successful relevant reference and a less successful/recent comparable reference when available. Record differences in age, duration, format and publisher scale if known; missing baselines remain unknown. Do not infer a causal winning format from one high-view video or compute a success forecast from views/day or current subscriber counts.
5. For an important finalist, open the strongest relevant references. Inspect actual title/thumbnail and original-language opening, consequential middle and ending when accessible. Distinguish metadata, chapters, sampled playback, original transcript, translated captions and full review. If transcript access fails, retain that limit; do not award spoken-quality conclusions from metadata. An old video is not automatically stale if the underlying question/answer is unchanged.
6. Independently verify the essential answer through primary/authoritative sources. Identify the observations that can carry the middle, not just a list of URLs. A particular recipe, location, legal status, chronology or outcome may need evidence beyond an institutional summary. Do not stitch Rome, Pompeii and a distant province or several centuries into one supposedly typical person's day without explicit boundaries.
7. Test the story: can the first useful answer arrive early; what distinct understanding follows; what is the strongest supported reveal; what is the earned endpoint? A museum-method lecture or repeated uncertainty is not extra substance. Keep useful uncertainty at its claim. Check visual feasibility with the original Chibi stills route and whether supported material can sustain 8–16 minutes without padding.

Use `scripts/research_youtube.py` with explicit `--query-language`, `--relevance-language` and `--region-code`. Deliberate cross-language scans are supplemental, separately labeled with `--cross-language-note`, and never replace the primary-market scan. Browser-only discovery is acceptable when the API is unavailable; label its personalization/coverage limits and save the observed URLs and metadata. Never expose API keys.

## Judge three separate things

- **Curiosity:** the recognizable question, a truthful surprising relationship, what the viewer gains, and why the title can be understood without specialist vocabulary. A forced crisis or an absence that never existed fails this test.
- **Evidence and story feasibility:** supported central answer, distinctive bounded details, a connected question path, meaningful visuals and useful runtime. An essential missing link requires more research, a narrower question or deferral, even if public videos are popular.
- **Market observation:** which relevant videos/questions actually exist and what the dated public or authorized private evidence says. Weak exact-query results mean weak evidence for that query, not an empty market. Popular adjacent subjects do not prove demand for the exact question; strong competition does not automatically rule it out.

Do not combine these into an invented success percentage, an automatic weighted score or a universal demand threshold. A candidate with strong sources and unknown demand may be proposed as an **editorial experiment**, with the uncertainty visible. Prefer an honest bounded test over either pretending demand is proven or rejecting every distinctive idea with little exact-query data.

## Recommend a decision the user can assess

### Try two treatments before a full script

For the leading viable candidate, and a close rival when useful, develop **two substantively different treatments of the same evidence-bounded subject**. Each includes an audience question, provisional title, thumbnail concept with optional exact text, recognizable subject phrase and native-market intent check, a short target-language opening, first useful answer, linked passage contributions, strongest supported reveal and earned ending. Apply script-packaging-coordination.md before long narration; these concepts may change with evidence. Keep excerpts brief; do not write two full scripts or generate audio/images for this test.

The treatments must differ in their question or route through the material, not just title wording. Compare accessibility, curiosity, answer support, distinct progress, channel voice and the risk of becoming a lecture. Keep material uncertainty in both. A day, one object, a practical job or a contrast may provide different routes when the sources support them; these are options, not a required menu. Choose one with concrete reasons. If neither can support its promise, reframe or defer rather than picking the less weak one. This is a pre-draft editorial comparison, not an audience A/B test or completed SEO.

### Challenge the choice before recommending it

Run a distinct critical pass **after** comparing treatments and **before** the final recommendation. Name the candidate and version being challenged. Ask: is the premise true; can the essential answer and consequential middle be demonstrated; is adjacent popularity being mistaken for direct demand; are weak query results being called low competition; is the runtime sustained without method lectures; what makes the runner-up worse; and what evidence could reverse the ranking?

Record concrete objections tied to lines, missing evidence or observed results, a response/action for each, unresolved blockers, and `proceed`, `revise` or `defer`. Do not force an objection count or wave concerns away by repeating the proposal. Missing essential causality, a false premise or a broken central promise prevents an unqualified readiness recommendation. Unknown demand can remain an explicit editorial experiment. If the same Agent performs the pass, label it same-author second-pass; do not claim independent validation. A separate reviewer can be used when actually available and authorized, but is not a hidden requirement or permission to spawn/send work to another chat.

Use [topic-shortlist.md](templates/topic-shortlist.md). Present a ranked shortlist with reasons, one recommended question and a substantively different alternative. For each include: channel/market; shape; curiosity; place/period/group; supported answer and source access; direct vs adjacent public evidence; actual differentiation; overlap; a possible first image/action and a brief opening premise; linked passage contributions; useful runtime; principal risk and next check. Title phrasing is a provisional promise, not completed SEO or approved packaging.

Use explicit dispositions: `research_next`, `ready_for_drafting`, `defer`, `reject`. Readiness is an editorial recommendation, never narration approval. `ready_for_drafting` requires a supportable essential answer, channel/period/exclusion checks and an honest account of market uncertainty; it does not require pretending the future performance is known. A novelty-only rationale, an unusable scan or a known factual blocker cannot be labeled a proven opportunity. Explain what evidence would reverse the recommendation.

Only bind a fresh slug when a candidate is selected for episode development within the user's scope. Keep pre-selection research in a dated repository research folder; after binding, use the episode's own research directory under its configured D:/Video destination. Existing project brief/handoff and `channels.py context` govern continuation. User approval of the exact narration still precedes beats, TTS and images.

## Decision memory before and after selection

Use [topic-memory.md](topic-memory.md). Before discovery, read the channel's recent history exposed by scout and search the full memory for related questions, including other channels. A previous rejection or deferral is provenance, not a permanent ban; read its reason and check what changed. Do not treat a possible repeat as a duplicate merely because both use the same civilization or artifact.

After the recommendation, record the serious finalists with the reason for recommending, deferring or rejecting them and a pointer to their evidence/packet. Record selection for development separately when it actually happens. If the user later changes the decision, append a new event instead of deleting the prior one. Shortlist recommendations never become user approvals through this memory.

After publication, append observed outcomes only from real supplied/authorized data, naming the source, observation period and exact published version or its explicit availability limit. Keep observations separate from hypotheses about why they occurred. A public view count can be recorded as such; it cannot supply missing CTR, retention or attribution. If no analytics are available, leave them unknown and keep the original hypothesis for a later review. Reading memory must not modify episode files or generate production.

## Improve the next selection from real outcomes

Record the original hypothesis and exact published narration/packaging when available. Read impressions/CTR by traffic source, early retention, middle dips/spikes, watch time and relevant audience feedback together; compare reasonably similar conditions and lengths. A spike may reflect interest or confusion. Do not change a whole channel DNA because one new video has low views or because a query returned nothing.

YouTube's [search/discovery guidance](https://support.google.com/youtube/answer/11914225?hl=en) describes personalization, viewing/enjoyment signals and differences in topic interest and competition; it does not promise a favored universal format. Its [retention guidance](https://support.google.com/youtube/answer/9314415?hl=en) explains the 30-second Intro and interpretation of dips/spikes. Checked 21/10/2026; these support the measurement boundaries, not a forecast for these channels.
