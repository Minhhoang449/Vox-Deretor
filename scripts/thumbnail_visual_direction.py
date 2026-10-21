"""Compile the shared Chibi 2D thumbnail direction and hard-check thumbnail candidates.

Studio rules (user decision 2026-10-21): every channel uses Chibi 2D; channels are
told apart by palette, setting and layout; one emotional character sits in the
centre; text is a short surprising true claim that does not repeat the title;
no diagrams/arrows on thumbnails; every drawn detail has a source; museum images
need a recorded licence.
"""
import argparse
import json
import re
import sys

from channels import resolve, load_channel_visual_dna
from animation_prompts import ANIMATION_STYLES


THUMBNAIL_PROFILE = {
    "revision": "studio-chibi-thumbnail-v4",
    "aspect": "16:9",
    "width": 1280,
    "height": 720,
    "style": ANIMATION_STYLES["chibi-2d"],
    "safe_margin_percent": 6,
    "max_text_lines": 2,
    "max_text_words": 3,
    "max_text_chars_cjk": 8,
    "minimum_text_height_pixels": 64,
}

CENTRE_CHARACTER_RULE = (
    "Put exactly one emotional Chibi 2D character in the centre of the frame, doing or reacting to "
    "the episode's supported task. Never make the thumbnail only an object, map or diagram. "
    "Draw only details the sources support; show damaged or interpreted parts of an artifact as such.")
TONE_RULE = (
    "Tone: cute, humorous, slightly mischievous Chibi with exaggerated, readable expressions "
    "(a cheeky grin, comic strain, wide-eyed surprise). Never mock real people, ethnic groups or cultures, "
    "and never add a detail the sources do not support just for the joke.")
NO_DIAGRAM_RULE = "No diagrams, arrows, route maps or cutaways on the thumbnail; keep the one core mechanism diagram inside the video."

