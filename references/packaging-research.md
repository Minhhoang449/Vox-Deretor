# Packaging research: title, thumbnail, description, and tags

Use two stages under [script-packaging-coordination.md](script-packaging-coordination.md): develop provisional title/thumbnail/opening concepts before long narration, then finalize packaging after story lock. Record the subject phrase, native language/market, intent ambiguity, supported answer and two distinct package hypotheses in existing research/story records. Autocomplete, when actually observed, informs wording rather than proving volume. Packaging should help the right viewer recognize the real story and decide to watch; it cannot repair an unclear or weak episode. Do not promise a result the film does not deliver.

First read the selected live profile's `packaging_direction` and [six-channel editorial packaging guide](channel-packaging-dna.md). Its viewer question, title starting points, thumbnail approaches and opening alignment define what to investigate. They are editorial options, not fixed visual templates or a replacement for episode research. `export_youtube.py` injects that channel's thumbnail direction into image prompts and writes `packaging-direction.md` for title review.

## Research the intended market

Use a small set of specific search phrases in the channel language. Set `--region-code` to the intended market when it differs from the channel default (for example, `JP` for a Japanese-language scan). Region and language filters create a discovery slice; they are not audience analytics. Open the result thumbnails and read the descriptions yourself. Public view counts do not show retention, satisfaction, or a causal reason for success.

Do not copy titles, descriptions, thumbnails, scripts, or visual identity. YouTube does not return another channel's Studio tags.

```text
python scripts/research_packaging.py "<episode>" --query "<localized episode question>" --region-code JP
```

## Build a coherent package

### Title

- Put the subject or important search phrase near the beginning. Keep the wording short enough to read in common placements; the hard limit remains 100 characters.
- Prepare distinct approaches: one clear searchable title and one curiosity-led title that still names the real subject or consequence.
- Keep claims accurate. Avoid false urgency, vague clickbait, long episode labels, and all-caps styling.
- Make the title and thumbnail work together: the title can name the question while the thumbnail shows the object, action, or consequence.

### Thumbnail

- Read [`thumbnail-visual-direction.md`](thumbnail-visual-direction.md) and use the selected channel visual style: original Chibi 2D for all six channels, with explanatory graphics where useful. The exporter adds the channel's editorial angle while leaving palette, font, text position, composition and references to the episode concept.
- Keep 1280×720 (16:9) delivery independent of video aspect. Let the real episode subject lead and vary the image's color, camera, text placement and composition when the idea benefits from it.

- First write the one thing a new viewer should understand from the image. Choose the real story carrier: person/action only when it adds narrative value; otherwise the ship, landscape, map, building, mechanism, ecosystem, natural process or changed world can lead. Do not insert the protagonist just to satisfy a thumbnail template.
- Give the viewer one dominant subject and one readable relationship or question. Use a strong silhouette, clear contrast and a restrained background. At phone size, the subject and stakes should register before small details.
- Use the selected channel visual style for new scene images; explanatory diagrams may remain simplified graphics. Preserve explicit recorded styles for existing episodes. Do not reuse a generic frame or identical subject/action for every topic.
- Use a short localized phrase only when it makes the question clearer, roughly 2–5 words where the language permits. Lettering is optional when the image already communicates the relationship. Record an explicit empty `thumbnail_text` and a `thumbnail_text_reason` for that choice. When lettering is used, keep it exact, high contrast and readable with safe margins; complement rather than repeat the full title.
- Keep curiosity concrete and honest. Do not depict an outcome as certain when the film treats it as hypothetical, exaggerate danger, or promise an answer the opening/video does not deliver.
- Make candidates meaningfully different in visual hypothesis, subject, shot scale, angle, action, palette, text placement or consequence. Up to three is a platform test limit, not a requirement to invent weak variants.
- Keep the image faithful to the episode and within YouTube's thumbnail and community policies.

### Description

- Write a unique description for this episode. The first few lines should explain what the viewer will understand and name the country, time period, product, or other important scope.
- Include one or two natural search phrases in the title and description. Do not stuff keywords or repeat the title mechanically.
- After the opening, add concise scope and useful chapter timestamps only from the final measured edit. Keep research sources in the internal ledger; include public attribution when a used asset/license requires it or the user explicitly requests it. Do not append a research bibliography by default.
- Preview the first lines on mobile. Keep the description plus hashtags under 5,000 characters.

For manual chapters, start at `00:00`, use at least three timestamps in ascending order, and make each chapter at least ten seconds long. Only add timestamps after the final edit is assembled and its timing is known.

### Tags and hashtags

- Treat Studio tags as a small supporting field. YouTube says titles, thumbnails, and descriptions matter more for discovery; tags mainly help with common misspellings.
- Use only episode-specific names and useful spelling, diacritic, transliteration, or abbreviation variants. Remove broad, duplicate, and speculative tags. The 500-character limit is a ceiling, not a target.
- Use at most three relevant hashtags. Do not put a tag list into the description.

### Playlists

Read [`playlist-catalog.md`](playlist-catalog.md) and the live channel catalog in `config/playlists.json`. Names and ready-to-copy descriptions are localized for each channel. Put the real topic first in the title and explain scope in natural language; keywords help viewers recognize the subject, but the catalog is not search-volume evidence or a ranking guarantee. The 100-character title and 1,200-character description caps are this project's editorial limits, not claims about YouTube platform limits. Playlist tags are not a field in this workflow.

