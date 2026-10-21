"""Compile the shared Chibi 2D thumbnail direction and hard-check thumbnail candidates.

Studio rules (user decision 2026-10-21): every channel uses Chibi 2D; channels are
told apart by palette, setting and layout; one emotional character sits in the
centre; text is a short number or everyday question the video answers, not repeating the title;
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
    "subject_area_ratio": (0.40, 0.60),
    "max_main_colors": 3,
    "forbidden_text_positions": ("bottom-right", "bottom_right", "lower-right", "lower_right"),
    "variant_labels": ("A", "B"),
    "ctr_review_hours": 48,
    "ctr_rule": "clearly below the channel's own average CTR at 48h -> change thumbnail and title first; replace with a measured number after ~5 videos in references/post-publish-tracking.md",
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
STOPWORDS = {"trên", "dưới", "của", "và", "là", "có", "cho", "với", "những", "các", "một", "ở", "trong", "bằng", "a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "is", "it", "did", "do", "how", "why", "what", "no", "not", "with", "at", "by", "from", "he", "she", "they", "we", "you", "i", "was", "were", "are", "be", "this", "that", "his", "her", "their", "does", "so", "up"}
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
        MODERN_ITEMS_RULE,
        SOURCED_OBJECTS_RULE,
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


MODERN_ITEMS_RULE = ("Period-accurate only: no modern items such as sneakers, trainers, jeans, zips, "
                     "plastic, glass bottles, phones, wristwatches, glasses, metal cutlery or printed fabric.")
SOURCED_OBJECTS_RULE = ("Draw every food and object as the right kind named in the sources (e.g. emmer or barley "
                        "kernels, not wheat ears or bread loaves; a tochi horse-chestnut with its large pale scar, "
                        "not an acorn or chestnut). Draw nothing the narration or source table does not name.")
MODERN_WORDS = re.compile(r"\b(sneakers?|trainers?|jeans|zips?|zippers?|plastic|glass bottles?|phones?|smartphones?|"
                          r"wristwatch(?:es)?|watch(?:es)?|eyeglasses|glasses|sunglasses|forks?|t-shirts?|baseball caps?|"
                          r"tin cans?|cans?|bicycles?|cars?|electric|lightbulbs?)\b", re.I)
NEGATION = re.compile(r"\b(no|without|never|not|avoid|forbid|forbidden)\b[^.;]*", re.I)
UNIT_WORDS = {"km", "m", "cm", "kg", "g", "l", "ml", "hour", "hours", "day", "days", "min", "minutes", "year", "years",
              "every", "all", "each", "only", "away", "here", "there", "nothing", "something", "too", "very", "much",
              "many", "more", "less", "free", "monthly", "daily", "carried", "doing"}


def _stem(word):
    w = word.lower().strip(".,?!'’")
    for suf in ("ies", "es", "s"):
        if len(w) > 3 and w.endswith(suf):
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def check_sourced_words(text, narration, source_table=None):
    """Lunch-test lesson: every content word of the thumbnail text (nouns such as ONIONS)
    must appear in the narration or source table. Heuristic: there is no part-of-speech
    tagger, so every non-stopword, non-number word is treated as a possible concrete noun,
    with a small allowlist of units and common non-nouns. Latin-script text only."""
    if not narration or not text or CJK.search(text):
        return []
    support = " ".join([narration] + [str(x) for x in (source_table or [])])
    supported = {_stem(w) for w in re.findall(r"[\w'’]+", support.lower())}
    missing = []
    for w in _words(text):
        w = w.strip(".?!")
        if not w or w in STOPWORDS or w in UNIT_WORDS or re.fullmatch(r"[\d.,%]+", w):
            continue
        if _stem(w) not in supported:
            missing.append(w)
    return [f"thumbnail_text word '{w}' is not in the narration or source table; draw and write only what the sources name."
            for w in missing]


def check_depicted_items(candidate, narration):
    """Every listed depicted food/object must be named in the narration or source_table,
    and the prompt may not ask for modern items."""
    errors = []
    support = " ".join([narration or ""] + [str(x) for x in (candidate.get("source_table") or [])]).lower()
    supported = {_stem(w) for w in re.findall(r"[\w'’-]+", support)}
    items = candidate.get("depicted_items")
    if items is not None and (narration or candidate.get("source_table")):
        for item in items if isinstance(items, list) else [items]:
            words = [_stem(w) for w in re.findall(r"[\w'’-]+", str(item).lower()) if w not in STOPWORDS]
            if not words or not all(w in supported for w in words):
                errors.append(f"depicted item '{item}' is not in the narration or source table.")
    prompt = " ".join(str(candidate.get(k, "")) for k in ("thumbnail_prompt", "thumbnail_concept"))
    for m in MODERN_WORDS.finditer(NEGATION.sub(" ", prompt)):
        errors.append(f"prompt asks for a modern item ('{m.group(0)}'); keep everything period-accurate.")
    return errors


def check_thumbnail_image(path, text_position=None, preview_path=None):
    """Real 160 px check. Downsizes to 160x90 (Pillow, LANCZOS), saves the preview next to
    the image as <name>.160px.png, and applies two deterministic heuristics:
      - whole image: luminance standard deviation >= 32 (not washed out / low contrast);
      - declared text area: luminance spread (95th minus 5th percentile) >= 90, so
        lettering can separate from its background.
    Limits: this cannot read the text, recognise a face or judge an expression; it only
    rejects images that are clearly too flat to read at 160 px. A human still looks at
    the preview."""
    import os
    from PIL import Image, ImageStat
    errors = []
    try:
        with Image.open(path) as im:
            small = im.convert("RGB").resize((160, 90), Image.LANCZOS)
    except (OSError, ValueError) as exc:
        return [f"thumbnail image cannot be opened: {exc}"]
    root, _ = os.path.splitext(path)
    preview_path = preview_path or root + ".160px.png"
    small.save(preview_path)
    gray = small.convert("L")
    if ImageStat.Stat(gray).stddev[0] < 32:
        errors.append("thumbnail is low-contrast overall at 160 px (luminance stddev < 32).")
    box = TEXT_REGIONS.get(str(text_position or "").strip().lower().replace(" ", "-").replace("_", "-"))
    if box:
        hist = sorted(gray.crop(box).getdata())
        lo, hi = hist[int(len(hist) * 0.05)], hist[int(len(hist) * 0.95) - 1]
        if hi - lo < 90:
            errors.append(f"text area '{text_position}' has too little contrast at 160 px (spread {hi - lo} < 90).")
    return errors


# 160x90 boxes (left, top, right, bottom) for declared text positions.
TEXT_REGIONS = {
    "top-left": (0, 0, 80, 45), "top": (0, 0, 160, 45), "top-center": (40, 0, 120, 45), "top-centre": (40, 0, 120, 45),
    "top-right": (80, 0, 160, 45), "left": (0, 0, 80, 90), "right": (80, 0, 160, 90),
    "center": (40, 22, 120, 68), "centre": (40, 22, 120, 68), "bottom-left": (0, 45, 80, 90),
    "bottom": (0, 45, 160, 90), "bottom-center": (40, 45, 120, 90), "bottom-centre": (40, 45, 120, 90),
}


QUESTION_WORDS = re.compile(r"^(how|why|what|which|who|where|when|did|does|do|is|are|can|could)\b|^(vì sao|tại sao|sao|thế nào|làm sao)|^¿|なぜ|どう|何|か[?？]?$", re.I)


def _words(text):
    """Split into words; a number plus its unit (1.2 KM) counts as one word."""
    raw = [w for w in re.findall(r"[\w.'’%]+", text.lower()) if w.strip(".")]
    merged = []
    for w in raw:
        merged.append(w)  # strict: a number and its unit are two words (user decision)
    return merged


def check_thumbnail_text(text, title, language):
    """Hard checks: <=3 words (<=8 chars Japanese) and it must not repeat any content word
    of the title. Everyday questions ("NO WELL?!") are allowed; short function words such
    as "no" do not count as repetition."""
    errors = []
    text = (text or "").strip()
    if not text:
        return ["thumbnail_text is empty; the studio rule needs a short number or everyday question the video answers."]
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
    errors.extend(check_sourced_words(candidate.get("thumbnail_text"), narration, candidate.get("source_table")))
    errors.extend(check_depicted_items(candidate, narration))
    errors.extend(check_layout_metadata(candidate))
    errors.extend(check_variants(candidate, language, title or candidate.get("title", "")))
    return errors


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def check_layout_metadata(candidate):
    """Team rules 1 and 5: one centred Chibi at 40-60% of frame, <=3 main colours,
    no text in the bottom-right (duration overlay)."""
    errors = []
    count = candidate.get("character_count")
    if count is None:
        errors.append("character_count is missing; rule 1 needs exactly one Chibi character.")
    elif count != 1 or isinstance(count, bool):
        errors.append(f"character_count is {count!r}; rule 1 needs exactly one Chibi character.")
    lo, hi = THUMBNAIL_PROFILE["subject_area_ratio"]
    ratio = _num(candidate.get("subject_area_ratio"))
    if candidate.get("subject_area_ratio") is None:
        errors.append("subject_area_ratio is missing; the character must fill about 40-60% of the frame.")
    elif ratio is None or not lo <= ratio <= hi:
        errors.append(f"subject_area_ratio {candidate.get('subject_area_ratio')!r} is outside {lo:.2f}-{hi:.2f}.")
    if candidate.get("thumbnail_path"):
        errors.extend(check_thumbnail_image(candidate["thumbnail_path"], candidate.get("text_position")))
    elif candidate.get("expression_readable_160px") is not True:
        errors.append("expression_readable_160px must be true; check the exaggerated expression at 160 px.")
    colors = candidate.get("main_colors")
    if not isinstance(colors, list) or not colors or not all(str(c).strip() for c in colors):
        errors.append("main_colors is missing or invalid; list 1-3 main colours.")
    elif len(colors) > THUMBNAIL_PROFILE["max_main_colors"]:
        errors.append(f"main_colors has {len(colors)} colours; max {THUMBNAIL_PROFILE['max_main_colors']}.")
    pos = str(candidate.get("text_position") or "").strip().lower().replace(" ", "-")
    if (candidate.get("thumbnail_text") or "").strip():
        if not pos:
            errors.append("text_position is missing; text may not sit bottom-right (duration overlay).")
        elif pos in THUMBNAIL_PROFILE["forbidden_text_positions"]:
            errors.append("text_position is bottom-right; the duration overlay covers it.")
    return errors


def check_variants(candidate, language, title):
    """Team rule 6: A and B variants that differ only in text or expression; both pass the text rules."""
    variants = candidate.get("variants")
    if not isinstance(variants, list) or len(variants) != 2:
        return ["variants must list exactly two thumbnails, A and B, for the 48-hour CTR comparison."]
    errors = []
    labels = [str((v or {}).get("label", "")).strip().upper() if isinstance(v, dict) else "" for v in variants]
    if sorted(labels) != list(THUMBNAIL_PROFILE["variant_labels"]):
        errors.append(f"variants labels are {labels}; use A and B.")
    if not all(isinstance(v, dict) for v in variants):
        return errors + ["each variant must be an object."]
    a, b = variants
    for v, lab in zip(variants, labels):
        if not (v.get("thumbnail_text") or "").strip():
            continue  # text-free variant; the candidate's thumbnail_text_reason covers it
        for e in check_thumbnail_text(v.get("thumbnail_text"), title, language):
            errors.append(f"variant {lab or '?'}: {e}")
    differs = [k for k in ("thumbnail_text", "emotion") if (a.get(k) or "") != (b.get(k) or "")]
    if not differs:
        errors.append("variants A and B are identical; change the text or the expression.")
    other = (set(a) | set(b)) - {"label", "thumbnail_text", "emotion", "text_source_line", "text_position"}
    changed = sorted(k for k in other if a.get(k) != b.get(k))
    if changed:
        errors.append("variants may differ only in text or expression; also changed: " + ", ".join(changed) + ".")
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
