"""Purpose-led still camera planning; metadata hints are not image analysis."""
import json
import math
from pathlib import Path
import re

GENERIC_CAMERAS = {
    '', 'auto', 'slow push-in, then hold',
    'subtle pull-back to reveal surrounding space',
    'gentle pan left to right, then hold',
    'slow tilt from architecture to focal detail',
}
CAMERA_METADATA = ('visual_intent', 'in_scene_text', 'camera_intent',
                   'camera_direction', 'camera_motion_safe', 'image_source_key',
                   'reuse_image_from', 'is_scene_shot', 'visual_state')


def shot_camera_metadata(shot, source=None):
    """Carry the actual baked text of a reused source into motion planning."""
    animation = shot.get('animation') or {}
    original = source if source is not None else shot
    fields = {k: animation[k] for k in ('camera_intent', 'camera_direction', 'camera_motion_safe') if k in animation}
    fields['visual_intent'] = shot.get('visual_intent', original.get('visual_intent', ''))
    fields['in_scene_text'] = original.get('in_scene_text') or original.get('prompt_text_exception') or ''
    if 'reuse_image_from' in shot:
        fields['reuse_image_from'] = shot['reuse_image_from']
    if 'visual_state' in shot:
        fields['visual_state'] = shot['visual_state']
    return fields


def _hints(segment):
    return ' '.join(json.dumps(segment.get(k, ''), ensure_ascii=False) if isinstance(segment.get(k), (dict, list))
                    else str(segment.get(k) or '') for k in ('scene', 'framing', 'visual_intent')).lower()


def _automatic(segment, repeated):
    intent = str(segment.get('camera_intent') or '').strip().lower()
    if intent not in ('', 'read', 'compare', 'orient', 'follow', 'reveal', 'inspect', 'observe'):
        raise ValueError('Unknown camera_intent: ' + intent)
    direction = str(segment.get('camera_direction') or '').strip().lower()
    if direction not in ('', 'left', 'right', 'up', 'down'):
        raise ValueError('camera_direction must be left, right, up or down.')
    safe = segment.get('camera_motion_safe')
    if safe is not None and not isinstance(safe, bool):
        raise ValueError('camera_motion_safe must be a boolean.')
    seconds = float(segment.get('camera_duration', segment.get('dur', 0)))
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('Camera duration must be finite and positive.')
    hints = _hints(segment)
    if segment.get('reuse_image_from') or repeated:
        return 'locked-off', 'full-image return; preserve the familiar composition'
    if safe is False:
        return 'locked-off', 'authored motion-safe flag is false'
    if seconds < 4:
        return 'locked-off', 'short shot needs immediate readability'
    if intent in ('read', 'compare', 'orient'):
        return 'locked-off', 'reading/comparison/orientation needs a stable frame'
    text = bool(str(segment.get('in_scene_text') or '').strip())
    diagram = bool(re.search(r'map\b|diagram|cutaway|cross[- ]section|comparison|split[- ]screen|chart|table|ledger|receipt|document|inscription|bản đồ|sơ đồ|mặt cắt|so sánh|biểu đồ|地図|断面|比較|図解|지도|断面図', hints))
    # An authored safe move can deliberately follow part of a labeled diagram.
    if (text or diagram) and safe is not True:
        return 'locked-off', 'labels or explanatory layout; crop safety not confirmed'
    if intent == 'follow':
        if not direction:
            return 'locked-off', 'follow needs an authored direction; no guessed flow'
        return ('pan ' if direction in ('left', 'right') else 'tilt ') + direction, 'follow the authored direction of the subject or flow'
    if intent == 'reveal':
        return 'gentle zoom-out', 'reveal surrounding context without reversing direction'
    if intent == 'inspect':
        return 'gentle zoom-in', 'inspect a non-reading detail; review final crop'
    wide = bool(re.search(r'landscape|panorama|wide room|wide view|establishing|coast|valley|toàn cảnh|phong cảnh|bờ biển|thung lũng|全景|風景|街並み', hints))
    tall = bool(re.search(r'tower|facade|façade|vertical|tall building|tháp|縦|塔', hints))
    close = bool(re.search(r'close[- ]?up|focal detail|cận cảnh|特写|接写', hints))
    if direction and (intent == 'observe' or wide or tall):
        return ('pan ' if direction in ('left', 'right') else 'tilt ') + direction, 'authored viewing direction fits the scene'
    if seconds >= 5 and (wide or intent == 'observe'):
        return 'gentle zoom-out', 'give spatial context; no fixed camera cycle'
    if seconds >= 5 and close:
        return 'gentle zoom-in', 'emphasize the authored focal detail'
    return 'locked-off', 'no supported reason for motion; preserve the full relationship'


def plan_cameras(segments, config):
    policy = config.get('camera_policy', 'balanced')
    if policy not in ('balanced', 'preserve'):
        raise ValueError('stills_camera_policy must be balanced or preserve.')
    seen_images = set()
    planned = []
    for index, item in enumerate(segments):
        segment = dict(item)
        original = str(segment.get('original_camera', segment.get('camera')) or 'auto').strip()
        shot_policy = segment.get('camera_policy', 'auto')
        if shot_policy not in ('auto', 'balanced', 'preserve'):
            raise ValueError(f'Shot {index} has unknown camera_policy {shot_policy!r}.')
        image = str(Path(segment['image']).resolve()) if segment.get('image') else ''
        source = segment.get('image_source_key') or image
        repeated = bool(source and source in seen_images)
        if source:
            seen_images.add(source)
        automatic = shot_policy == 'balanced' or (shot_policy == 'auto' and policy == 'balanced' and original.lower() in GENERIC_CAMERAS)
        segment['original_camera'] = original
        if automatic:
            segment['camera'], segment['camera_reason'] = _automatic(segment, repeated)
        else:
            segment['camera'] = original if original.lower() != 'auto' else 'locked-off'
            segment['camera_reason'] = 'preserved authored direction'
        planned.append(segment)
    return planned
