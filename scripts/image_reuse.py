"""Resolve explicitly related shots to the same full-frame scene still.

Reuse is an editorial decision, never a similarity guess. No copies, crops,
new prompts, or image-generation requests are needed for a reused shot.
"""

from animation_prompts import resolve_people_policy
from visual_policy import is_video_shot

MAX_REUSED_SCENE_SHOT_PERCENT = 35
MAX_REUSES_PER_ORIGINAL_IMAGE = 2


def shot_rows(doc):
    for beat in doc.get("beats") or []:
        for shot in beat.get("shots") or [beat]:
            if shot.get("kind") != "host" and not is_video_shot(shot):
                key = str(beat["id"])
                if beat.get("shots"):
                    key += str(shot.get("id", ""))
                yield beat, shot, key


def character_ids(shot):
    value = shot.get("characters") or []
    return {str(item) for item in ([value] if isinstance(value, str) else value)}


def image_wording(shot):
    wording = str(shot.get("in_scene_text") or shot.get("prompt_text_exception") or "").strip()
    if shot.get("image_text_policy") == "none":
        return ""
    return wording


def image_sources(doc, *, enforce_limits=False):
    """Return shot-key -> original-shot-key, checking references before mutation."""
    shots = {}
    for _, shot, key in shot_rows(doc):
        if key in shots:
            raise SystemExit(f"Duplicate shot key {key!r}; use unique beat/shot IDs.")
        shots[key] = shot
    sources = {}
    for key in shots:
        chain = []
        current = key
        while current not in sources:
            if current in chain:
                raise SystemExit("Image reuse cycle: " + " -> ".join(chain + [current]))
            chain.append(current)
            shot = shots[current]
            target = shot.get("reuse_image_from")
            if "reuse_image_from" not in shot:
                sources[current] = current
                break
            if not isinstance(target, str) or target not in shots:
                raise SystemExit(f"[{current}] unknown reuse_image_from {target!r}; use a still shot key from this episode.")
            if not str(shot.get("reuse_reason") or "").strip():
                raise SystemExit(f"[{current}] needs reuse_reason explaining why the existing full image fits this passage.")
            current = target
        root = sources[current]
        for item in chain:
            sources[item] = root
    for key, source_key in sources.items():
        if key == source_key:
            continue
        shot, original = shots[key], shots[source_key]
        if "visual_state" in shot:
            if "visual_state" not in original or shot["visual_state"] != original["visual_state"]:
                raise SystemExit(f"[{key}] reused image has a different or unknown visual_state from [{source_key}]; create a new still or define the matching source state.")
        if "characters" in shot and character_ids(shot) != character_ids(original):
            raise SystemExit(f"[{key}] reused full image has different characters from [{source_key}]; create a new still.")
        if ("people_policy" in shot or "characters" in shot) and resolve_people_policy(shot) != resolve_people_policy(original):
            raise SystemExit(f"[{key}] reused full image has a different people policy from [{source_key}]; create a new still.")
        wording = str(shot.get("in_scene_text") or shot.get("prompt_text_exception") or "").strip()
        source_wording = image_wording(original)
        if wording and wording != source_wording:
            raise SystemExit(f"[{key}] cannot change text in reused image [{source_key}]; create a new still.")
        if shot.get("image_text_policy") == "none" and source_wording:
            raise SystemExit(f"[{key}] reused image [{source_key}] contains text; full-frame reuse cannot remove it.")
        if (shot.get("image_text_policy") == "contextual" and not source_wording
                and (original.get("image_text_policy") or doc.get("image_text_policy")) == "none"):
            raise SystemExit(f"[{key}] reused image [{source_key}] is text-free; create a new still to add text.")
    if enforce_limits:
        scene_keys = [key for _, _, key in shot_rows(doc)]
        reused_keys = [key for key in scene_keys if sources[key] != key]
        scene_count = sum(1 for beat in doc.get("beats") or []
                          for shot in beat.get("shots") or [beat]
                          if shot.get("kind") != "host")
        max_reused = scene_count * MAX_REUSED_SCENE_SHOT_PERCENT // 100
        if len(reused_keys) > max_reused:
            raise SystemExit(
                f"Image reuse is {len(reused_keys)}/{scene_count} scene shots; "
                f"the {MAX_REUSED_SCENE_SHOT_PERCENT}% limit allows at most {max_reused}. "
                "Create original stills for some reused shots; do not add filler shots."
            )
        reuse_counts = {}
        for key in reused_keys:
            source_key = sources[key]
            reuse_counts[source_key] = reuse_counts.get(source_key, 0) + 1
        for source_key, count in reuse_counts.items():
            if count > MAX_REUSES_PER_ORIGINAL_IMAGE:
                raise SystemExit(
                    f"[{source_key}] original image is reused {count} times; "
                    f"the maximum is {MAX_REUSES_PER_ORIGINAL_IMAGE} reuse appearances "
                    "after its first appearance. Create a new still for an additional shot."
                )
    return sources


def apply_image_reuse(doc):
    """Resolve paths again at assembly, so aliases never render an obsolete copy."""
    sources = image_sources(doc, enforce_limits=True)
    shots = {key: shot for _, shot, key in shot_rows(doc)}
    for key, source_key in sources.items():
        if key == source_key:
            continue
        original = shots[source_key]
        path = original.get("keyframe_path") or original.get("image_path")
        if not path:
            raise SystemExit(f"[{key}] source image [{source_key}] is not registered. Run codex_prompts.py --register.")
        current_hash = original.get("keyframe_prompt_current_hash")
        if current_hash and current_hash != original.get("keyframe_prompt_hash"):
            raise SystemExit(f"[{key}] source image [{source_key}] needs generation/review and registration before reuse.")
        shots[key]["keyframe_path"] = path
        shots[key].pop("keyframe_url", None)
    return sources
