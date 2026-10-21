"""Language-aware caption segmentation, layout and reading limits.

Netflix guides inform the limits; approved narration is never rewritten here.
"""
from functools import lru_cache
import json
import os
import re
import unicodedata

from tts_settings import split_period_pauses

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CaptionLayoutError(ValueError):
    pass


def normalized_text(text, language):
    value = unicodedata.normalize('NFC', str(text))
    return re.sub(r'\s+', '' if language == 'ja' else ' ', value).strip()


def display_text(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', str(text))).strip()


def resolve_policy(doc, language, width=1920, height=1080):
    with open(os.path.join(ROOT, 'config', 'pipeline.json'), encoding='utf-8-sig') as handle:
        config = json.load(handle)
    common = dict(config.get('caption_policy') or {})
    languages = common.pop('languages', {})
    if language not in languages:
        raise ValueError(f'No caption readability profile for language {language!r}.')
    render = dict(config.get('caption_render') or {})
    profile = dict(languages[language])
    policy = {**render, **common, **profile}
    # Explicit episode styling/limits remain supported, after localized defaults.
    overrides = doc.get('caption_render') or {}
    if overrides.get('font') and overrides['font'] != policy['font'] and 'font_file' not in overrides:
        policy['font_file'] = None
    policy.update(overrides)
    policy.update(doc.get('caption_policy') or {})
    policy['quality'] = {**(config.get('caption_quality') or {}), **(doc.get('caption_quality') or {})}
    policy.update(language=language, width=int(width), height=int(height),
                  fps=int((doc.get('format') or {}).get('fps', 30)))
    policy['font_size'] = round(float(policy['font_size']) * height / 1080)
    policy['margin_v'] = round(float(policy['margin_v']) * height / 1080)
    policy['margin_h'] = round(float(policy['margin_h']) * width / 1920)
    policy['max_pixel_width'] = width - 2 * policy['margin_h']
    if policy['max_lines'] not in (1, 2) or policy['max_chars_per_line'] <= 0:
        raise ValueError('Caption layout needs one or two lines and a positive line limit.')
    if policy['position'] not in ('bottom', 'top') or policy['fps'] <= 0:
        raise ValueError('Caption position must be bottom/top and fps must be positive.')
    return policy


def character_count(text, policy):
    total = 0.0
    for char in unicodedata.normalize('NFC', str(text)).replace('\n', ''):
        if unicodedata.combining(char):
            continue
        mode = policy.get('counting', 'characters')
        if mode == 'full_width_equivalent':
            total += 1.0 if unicodedata.east_asian_width(char) in 'FWA' else 0.5
        elif mode == 'hangul_equivalent':
            half = char.isascii() or char.isspace() or unicodedata.category(char).startswith('P') or 'LATIN' in unicodedata.name(char, '')
            total += 0.5 if half else 1.0
        else:
            total += 1
    return total


@lru_cache(maxsize=32)
def measured_font(path, size):
    if not path or not os.path.isfile(path):
        return None
    try:
        from PIL import ImageFont
        return ImageFont.truetype(path, size)
    except (ImportError, OSError):
        return None


def fits_line(text, policy):
    if character_count(text, policy) > float(policy['max_chars_per_line']) + 1e-6:
        return False
    font = measured_font(policy.get('font_file'), policy['font_size'])
    return font is None or font.getlength(text) <= policy['max_pixel_width']


def protected_ranges(text, terms=()):
    spans = []
    for term in terms:
        if term:
            spans.extend((m.start(), m.end()) for m in re.finditer(re.escape(term), text))
    # Keep numbers with scale/currency/unit, and runs of capitalized name words.
    patterns = [r'\b\d+(?:[.,]\d+)*(?:\s+(?:triệu|nghìn|tỷ|million|billion|thousand))?\s+(?:đồng|USD|dollars?|coins?|km|kg|mét|years?)\b',
                r'\b[A-ZÀ-Ỹ][A-Za-z\u00C0-\u024F\u1E00-\u1EFF]+(?:\s+[A-ZÀ-Ỹ][A-Za-z\u00C0-\u024F\u1E00-\u1EFF]+)+']
    for pattern in patterns:
        spans.extend((m.start(), m.end()) for m in re.finditer(pattern, text))
    return spans


def break_positions(text, policy, terms=()):
    spans = protected_ranges(text, terms)
    candidates = list(range(1, len(text))) if policy['language'] == 'ja' else [m.start() for m in re.finditer(r'\s+', text)]
    for pos in candidates:
        if any(start < pos < end for start, end in spans):
            continue
        left, right = text[:pos].rstrip(), text[pos:].lstrip()
        if policy['language'] == 'ja' and text[pos-1].isascii() and text[pos].isascii() and text[pos-1].isalnum() and text[pos].isalnum():
            continue
        if text[pos-1].isdigit() and text[pos].isdigit():
            continue
        if not left or not right or right[0] in ',.;:!?。！？、，）)]」』”’':
            continue
        if left[-1] in '（([「『“':
            continue
        yield pos


def break_penalty(left, right):
    if left[-1:] in ',;:，、':
        return -30
    first = right.split()[0].casefold() if right.split() else ''
    last = left.split()[-1].casefold() if left.split() else ''
    if last in {'the', 'a', 'an', 'to', 'of', 'and', 'but', 'không', 'một', 'những', 'các', 'của', 'el', 'la', 'los', 'las', 'de'}:
        return 40
    return -10 if first in {'and', 'but', 'because', 'và', 'nhưng', 'vì', 'nên', 'pero', 'porque', 'y'} else 0


def wrap_lines(text, policy, terms=()):
    text = display_text(text)
    if fits_line(text, policy):
        return [text]
    if policy['max_lines'] < 2:
        raise CaptionLayoutError(f'Caption does not fit one line: {text}')
    options = []
    for pos in break_positions(text, policy, terms):
        left, right = text[:pos].rstrip(), text[pos:].lstrip()
        if fits_line(left, policy) and fits_line(right, policy):
            a, b = character_count(left, policy), character_count(right, policy)
            score = abs(a - b) + (10 if a > b else 0) + break_penalty(left, right)
            options.append((score, left, right))
    if not options:
        raise CaptionLayoutError(f'Caption cannot fit two lines without breaking a protected term: {text}')
    _, left, right = min(options)
    return [left, right]


def split_phrases(text, policy, terms=()):
    """Full stops first, then punctuation/meaning-aware capacity boundaries."""
    units = []
    for sentence, _ in split_period_pauses(display_text(text)):
        # Question/exclamation marks also end a caption sentence, without modifying speech.
        sentences = re.split(r'(?<=[!?！？])\s+', sentence) if policy['language'] != 'ja' else re.split(r'(?<=[！？])', sentence)
        for remainder in sentences:
            remainder = remainder.strip()
            while remainder:
                try:
                    wrap_lines(remainder, policy, terms)
                    fits = character_count(remainder, policy) <= min(float(policy['target_phrase_characters']), 2 * policy['max_chars_per_line'])
                except CaptionLayoutError:
                    fits = False
                if fits:
                    units.append(remainder)
                    break
                options = []
                for pos in break_positions(remainder, policy, terms):
                    left, right = remainder[:pos].rstrip(), remainder[pos:].lstrip()
                    try:
                        wrap_lines(left, policy, terms)
                    except CaptionLayoutError:
                        continue
                    length = character_count(left, policy)
                    target = min(float(policy['target_phrase_characters']), 2 * policy['max_chars_per_line'])
                    score = abs(target - length) + break_penalty(left, right)
                    options.append((score, -pos, left, right))
                if not options:
                    raise CaptionLayoutError(f'Cannot split caption safely: {remainder}')
                _, _, left, remainder = min(options)
                units.append(left)
    return units
