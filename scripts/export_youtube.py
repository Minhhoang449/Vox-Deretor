#!/usr/bin/env python3
"""
Validate YouTube packaging on beats.json and export thumbnail prompts.

Codex fills youtube_metadata, this script writes thumbnail-prompts.md, Codex
generates each thumbnail image, then a second run (after selected_candidate_id
and the chosen file exist) writes youtube-upload.txt.

Rules match Vox-AI export_youtube_metadata.py: 1–3 candidates, title ≤ 100
characters, description + hashtags ≤ 5000, studio tags ≤ 500.

Usage: python export_youtube.py <episode_dir>
"""
import json
import os
import sys

from local_guard import refuse_out_dir


def clean(value):
    return value.strip() if isinstance(value, str) else ""


def run(project_dir):
    refuse_out_dir(project_dir)
    path = os.path.join(project_dir, "beats.json")
    with open(path, encoding="utf-8-sig") as f:
        doc = json.load(f)
    metadata = doc.get("youtube_metadata") or {}
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
            "Each needs id, title, thumbnail_concept, thumbnail_prompt, thumbnail_file."
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
        if len(title) > 100:
            raise SystemExit(f"Candidate {candidate_id} title is {len(title)} characters; max is 100.")
        for key in ("thumbnail_concept", "thumbnail_prompt", "thumbnail_file"):
            if not clean(candidate.get(key)):
                raise SystemExit(f"Candidate {candidate_id} needs {key}.")
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
            raise SystemExit(f"Selected thumbnail is missing: {image}. Codex must generate it first.")

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
    language = doc.get("language", "unknown")
    title = doc.get("topic") or doc.get("project") or "Untitled episode"
    research = metadata.get("packaging_research") or []
    search_phrases = metadata.get("search_phrases") or []
    experiment = metadata.get("experiment") or {}

    if selected:
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
            f"Concept: {clean(selected['thumbnail_concept'])}\n"
            f"Overlay text (add as editable text in the editor): {clean(selected.get('thumbnail_text')) or '(none)'}\n"
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
        upload = os.path.join(project_dir, "youtube-upload.txt")
        with open(upload, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Exported upload package: {upload}")
    else:
        print("No selected_candidate_id yet. Codex generates the thumbnails, you pick one, then rerun.")

    prompt_lines = [
        f"# Thumbnail prompts — {title}",
        "",
        f"Channel: {doc.get('channel_id', 'unknown')} | Language: {language} | Target ratio: {ratio}",
        "The title and the thumbnail make one promise. Each candidate must show this episode's real subject.",
        "Make the candidates different in composition, not just background color.",
        "If thumbnail_text is set, render only that exact text in the channel language and keep its spelling.",
        "If thumbnail_text is empty, render no lettering.",
        "Codex generates each image and saves it at the path below.",
        "",
    ]
    for candidate in candidates:
        prompt_lines.extend([
            f"## Candidate {clean(candidate['id'])} — {clean(candidate['title'])}",
            "",
            f"Concept: {clean(candidate['thumbnail_concept'])}",
            f"Optional overlay text: {clean(candidate.get('thumbnail_text')) or '(none)'}",
            f"Save to: {clean(candidate['thumbnail_file'])}",
            "",
            "```text",
            clean(candidate["thumbnail_prompt"]),
            f"Create a YouTube thumbnail at {ratio}. One dominant subject, a readable silhouette, "
            "clear contrast, a simple background, and safe margins. It must still read when very small "
            "on a phone. Match the episode's real claim. Original layered cut-paper collage. "
            "No logos, watermarks, gore, fake documents, or extra lettering beyond the overlay above.",
            "```",
            "",
        ])
    prompt_file = os.path.join(project_dir, "thumbnail-prompts.md")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(prompt_lines) + "\n")
    print(f"Exported thumbnail prompts: {prompt_file}")
    if len([item for item in hashtags if item.strip()]) > 3:
        print("Warning: more than three hashtags. YouTube may show only three above the title.")
    if not search_phrases:
        print("Warning: no search phrases recorded.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python export_youtube.py <episode_dir>")
    try:
        run(os.path.abspath(sys.argv[1]))
    except OSError as exc:
        raise SystemExit(f"Error: {exc}")