For the final metadata of a completed video, select one existing primary playlist according to the episode's central question and add up to two more only when the film substantially covers those topics. A passing mention does not justify another assignment. Use a war/conflict specialist playlist for a central military topic rather than forcing it into an unrelated group. Period-specific groups only fit those periods; broader groups can fit other supported subjects. Put the assignment in `beats.json` under `youtube_metadata.playlists` and export it with the video package. Do not create new catalog entries or YouTube playlists for an episode. A draft package may remain pending until the video is complete; a completed video's final package needs a selected primary playlist.

```json
"playlists": {
  "primary_id": "vi-sao-noi-nay-water",
  "additional_ids": ["vi-sao-noi-nay-infrastructure"],
  "selection_reason": "Hành trình cấp nước là câu hỏi chính; công trình hạ tầng được giải thích đáng kể."
}
```

Put this object inside `youtube_metadata` in `beats.json`. `channels.py bind` seeds an empty choice; `channels.py show` includes the current playlist catalog. The exporter rejects unknown/foreign-channel keys and duplicate choices. It writes `youtube-playlists.txt` and `youtube-playlists.json` even when no thumbnail is selected, after the usual packaging validation. When the upload package is ready, its section 7 includes the selected playlist names, descriptions, roles and platform-link state. Drafts with no choice are marked `pending_selection` with optional keyword suggestions; choose the primary playlist from the finished video's actual content before delivering its final package. Suggestions are never silently applied.

The catalog's internal `id` is a routing key. Fill `youtube_playlist_id` only after creating or identifying a real playlist on the correct channel; supplied platform IDs/URLs are labeled unverified until checked separately. This exporter performs local file writes only. Publish playlist shelves when relevant videos exist; the catalog does not instruct creation of empty public playlists.

## Use tests and channel data

If YouTube Studio offers Test & Compare for the channel and video, test up to three genuinely different packages at the same time. The current feature may test thumbnail variants or title-and-thumbnail combinations; YouTube selects based on watch-time share, not CTR alone. Results can take days or up to two weeks, and an inconclusive result is not proof that one package is better. Do not substitute sequential manual swaps as if they were an A/B test: audience and traffic-source mix can change between swaps.

After publication, use the channel's own Analytics: compare impressions and click-through rate by surface and audience, then check watch time and audience retention to see whether the promise attracted the right viewers. YouTube notes that CTR shifts with audience, content type, traffic source and impression scale; compare similar videos over time and do not set a universal CTR target or react to a small early sample. Record the hypothesis and result in `youtube_metadata.experiment`. High CTR with weak viewing is a mismatch signal, not a win. Do not treat public view counts or a competitor's popularity as proof of a winning package.

## Workflow

Run the scan, open the linked thumbnails, and record one `packaging_research.observation` describing what the market makes clear, what the episode can explain distinctively, and the packaging angle to test. Then fill:

- `promise`: one accurate sentence shared by the title, thumbnail, opening, and film.
- `candidates`: one to three materially different title/thumbnail approaches. Each candidate needs `id`, `title`, `thumbnail_concept`, `thumbnail_prompt`, an episode-relative `thumbnail_file`, and `thumbnail_text`: an exact localized phrase, or an explicit empty string plus `thumbnail_text_reason` explaining why the image is clear without lettering.
- `description`: natural localized opening and concise episode scope. Omit public source/research/reference sections by default; keep the claim ledger internal. Required asset/license attribution and explicit user requests are exceptions.
- `hashtags`: zero to three relevant hashtags.
- `studio_tags`: a short, relevant list, not a keyword dump.
- `experiment`: the audience hypothesis and what result would change the next package.
- `playlists`: one primary catalog key, up to two relevant additional keys, and a selection reason.

Run `export_youtube.py` to create `thumbnail-prompts.md`. Use the Codex `imagegen` skill to generate each thumbnail, save it at `thumbnail_file`, and inspect localization, legibility and composition at phone size. Render nonempty `thumbnail_text` exactly; regenerate inaccurate or garbled lettering. For an explicitly text-free candidate, inspect that no unintended lettering appeared and the visual question remains clear.

Example candidate shape:

```json
{
  "id": "mechanism-closeup",
  "title": "How a card payment reaches the shop",
  "thumbnail_concept": "A card tap sends a bright payment pulse through three visible checkpoints.",
  "thumbnail_prompt": "Original animated scene showing ...",
  "thumbnail_file": "thumbnails/mechanism-closeup.png",
  "thumbnail_text": "Where does it go?"
}
```

## Official YouTube guidance

- [Thumbnail and title tips](https://support.google.com/youtube/answer/12340300)
- [Impressions and click-through rate FAQ](https://support.google.com/youtube/answer/7628154)
- [Tips for video descriptions](https://support.google.com/youtube/answer/12948449)
- [Add tags to your YouTube videos](https://support.google.com/youtube/answer/146402)
- [Test and compare thumbnails](https://support.google.com/youtube/answer/13861714)
- [A/B tests for titles and thumbnails](https://support.google.com/youtube/answer/16391400)
- [Video chapters](https://support.google.com/youtube/answer/9884579)

## Optional hypothetical episode promise

The active six-channel default is a research-led documentary or explainer whose title, thumbnail and opening match its channel-specific question. Only when a hypothetical episode is specifically selected may the title name a mission or alternate outcome. Identify that framing clearly and avoid presenting a conditional result as a forecast or an actual changed event. Descriptions distinguish facts, reconstruction, illustrative examples and optional assumptions where used.

## Adopted marketing specialist

Read [youtube-marketing-integration.md](youtube-marketing-integration.md) when using upstream thumbnail/seo/metadata modules. This document and the live packaging_direction govern localized output, schema and QA; upstream product templates and unsupported performance forecasts do not apply.
