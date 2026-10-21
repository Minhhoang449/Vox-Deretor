#!/usr/bin/env python3
"""
Validate YouTube packaging on beats.json and export thumbnail prompts.

The script writes thumbnail-prompts.md for generation with the Codex imagegen skill. After a
selected candidate's image exists, a second run writes youtube-upload.txt.

Rules: 1–3 candidates, title ≤ 60 characters (Japanese ≤ 32; YouTube hard cap 100); run research_autocomplete.py on the lead phrase, description + hashtags ≤ 5000,
studio tags ≤ 500. Thumbnail prompts follow the episode's selected animation style.

Usage: python export_youtube.py <episode_dir>
"""
import json
import os
import sys

from local_guard import refuse_out_dir
from thumbnail_visual_direction import resolve_thumbnail_profile, thumbnail_visual_prompt, check_thumbnail_candidate
from playlists import episode_playlists, export_episode_playlists, playlist_text
from channel_packaging import packaging_guide


def clean(value):
    return value.strip() if isinstance(value, str) else ""


SHORT_TITLE_CAP = {"ja": 32}


def long_title_cap(title):
    """Studio cap for long-video titles: 32 if the title has Japanese/CJK text, else 60."""
    return 32 if any("\u3040" <= c <= "\u9fff" for c in title) else 60


def validate_shorts(metadata, long_title, language, narration=""):
    """Studio Shorts rule: 0-3 Shorts, each cut from a named passage, ends by pointing to the long video."""
    shorts = metadata.get("shorts") or []
    if not isinstance(shorts, list) or len(shorts) > 3:
        raise SystemExit("youtube_metadata.shorts must be a list of at most 3 Shorts.")
    cap = SHORT_TITLE_CAP.get((language or "")[:2], 60)
    seen = set()
    for index, short in enumerate(shorts, start=1):
        sid = clean(short.get("id")) or f"short-{index}"
        for key in ("title", "source_passage", "hook", "closing_line"):
            if not clean(short.get(key)):
                raise SystemExit(f"Short {sid} needs {key} (closing_line must point to the long video).")
        title = clean(short["title"])
        if len(title) > cap:
            raise SystemExit(f"Short {sid} title is {len(title)} characters; cap is {cap}.")
        if long_title and title.casefold() == long_title.casefold():
            raise SystemExit(f"Short {sid} title duplicates the long video title.")
        if title.casefold() in seen:
            raise SystemExit(f"Short {sid} title duplicates another Short.")
        seen.add(title.casefold())
        if narration:
            norm = lambda t: " ".join(str(t).split()).casefold()
            if norm(short["hook"]) not in norm(narration):
                raise SystemExit(f"Short {sid} hook must be quoted verbatim from the long video's narration.")
    return shorts