DIAGRAM_WORDS = re.compile(r"\b(diagram|diagrams|arrow|arrows|cutaway|cross-section|schematic|route map|flowchart|infographic)\b|矢印|図解|断面図|sơ đồ|mũi tên", re.I)
HUMAN_WORDS = re.compile(r"\b(person|people|man|woman|child|worker|villager|maker|farmer|hunter|cook|baker|citizen|trader|priest|scribe|potter|fisher|mother|father|elder|herder|builder|girl|boy|character|he|she|lookout|sailor|soldier|guard|merchant|monk|shepherd|carrier|labourer|laborer|weaver|smith)\b|人|子ども|男|女|người|nhân vật", re.I)
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
STOPWORDS = {"trên", "dưới", "của", "và", "là", "có", "cho", "với", "những", "các", "một", "ở", "trong", "bằng", "a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "is", "it", "did", "do", "how", "why", "what"}
JA_PARTICLES = set("のはをがにでとも")
CJK_LANGS = {"ja", "zh", "ko"}


def resolve_thumbnail_profile(channel_id, episode=None):
    """Return the shared Chibi profile plus the channel's language, palette, setting and layout."""
    channel = resolve(channel_id)
    dna = load_channel_visual_dna(channel)
    identity = (channel.get("packaging_direction") or {}).get("thumbnail_identity") or dna.get("thumbnail_identity") or {}
    return {**THUMBNAIL_PROFILE,
            "language": channel["language"],
            "channel_name": channel["display_name"],
            "channel_identity": identity,
            "editorial_packaging": channel.get("packaging_direction", {})}


def thumbnail_visual_prompt(profile):
    lines = [
        f"SHARED THUMBNAIL VISUAL DNA: {profile['revision']}. All channels use Chibi 2D.",
        f"Canvas: {profile['aspect']}; final delivery {profile['width']}x{profile['height']}.",
        f"Style: {profile['style']}",
        CENTRE_CHARACTER_RULE,
        TONE_RULE,
        NO_DIAGRAM_RULE,
        "Channels are told apart by palette, setting and thumbnail layout, never by a different art style.",
        f"Render at most {profile['max_text_lines']} lines of the supplied exact phrase, preserving all {profile['language']} glyphs and diacritics.",
        f"Keep essential content {profile['safe_margin_percent']}% inside the edges. Leave the bottom-right 15% width by 16% height clear for the YouTube duration badge.",
        "No extra lettering, channel name, logo, watermark, torn-paper collage or fake archival documents.",
    ]
    identity = profile.get('channel_identity') or {}
    for key in ("palette", "setting", "layout"):
        if identity.get(key):
            lines.append(f"Channel {key}: {identity[key]}")
    rules = profile.get('editorial_packaging') or {}
    if rules:
        lines.extend([
            'CHANNEL EDITORIAL ANGLE — guidance only; the centre-character and no-diagram rules above still apply.',
            'Viewer question: ' + rules.get('viewer_question', ''),
            'Thumbnail direction: ' + rules.get('thumbnail_direction', ''),
            'Role of the supplied exact text: ' + rules.get('text_role', ''),
            'Opening alignment: ' + rules.get('opening_contract', ''),
            'Editorial avoids: ' + ' | '.join(rules.get('avoid', [])),
            'Do not render these guidance notes as extra lettering.',
        ])
    return "\n".join(lines)


QUESTION_WORDS = re.compile(r"^(how|why|what|which|who|where|when|did|does|do|is|are|can|could)\b|^(vì sao|tại sao|sao|thế nào|làm sao)|^¿|なぜ|どう|何|か[?？]?$", re.I)


def _words(text):
    """Split into words; a number plus its unit (1.2 KM) counts as one word."""
    raw = [w for w in re.findall(r"[\w.'’%]+", text.lower()) if w.strip(".")]
    merged = []
    for w in raw:
        merged.append(w)  # strict: a number and its unit are two words (user decision)
    return merged


def check_thumbnail_text(text, title, language):
    """Hard checks: <=3 words (<=8 chars CJK), a statement not a question, and it must not
    repeat any content word of the title."""
    errors = []
    text = (text or "").strip()
    if not text:
        return ["thumbnail_text is empty; the studio rule needs a short surprising true claim."]
    if text.endswith(("?", "？")) or QUESTION_WORDS.search(text):
        errors.append("thumbnail_text is a question; use a surprising true claim from the script.")
    if language in CJK_LANGS or CJK.search(text):
        chars = re.sub(r"[\s「」『』、。！？!?・…]", "", text)
        if len(chars) > THUMBNAIL_PROFILE["max_text_chars_cjk"]:
            errors.append(f"thumbnail_text has {len(chars)} characters; max {THUMBNAIL_PROFILE['max_text_chars_cjk']}.")
        title_clean = re.sub(r"\s", "", title or "")
        # Japanese has no spaces: a repeated 2-character kanji/kana run counts as a repeated word.
        content = [chars[i:i + 2] for i in range(len(chars) - 1)
                   if CJK.search(chars[i:i + 2]) and not JA_PARTICLES.intersection(chars[i:i + 2])]
    else:
        words = _words(text)
        if len(words) > THUMBNAIL_PROFILE["max_text_words"]:
            errors.append(f"thumbnail_text has {len(words)} words; max {THUMBNAIL_PROFILE['max_text_words']}.")
        content = [w.strip(".?!") for w in words if w.strip(".?!") not in STOPWORDS]
        title_clean = {w.strip(".?!") for w in _words(title or "")}
    repeats = sorted({w for w in content if w in title_clean})
    if repeats:
        errors.append("thumbnail_text repeats the title (" + ", ".join(repeats) + "); add new information.")
    return errors


def check_thumbnail_candidate(candidate, language, title=None, narration=None):
    """Return a list of rule violations; empty means the candidate passes the hard checks."""
    errors = check_thumbnail_text(candidate.get("thumbnail_text"), title or candidate.get("title", ""), language)
    character = candidate.get("character")
    if isinstance(character, str):
        character = {"description": character}
    character = character or {}
    if not str(character.get("description", "")).strip():
        errors.append("character is missing; one emotional Chibi character must sit in the centre.")
    elif not HUMAN_WORDS.search(character["description"]) and not character.get("is_human"):
        errors.append("character does not name a human subject.")
    emotion = str(candidate.get("emotion") or character.get("emotion") or "").strip().lower()
    if not emotion:
        errors.append("emotion is missing.")
    elif emotion in {"neutral", "none", "calm", "blank", "shock", "shocked"}:
        errors.append(f"emotion '{emotion}' is not a readable situational emotion.")
    if character.get("position", "center") not in {"center", "centre"}:
        errors.append("character position must be center.")
    visual_text = " ".join(str(candidate.get(k, "")) for k in ("thumbnail_concept", "thumbnail_prompt", "thumbnail_text"))
    if DIAGRAM_WORDS.search(re.sub(r"\b(no|without|never)\s+(diagrams?|arrows?)(,?\s*(or|and)?\s*(diagrams?|arrows?))*", "", visual_text, flags=re.I)):
        errors.append("thumbnail uses a diagram/arrow/route map; keep it inside the video.")
    source_line = str(candidate.get("text_source_line") or candidate.get("text_source") or "").strip()
    if not source_line:
        errors.append("text_source_line is missing; quote the script line behind the thumbnail text.")
    else:
        norm = lambda v: re.sub(r"\s+", " ", v).strip().lower()
        if narration and norm(source_line) not in norm(narration):
            errors.append("text_source_line is not in the approved narration.")
        for num in re.findall(r"\d+(?:[.,]\d+)?", candidate.get("thumbnail_text") or ""):
            if num not in source_line:
                errors.append(f"number {num} in thumbnail_text is not in text_source_line.")
    details = candidate.get("details")
    if details is not None:
        for i, d in enumerate(details if isinstance(details, list) else [details]):
            if not (isinstance(d, dict) and str(d.get("detail", "")).strip() and str(d.get("source", "")).strip()):
                errors.append(f"details[{i}] needs both detail and source.")
    errors.extend(check_museum_images(candidate.get("museum_images") or []))
    return errors


def check_museum_images(images):
    errors = []
    for i, img in enumerate(images):
        lic = str((img or {}).get("licence") or (img or {}).get("license") or "").strip()
        if not lic:
            errors.append(f"museum_images[{i}] has no licence field; confirm Open Access before use.")
        if not str((img or {}).get("licence_url") or (img or {}).get("source_url") or "").strip():
            errors.append(f"museum_images[{i}] needs licence_url or source_url.")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Hard-check thumbnail candidates in a JSON file.")
    parser.add_argument("candidates_json")
    parser.add_argument("--language", default="en")
    args = parser.parse_args(argv)
    with open(args.candidates_json, encoding="utf-8-sig") as handle:
        data = json.load(handle)
    failed = 0
    for cand in data if isinstance(data, list) else [data]:
        errs = check_thumbnail_candidate(cand, cand.get("language", args.language))
        failed += bool(errs)
        print(("PASS " if not errs else "FAIL ") + str(cand.get("id", cand.get("thumbnail_text"))))
        for e in errs:
            print("  - " + e)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
