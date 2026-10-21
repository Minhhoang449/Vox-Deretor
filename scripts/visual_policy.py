"""Shared Chibi visual defaults for new videos; saved episode styles remain explicit."""
import json
from pathlib import Path

REALISTIC_STYLE = "documentary-realistic"
LEGACY_STYLE = "chibi-2d"
VISUAL_DNA = {
    "revision": "human-history-chibi-v3-reference-look",
    "reference": "references/chibi-historical-visual-dna.md",
    "default_style": LEGACY_STYLE,
    "style_name": "Original hand-drawn Chibi 2D educational illustration",
    "subject_selection": "Use the selected channel's visual grammar and the actual narration span.",
    "character_presence": "Use friendly expressive Chibi people for supported actions; in video stills objects, maps and the one core mechanism diagram can lead. Thumbnails always centre one emotional character.",
    "all_channels_style": "chibi-2d",
    "thumbnail_rules": "One emotional Chibi character centred; text <=3 words (~8 Japanese chars), a surprising sourced claim not repeating the title; no diagrams/arrows; every detail sourced; museum images need a licence field (Open Access) before use.",
    "consistency": "Bold clean dark outlines, warm luminous colors, gentle painterly surface texture, restrained cel shading, and researched period/place details; distinguish reconstruction from source evidence.",
    "scene_options": "Original Chibi 2D people, objects, environments, maps, cutaways and explanatory diagrams; no video clips or montage.",
    "prompt_policy": "Use Codex imagegen for original Chibi 2D stills after narration approval and audio review. Do not use Montage or search for video. Keep exact localized labels and visible cast references when relevant.",
    "review": "Review generated images for factual grounding, crop, continuity and explanatory value. Keep factual role and provenance in internal records; do not add visible AI/illustration disclosure labels. Prompt quality alone does not establish visual accuracy.",
}
VISUAL_WORKFLOW = {
    "revision": "imagegen-stills-v1",
    "reference": "references/imagegen-stills.md",
    "source_order": "imagegen_stills",
    "retrieval_tool": "Codex imagegen",
    "providers": [],
    "default_visual_mode": "revideo_stills",
    "generated_still_style": LEGACY_STYLE,
    "source_plan_required": False,
    "existing_episode_policy": "Keep recorded media/style unless the user requests a revision; no automatic migration.",
}


def load_visual_workflow():
    path = Path(__file__).resolve().parents[1] / "config" / "pipeline.json"
    return json.loads(path.read_text(encoding="utf-8-sig")).get("visual_workflow", {})


def episode_style(doc):
    """Unversioned legacy episodes keep their historical fallback."""
    return (doc.get("animation_style")
            or (doc.get("visual_dna") or {}).get("default_style")
            or (doc.get("visual_workflow") or {}).get("generated_still_style")
            or LEGACY_STYLE)


def footage_first(doc):
    return (doc.get("visual_workflow") or {}).get("source_order") == "footage_first"


def imagegen_stills(doc):
    return (doc.get("visual_workflow") or {}).get("source_order") == "imagegen_stills"


def is_video_shot(shot):
    return (shot.get("visual_source") or {}).get("decision") == "video"