def run(project_dir):
    refuse_out_dir(project_dir)
    path = os.path.join(project_dir, "beats.json")
    with open(path, encoding="utf-8-sig") as f:
        doc = json.load(f)
    visual_profile = resolve_thumbnail_profile(doc.get("channel_id") or "", episode=doc)
    visual_prompt = thumbnail_visual_prompt(visual_profile)
    metadata = doc.get("youtube_metadata") or {}
    playlist_bundle = episode_playlists(doc)
    research_dir = os.path.join(project_dir, "research")
    packaging_reports = []
    if os.path.isdir(research_dir):
        packaging_reports = [
            name for name in os.listdir(research_dir)
            if name.startswith("packaging-") and name.endswith(".md")
        ]
    if not packaging_reports:
        raise SystemExit(
            "No packaging research for this episode.\n"
            "Run: python scripts/research_packaging.py <episode> --query \"<search phrase>\"\n"
            "See references/packaging-research.md."
        )
    notes = metadata.get("packaging_research") or []
    if not any(isinstance(item, dict) and clean(item.get("observation")) for item in notes):
        raise SystemExit(
            "Packaging scan exists, but youtube_metadata.packaging_research has no observation.\n"
            "Open the thumbnail links in research/packaging-*.md. Record what the titles name, "
            "what the thumbnails show, and the gap. Then fill promise, candidates, description, and tags."
        )
    candidates = metadata.get("candidates") or []
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 3:
        raise SystemExit(
            "youtube_metadata.candidates needs 1 to 3 packages. "
            "Each needs id, title, thumbnail_concept, thumbnail_prompt, thumbnail_file, thumbnail_text, "
            "character, emotion and text_source_line."
        )
    seen = set()
    for index, candidate in enumerate(candidates, start=1):
        candidate_id = clean(candidate.get("id"))
        title = clean(candidate.get("title"))
        if not candidate_id or candidate_id in seen:
            raise SystemExit(f"Candidate {index} needs a unique id.")
        seen.add(candidate_id)
        if not title:
            raise SystemExit(f"Candidate {candidate_id} needs a title.")
        cap = long_title_cap(title)
        if len(title) > cap:
            raise SystemExit(f"Candidate {candidate_id} title is {len(title)} characters; Studio max is {cap}.")
        for key in ("thumbnail_concept", "thumbnail_prompt", "thumbnail_file"):
            if not clean(candidate.get(key)):
                raise SystemExit(f"Candidate {candidate_id} needs {key}.")
        if not isinstance(candidate.get("thumbnail_text"), str):
            raise SystemExit(f"Candidate {candidate_id} needs thumbnail_text (a phrase or an explicit empty string).")
        if not clean(candidate["thumbnail_text"]) and not clean(candidate.get("thumbnail_text_reason")):
            raise SystemExit(f"Candidate {candidate_id} needs thumbnail_text_reason explaining why the image works without lettering.")
        for key in ("character", "emotion"):
            if not clean(candidate.get(key)) and not (key == "character" and isinstance(candidate.get(key), dict)):
                raise SystemExit(f"Candidate {candidate_id} needs {key} (one emotional Chibi character in the centre).")
        if clean(candidate["thumbnail_text"]) and not clean(candidate.get("text_source_line")):
            raise SystemExit(f"Candidate {candidate_id} needs text_source_line: the script line that makes the thumbnail text true.")
        narration = " ".join(str(b.get("narration", "")) for b in doc.get("beats") or [] if isinstance(b, dict))
        problems = [p for p in check_thumbnail_candidate(candidate, visual_profile["language"], title, narration or None)
                    if not (p.startswith("thumbnail_text is empty") or p.startswith("text_source_line is missing"))]
        if problems:
            raise SystemExit(f"Candidate {candidate_id} thumbnail check failed:\n- " + "\n- ".join(problems))
        image_rel = clean(candidate["thumbnail_file"]).replace("\\", "/")
        if image_rel.startswith("/") or ".." in image_rel.split("/"):
            raise SystemExit(f"Candidate {candidate_id} thumbnail_file must stay inside the episode folder.")

    selected_id = clean(metadata.get("selected_candidate_id"))
    if selected_id and selected_id not in seen:
        raise SystemExit("selected_candidate_id does not match a candidate.")
    selected = next((c for c in candidates if clean(c.get("id")) == selected_id), None)
    if selected:
        image = os.path.join(project_dir, clean(selected["thumbnail_file"]))
        if not os.path.isfile(image):
            raise SystemExit(f"Selected thumbnail is missing: {image}. Generate it with imagegen first.")

    description = clean(metadata.get("description"))
    if not description:
        raise SystemExit("youtube_metadata.description is required.")
    hashtags = metadata.get("hashtags") or []
    tags = metadata.get("studio_tags") or []
    if not isinstance(hashtags, list) or not all(isinstance(item, str) for item in hashtags):
        raise SystemExit("hashtags must be a list of strings.")
    if not isinstance(tags, list) or not all(isinstance(item, str) for item in tags):
        raise SystemExit("studio_tags must be a list of strings.")
    if any(item.strip() and not item.strip().startswith("#") for item in hashtags):
        raise SystemExit("Each hashtag must start with #.")
    hashtag_text = " ".join(item.strip() for item in hashtags if item.strip())
    full_description = description + ("\n\n" + hashtag_text if hashtag_text else "")
    if len(full_description) > 5000:
        raise SystemExit(f"Description plus hashtags is {len(full_description)} characters; max is 5000.")
    tag_text = ", ".join(tag.strip() for tag in tags if tag.strip())
    if len(tag_text) > 500:
        raise SystemExit(f"Studio tags use {len(tag_text)} characters; max is 500.")

    ratio = doc.get("aspect", "16:9")
    language = visual_profile["language"]
    title = doc.get("topic") or doc.get("project") or "Untitled episode"
    research = metadata.get("packaging_research") or []
    search_phrases = metadata.get("search_phrases") or []
    experiment = metadata.get("experiment") or {}

    all_narration = " ".join(str(b.get("narration", "")) for b in doc.get("beats") or [] if isinstance(b, dict))
    shorts = validate_shorts(metadata, clean(selected["title"]) if selected else "", language, all_narration)

    if selected:
        thumbnail_text = clean(selected["thumbnail_text"])
        thumbnail_text_line = (
            f"Text rendered in image (exact wording): {thumbnail_text}" if thumbnail_text else
            f"No lettering. Editorial reason: {clean(selected['thumbnail_text_reason'])}"
        )
        lines = [
            f"YOUTUBE UPLOAD PACKAGE — {title}",
            f"Channel: {doc.get('channel_id', 'unknown')} | Language: {language} | Video ratio: {ratio}",
            "",
            "1. SELECTED TITLE",
            clean(selected["title"]),
            "",
            "2. DESCRIPTION",
            full_description,
            "",
            "3. YOUTUBE STUDIO TAGS",
            tag_text,
            "",
            "4. THUMBNAIL",
            f"Visual direction: {visual_profile['style']} / {visual_profile['revision']}",
            f"Thumbnail delivery: {visual_profile['width']}x{visual_profile['height']} ({visual_profile['aspect']})",
            f"Concept: {clean(selected['thumbnail_concept'])}\n"
            f"{thumbnail_text_line}\n"
            f"Image file: {clean(selected['thumbnail_file'])}",
            "",
            "5. TEST CANDIDATES",
            f"Mode: {clean(experiment.get('mode')) or 'package'} | Hypothesis: {clean(experiment.get('hypothesis')) or '(not recorded)'}",
        ]
        for candidate in candidates:
            lines.append(
                f"- {clean(candidate['id'])}: {clean(candidate['title'])} | "
                f"{clean(candidate['thumbnail_concept'])} | image: {clean(candidate['thumbnail_file'])}"
            )
        lines.extend(["", "6. PER-EPISODE SEARCH PHRASES"])
        lines.append("\n".join(f"- {item}" for item in search_phrases) or "(none recorded)")
        lines.extend(["", "7. PLAYLISTS", playlist_text(playlist_bundle)])
        lines.extend(["", "8. SHORTS (prepared locally; publish only after owner approval)"])
        if not shorts:
            lines.append("(none recorded; Studio default is 2 Shorts per long video)")
        for short in shorts:
            lines.extend([
                f"- {clean(short.get('id')) or 'short'}: {clean(short['title'])}",
                f"  Cut from: {clean(short['source_passage'])}",
                f"  Hook: {clean(short['hook'])}",
                f"  Closing line: {clean(short['closing_line'])}",
                f"  Related video: {clean(selected['title'])} (set in Studio after the long video is live)",
            ])
        if shorts:
            lines.append("  Before upload, run each Short title through scripts/research_autocomplete.py (title gate).")
        upload = os.path.join(project_dir, "youtube-upload.txt")
        with open(upload, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Exported upload package: {upload}")
    else:
        print("No selected_candidate_id yet. Generate thumbnails with imagegen from the prompt pack, pick one, then rerun.")

    prompt_lines = [
        f"# Thumbnail prompts — {title}",
        "",
        f"Output language: {language} | Target ratio: {visual_profile['aspect']}",
        f"Shared thumbnail visual DNA: {visual_profile['revision']}",
        "The title and the thumbnail make one promise. Each candidate must show this episode's real subject.",
        "Put one emotional Chibi 2D character in the centre doing or reacting to the supported task; never only an object, map or diagram. Draw only sourced details.",
        "No diagrams or arrows on the thumbnail; the core mechanism diagram stays inside the video.",
        "All channels use Chibi 2D; channels differ by palette, setting and thumbnail layout.",
        "Vary candidate visual hypotheses, subject scale, camera angle, action or focal scene enough to test a different idea, not merely a minor color or expression change.",
        "Keep curiosity accurate: do not imply a counterfactual outcome is certain or promise what the episode does not deliver.",
        "Lettering: at most 3 words (about 8 Japanese characters), a concrete number or everyday question the video answers, quoted from the script, that does not repeat the title. A text-free candidate needs an explicit editorial reason.",
        "When thumbnail_text is supplied, render it exactly in the channel language; do not paraphrase, translate, or add lettering.",
        "Use the Codex imagegen skill to generate each image and save it at the path below.",
        "",
    ]
    for candidate in candidates:
        phrase = clean(candidate['thumbnail_text'])
        text_instruction = (
            f"Render only this exact {language} phrase: {phrase}" if phrase else
            "Do not render any text, letters, numbers, labels, logos or watermarks."
        )
        text_summary = (
            f"Text to render in image, exactly: {phrase}" if phrase else
            f"No lettering. Editorial reason: {clean(candidate['thumbnail_text_reason'])}"
        )
        typography = (
            "Render the supplied phrase as large, high-contrast, cleanly spelled thumbnail typography with safe margins. "
            if phrase else "Keep the visual question understandable without lettering. "
        )
        prompt_lines.extend([
            f"## Candidate {clean(candidate['id'])} — {clean(candidate['title'])}",
            "",
            f"Concept: {clean(candidate['thumbnail_concept'])}",
            text_summary,
            f"Save to: {clean(candidate['thumbnail_file'])}",
            "",
            "```text",
            clean(candidate["thumbnail_prompt"]),
            visual_prompt,
            f"Create a YouTube thumbnail at {visual_profile['aspect']} using this episode's resolved visual style. "
            "Centre one emotional Chibi 2D character doing or reacting to the episode's supported task; no diagrams, arrows or route maps on the thumbnail. "
            "Use one dominant subject or relationship, a readable silhouette, strong contrast, "
            "a restrained background, and safe margins. Make the image clear at phone size. Show the "
            "episode's real subject and claim without implying an uncertain or hypothetical result is guaranteed. "
            + typography + "Do not add collage, torn paper, "
            "fake documents, logos, watermarks, gore, or any other lettering.",
            text_instruction,
            "```",
            "",
        ])
    prompt_file = os.path.join(project_dir, "thumbnail-prompts.md")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(prompt_lines) + "\n")
    print(f"Exported thumbnail prompts: {prompt_file}")
    direction_file = os.path.join(project_dir, 'packaging-direction.md')
    with open(direction_file, 'w', encoding='utf-8') as handle:
        handle.write(packaging_guide(visual_profile['channel_name'], language,
                                    visual_profile.get('editorial_packaging') or {}))
    print(f"Exported live title/thumbnail direction: {direction_file}")
    export_episode_playlists(project_dir, playlist_bundle)
    print(f"Exported playlists: {os.path.join(project_dir, 'youtube-playlists.txt')} ({playlist_bundle['status']})")
    if len([item for item in hashtags if item.strip()]) > 3:
        print("Warning: more than three hashtags. YouTube may show only three above the title.")
    if not search_phrases:
        print("Warning: no search phrases recorded.")
    if not shorts:
        print("Warning: no Shorts recorded; Studio default is 2 Shorts per long video.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python export_youtube.py <episode_dir>")
    try:
        run(os.path.abspath(sys.argv[1]))
    except OSError as exc:
        raise SystemExit(f"Error: {exc}")
