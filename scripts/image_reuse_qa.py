"""Final-timing reuse QA. Ratios by duration are advisory, shot caps are hard."""
from collections import Counter
import math
from pathlib import Path

from cache_keys import file_fingerprint
from image_reuse import MAX_REUSED_SCENE_SHOT_PERCENT, MAX_REUSES_PER_ORIGINAL_IMAGE


def build_report(segments):
    scene_segments = [segment for segment in segments if segment.get('is_scene_shot') is not False]
    rows = []
    seen = {}
    counts = Counter()
    last_seen = {}
    nearby = []
    warnings = []
    fingerprints = {}
    for scene_index, segment in enumerate(segments):
        if segment.get('is_scene_shot') is False or segment.get('clip'):
            continue
        seconds = float(segment['dur'])
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError('Reuse QA requires finite positive shot durations.')
        path = str(Path(segment['image']).resolve())
        if path not in fingerprints:
            fingerprints[path] = file_fingerprint(path, include_content=True)
        fingerprint = fingerprints[path]
        if not fingerprint['exists']:
            raise FileNotFoundError(path)
        # Different filenames cannot silently bypass the full-image limits.
        content = fingerprint['sha256']
        key = segment.get('shot_key') or str(segment.get('beat_id', '')) + str(segment.get('shot_id', '')) or str(len(rows) + 1)
        original = seen.setdefault(content, key)
        repeated = counts[content] > 0
        index = scene_index
        if content in last_seen and index - last_seen[content] <= 2:
            nearby.append({'shot': key, 'previous_scene_index': last_seen[content], 'scene_index': index, 'source': original})
        last_seen[content] = index
        counts[content] += 1
        row = {'shot': key, 'source': original, 'seconds': seconds, 'repeated_image': repeated,
               'declared_reuse': bool(segment.get('reuse_image_from')), 'sha256': content}
        if repeated and not segment.get('reuse_image_from'):
            warnings.append({'code': 'undeclared_identical_image', 'shot': key, 'source': original})
        rows.append(row)
    reused = sum(row['repeated_image'] for row in rows)
    maximum = len(scene_segments) * MAX_REUSED_SCENE_SHOT_PERCENT // 100
    if reused > maximum:
        raise SystemExit(f'Final images reuse {reused}/{len(scene_segments)} scene shots; the 35% limit allows at most {maximum}. Declare reuse correctly and create originals; do not add filler.')
    for content, count in counts.items():
        if count - 1 > MAX_REUSES_PER_ORIGINAL_IMAGE:
            raise SystemExit(f'[{seen[content]}] final original image is reused {count - 1} times; the maximum is 2.')
    total = sum(float(segment['dur']) for segment in scene_segments)
    repeated_seconds = sum(row['seconds'] for row in rows if row['repeated_image'])
    share = 100 * repeated_seconds / total if total else 0
    if share > MAX_REUSED_SCENE_SHOT_PERCENT:
        warnings.append({'code': 'duration_share_above_shot_cap', 'percent': round(share, 2), 'blocking': False})
    if nearby:
        warnings.append({'code': 'nearby_identical_images', 'occurrences': len(nearby), 'blocking': False})
    return {'basis': 'effective scene durations before dissolve compositing; identical encoded image bytes grouped across paths',
            'scene_shots': len(scene_segments), 'image_shots': len(rows), 'unique_images': len(counts), 'reused_shots': reused,
            'max_reused_shots': maximum, 'scene_seconds': round(total, 3),
            'reused_seconds': round(repeated_seconds, 3), 'reused_duration_percent': round(share, 2),
            'nearby_returns': nearby, 'warnings': warnings, 'shots': rows,
            'semantic_review': 'Required for every reuse against narration, visible action/state, text and crop. Metadata and matching files do not establish semantic suitability.'}
