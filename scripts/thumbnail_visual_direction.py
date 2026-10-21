"""Compile the shared, subject-led thumbnail visual direction."""

from channels import resolve, load_channel_visual_dna
from animation_prompts import ANIMATION_STYLES
from visual_policy import REALISTIC_STYLE, episode_style


THUMBNAIL_PROFILE = {
    "revision": "human-history-thumbnail-v2",
    "aspect": "16:9",
    "width": 1280,
    "height": 720,
    "style": ANIMATION_STYLES["chibi-2d"],
    "safe_margin_percent": 6,
    "max_text_lines": 2,
    "minimum_text_height_pixels": 64,
}


def resolve_thumbnail_profile(channel_id, episode=None):
    """Return shared visual constraints plus the channel's actual output language."""
    channel = resolve(channel_id)
    style = episode_style(episode) if episode is not None else load_channel_visual_dna(channel).get('default_style', 'chibi-2d')
    return {**THUMBNAIL_PROFILE, "style": ANIMATION_STYLES.get(style, style),
            "revision": "documentary-thumbnail-v2-realistic" if style.startswith("documentary-") else THUMBNAIL_PROFILE["revision"],
            "language": channel["language"],
            "channel_name": channel["display_name"],
            "editorial_packaging": channel.get("packaging_direction", {})}


def thumbnail_visual_prompt(profile):
    """Keep the series style coherent without imposing per-channel art direction."""
    lines = [
        f"SHARED THUMBNAIL VISUAL DNA: {profile['revision']}. This is a visual style, not a channel-specific template.",
        f"Canvas: {profile['aspect']}; final delivery {profile['width']}x{profile['height']}.",
        f"Style: {profile['style']}",
        "Choose the palette, lighting, typography, text placement, camera angle, framing and composition for this episode's subject and promise. Do not force a per-channel color scheme, font, text zone or layout.",
        f"Render at most {profile['max_text_lines']} lines of the supplied exact phrase, preserving all {profile['language']} glyphs and diacritics. Make the phrase easy to read at small size; choose its color and backing for clear contrast with this image.",
        f"Keep essential content {profile['safe_margin_percent']}% inside the edges. Leave the bottom-right 15% width by 16% height clear of text and essential details for the YouTube duration badge.",
        "No extra lettering, channel name, logo, watermark, torn-paper collage or fake archival documents.",
    ]
    rules = profile.get('editorial_packaging') or {}
    if rules:
        lines.extend([
            'CHANNEL EDITORIAL ANGLE — choose a relevant approach for this episode; this is not a fixed visual template.',
            'Viewer question: '+rules.get('viewer_question', ''),
            'Thumbnail direction: '+rules.get('thumbnail_direction', ''),
            'Possible approaches; choose, do not combine all: '+' | '.join(rules.get('thumbnail_approaches', [])),
            'Role of the supplied exact text: '+rules.get('text_role', ''),
            'Opening alignment: '+rules.get('opening_contract', ''),
            'Editorial avoids: '+' | '.join(rules.get('avoid', [])),
            'The supplied candidate prompt and exact phrase specify this image. Do not render these guidance notes as extra lettering.',
        ])
    return "\n".join(lines)
