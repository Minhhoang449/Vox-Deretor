#!/usr/bin/env python3
"""Prompt builders for documentary reconstruction and recorded legacy styles.

This module is intentionally separate from styles.py and clips.py so the local
animation workflow does not inherit the legacy paper-collage look or Atlas motion
constraints.
"""

import json
from functools import lru_cache
from pathlib import Path
from visual_policy import REALISTIC_STYLE, episode_style


@lru_cache(maxsize=1)
def default_image_text_policy():
    with (Path(__file__).resolve().parent.parent / "config" / "pipeline.json").open(
        encoding="utf-8-sig"
    ) as handle:
        return json.load(handle).get("image_text_policy", "contextual")


def compose_in_scene_text_prompt(doc, shot, *, require_text=False):
    """Use exact planned text by default, with explicit project/shot opt-outs."""
    policy = shot.get("image_text_policy") or doc.get("image_text_policy") or default_image_text_policy()
    if policy not in {"contextual", "none"}:
        raise SystemExit(f"Unknown image_text_policy {policy!r}; use contextual or none.")
    wording = str(shot.get("in_scene_text") or shot.get("prompt_text_exception") or "").strip()
    # Explicit shot opt-outs win; exact wording retains the legacy project-level exception.
    if shot.get("image_text_policy") == "none" or (policy == "none" and not wording):
        return (
            "TEXT-FREE SHOT: No readable letters, numbers, labels, signage, subtitles, "
            "logos, watermarks, interface elements, or title cards."
        )
    if not wording:
        if require_text:
            key = shot.get("id") or shot.get("key") or "unnamed shot"
            raise SystemExit(
                f"{key}: contextual image text is the default. Set in_scene_text to the exact "
                "short wording, or image_text_policy: none for a deliberately text-free shot."
            )
        # Legacy prompt consumers can still supply exact wording within the scene description.
        return (
            "IN-SCENE TEXT: Include concise contextual text using only exact wording "
            "supplied in the shot description. Keep it readable at phone size and integrated "
            "into a plausible sign, prop, or map. If no exact wording is supplied, do not "
            "invent it. No subtitles, title cards, logos, watermarks, or interface elements."
        )
    placement = str(shot.get("text_placement") or "a plausible sign, prop, or map label").strip()
    return (
        f"IN-SCENE TEXT: Render this exact wording: {json.dumps(wording, ensure_ascii=False)}. "
        f"Placement: {placement}. Use clear, correctly spelled, high-contrast lettering that "
        "is readable at phone size and remains inside the camera crop. Integrate it into "
        "the scene with period-appropriate lettering; keep it subordinate to the focal action. "
        "Do not add other wording, subtitles, title cards, logos, watermarks, or UI. "
        "Do not present an illustrative label as an authentic historical quotation or document."
    )


ANIMATION_STYLES = {
    "documentary-realistic": (
        "photorealistic documentary reconstruction with natural human proportions, "
        "credible materials, restrained lighting and a plausible documentary lens; "
        "keep lighting, color, texture, geography and period coherent across the episode. "
        "Follow researched geography, engineering, scale and visible state; this is "
        "AI reconstruction, never an authentic archival photograph or event record"
    ),
    "documentary-diagram": (
        "clear documentary explanatory graphics: sourced maps, engineering sections, "
        "flow arrows or comparisons with accurate spatial relationships and readable "
        "localized labels. Simplify deliberately for understanding; photographic "
        "texture and realistic people are unnecessary in a diagram"
    ),
    "chibi-2d": (
        "original polished hand-drawn Chibi 2D educational illustration; friendly expressive "
        "compact characters when useful, bold clean dark outlines, warm luminous colors, "
        "gentle painterly surface texture, restrained cel shading, clear silhouettes and a "
        "strong focal action. Give settings and props enough illustrated detail to feel like "
        "the same world while keeping explanatory relationships easy to read. Apply this finish "
        "to people, objects, buildings, landscapes, maps, cutaways and diagrams. Adapt palette "
        "and detail to researched subject and place; do not copy a reference image's scene"
    ),
    "expressive-2d": (
        "original polished 2D character animation for an educational short film; "
        "expressive poses, clear silhouettes, confident linework, rich but controlled "
        "color, layered depth, and cinematic staging"
    ),
    "graphic-2d": (
        "original 2D animated explainer graphics; clean geometric forms, purposeful "
        "shape transformations, animated diagrams and characters, crisp edges, and "
        "strong visual hierarchy"
    ),
    "stylized-3d": (
        "original stylized 3D animation; expressive but grounded characters, tactile "
        "materials, readable silhouettes, cinematic lighting, and carefully staged depth"
    ),
}

# Shared fallback for unversioned projects. Active channel profiles also set
# chibi-2d explicitly; saved episode styles remain respected when continuing work.
DEFAULT_ANIMATION_STYLE = "chibi-2d"

CHIBI_FRAME_GUARD = (
    "SHARED CHIBI FRAME FINISH: original hand-drawn 2D educational illustration, bold "
    "clean dark outlines, warm luminous colors, gentle painterly texture, restrained cel "
    "shading, clear foreground-to-background separation and forms readable at phone size. "
    "When people belong in the frame, use friendly compact Chibi proportions, rounded "
    "oversized heads, simple cartoon eyes and mouth, expressive brows, and a warm natural "
    "expression suited to the action. Keep objects and settings in the same illustrated "
    "world; detail follows the scene's explanatory purpose. "
    "NEGATIVE STYLE: no photorealism, no 3D rendering, no realistic anatomy, no thin "
    "fashion-anime proportions, no stick figures, no inconsistent character proportions, "
    "no plastic 3D finish, no excessive gradients, no random style changes, and no "
    "Vox-style motion graphics."
)

CHIBI_MOTION_GUARD = (
    "Keep the same compact Chibi body and oversized head throughout the motion. Preserve "
    "the character's face, outfit, colors, and silhouette; do not stretch, shrink, or morph "
    "the head or body."
)

HISTORICAL_CONTEXT_GUARD = (
    "For any historical scene, follow the researched place and period for clothing, "
    "architecture, tools, transport, symbols, and landscape. Do not default to Chinese "
    "historical motifs unless the episode is about that context. Do not invent archival "
    "documents, quotations, insignia, or source artifacts; avoid graphic depictions of war. "
    "If a visual detail is uncertain, keep it restrained rather than presenting it as evidence."
)

SCENARIO_CONTEXT_GUARD = (
    "For scientific or environmental scenes, preserve the researched spatial and time scale. "
    "Preserve documented events, processes and reconstruction boundaries. Only if an explicitly "
    "authored hypothetical scenario is present, separate its baseline, divergence and conditional aftermath; "
    "do not depict a scenario assumption or inferred outcome as an observed fact or a certain forecast. "
    "Keep any authored branch, resource constraints and uncertainty consistent across scenes. "
    "Do not introduce a mission, intervention or alternate timeline into a documentary scene."
)


def compose_scenario_context(beat, shot):
    """Carry authored layer/branch notes into images without imposing a story shape."""
    context = shot.get("scenario_context") or beat.get("scenario_context")
    if not context:
        return ""
    if isinstance(context, str):
        return f"SCENARIO CONTEXT: {context.strip()}"
    if not isinstance(context, dict):
        raise SystemExit("scenario_context must be an object or a descriptive string.")
    notes = "; ".join(f"{key}: {context[key]}" for key in
                      ("layer", "branch", "basis", "uncertainty") if context.get(key))
    return f"SCENARIO CONTEXT: {notes}" if notes else ""


def visible_character_ids(shot):
    raw = shot.get("characters") or []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        raise SystemExit("characters must be a list of visible character IDs or one ID.")
    return {str(value) for value in raw}


def resolve_people_policy(shot):
    """Separate recurring cast from optional anonymous scene inhabitants.

    Existing shots retain their explicit characters/empty-cast behavior. New
    contextual scenes can contain authored crowds without forcing the protagonist.
    """
    ids = visible_character_ids(shot)
    policy = shot.get("people_policy") or ("listed" if ids else "none")
    if policy not in {"none", "listed", "contextual"}:
        raise SystemExit("people_policy must be none, listed or contextual.")
    if policy == "none" and ids:
        raise SystemExit("people_policy: none conflicts with visible character IDs.")
    if policy == "listed" and not ids:
        raise SystemExit("people_policy: listed needs visible character IDs.")
    return policy


def _people_prompt(policy):
    if policy == "none":
        return (
            "PEOPLE: No people, human faces, human figures or human silhouettes appear. "
            "The authored environment, object, mechanism, geography or ecosystem is the subject. "
            "Plants and animals may appear when the scene calls for them; do not anthropomorphize them."
        )
    if policy == "contextual":
        return (
            "PEOPLE: Include only the named cast and anonymous inhabitants explicitly described "
            "in this scene, at its intended scale. Do not insert the protagonist or a presenter "
            "as decoration. Keep the primary subject and visual explanation dominant."
        )
    return (
        "PEOPLE: Show only the recurring character IDs listed for this shot. "
        "Keep their authored scale, pose, action and identity; do not insert other cast or a presenter."
    )


def compose_visual_intent(shot):
    """Carry editorial decisions without a fixed visual type or scene template."""
    intent = shot.get("visual_intent")
    if not intent:
        return ""
    if isinstance(intent, str):
        return f"VISUAL INTENT: {intent.strip()}"
    if not isinstance(intent, dict):
        raise SystemExit("visual_intent must be an object or a descriptive string.")
    notes = "; ".join(f"{key}: {value}" for key, value in intent.items()
                      if value not in (None, "", [], {}))
    return f"VISUAL INTENT: {notes}" if notes else ""


def _bible_text(bible, visible_ids=()):
    if isinstance(bible, str):
        return bible.strip()
    if not isinstance(bible, dict):
        return ""
    lines = []
    for key in (
        "style",
        "palette",
        "world",
        "narrator_direction",
        "film_language",
        "characters",
        "recurring_props",
        "continuity_rules",
        "scenario_layers",
        "linework",
        "color_logic",
        "environment_design",
        "scale_rules",
        "visual_language",
    ):
        value = bible.get(key)
        if key == "characters":
            value = [item for item in (value or []) if isinstance(item, dict)
                     and str(item.get("id")) in set(visible_ids)]
        if value in (None, "", [], {}):
            continue
        label = key.replace("_", " ").capitalize()
        if isinstance(value, list):
            value = "; ".join(
                ", ".join(
                    f"{k}: {v}" for k, v in item.items()
                    if not (key == "characters" and k in {"reference_image", "reference_images"})
                ) if isinstance(item, dict) else str(item)
                for item in value
            )
        elif isinstance(value, dict):
            value = "; ".join(f"{k}: {v}" for k, v in value.items())
        lines.append(f"{label}: {value}")
    return "\n".join(lines)


def _animation(shot):
    value = shot.get("animation")
    return value if isinstance(value, dict) else {}


def _sentence(value, fallback=""):
    text = str(value or fallback).strip().rstrip(" .!?;")
    return f"{text}." if text else ""


def compose_animation_frame_prompt(doc, beat, shot):
    """Describe one documentary still or a frame in the saved legacy style."""
    # The channel's Chibi visual world also governs diagram-led scenes; visual
    # source changes the composition, not the shared medium.
    style_name = episode_style(doc)
    style = ANIMATION_STYLES.get(style_name, style_name)
    character_ids = visible_character_ids(shot)
    people_policy = resolve_people_policy(shot)
    bible_data = doc.get("visual_bible") or {}
    character_entries = bible_data.get("characters", []) if isinstance(bible_data, dict) else []
    selected_characters = [
        item for item in character_entries
        if isinstance(item, dict) and str(item.get("id")) in character_ids
    ]
    bible = _bible_text(doc.get("visual_bible"), character_ids)
    animation = _animation(shot)
    scene = (shot.get("scene") or "").strip()
    frame_moment = (animation.get("keyframe") or animation.get("start") or scene).strip()
    if "visual_state" in shot:
        state = json.dumps(shot["visual_state"], ensure_ascii=False, sort_keys=True)
        frame_moment += " Required visible state: " + state
    palette = (beat.get("bg") or "").strip()
    continuity = (animation.get("continuity") or "").strip()
    framing = (animation.get("framing") or shot.get("framing") or "").strip()

    parts = [
        f"Create one documentary still in this visual style: {style}." if style_name.startswith("documentary-") else
        f"Create one clean keyframe from an original animated explainer in this visual style: {style}.",
        f"SCENE: {_sentence(scene, 'Show the main idea of this beat as a clear, memorable animated scene')}",
    ]
    parts.append(
        f"FRAME MOMENT: {_sentence(frame_moment, 'Match the opening visual state described in the scene')} "
        "Depict the authored state or causal relationship. Do not turn an action sequence into "
        "a multi-moment storyboard. An explicitly authored comparison, map or cutaway can use "
        "the explanatory layout it needs; it is one designed frame."
    )
    intent = compose_visual_intent(shot)
    if intent:
        parts.append(intent)
    if (shot.get("visual_source") or {}).get("decision") == "diagram":
        parts.append(
            "DIAGRAM-LED COMPOSITION: Explain the researched relationship with a clean, "
            "accurate map, cross-section, flow or comparison in the same hand-drawn Chibi "
            "2D illustrated finish. Keep labels exact and sparse; no realistic photo treatment."
        )
    if framing:
        parts.append(f"CINEMATIC FRAMING: {_sentence(f'Compose this shot as {framing}')}")
    if continuity:
        parts.append(f"CONTINUITY: {_sentence(continuity)}")
    if bible:
        parts.append(f"VISUAL BIBLE — keep these designs and rules consistent across shots:\n{bible}")
    if selected_characters:
        names = ", ".join(
            str(item.get("display_name") or item.get("id"))
            for item in selected_characters
        )
        parts.append(
            f"CHARACTER REFERENCE: Use the attached approved reference image(s) only as identity guides for {names}. "
            "Preserve face, hair, silhouette, proportions, outfit, colors, and props only for "
            "the cast visible here. Do not reproduce the reference-sheet grid or force its "
            "pose, size or composition onto this scene."
        )
    if palette:
        parts.append(f"COLOR DIRECTION: {_sentence(palette)}")
    if style_name == "chibi-2d":
        parts.append(CHIBI_FRAME_GUARD)
    parts.append(HISTORICAL_CONTEXT_GUARD)
    parts.append(SCENARIO_CONTEXT_GUARD)
    scenario = compose_scenario_context(beat, shot)
    if scenario:
        parts.append(scenario)
    parts.extend([
        "The film uses an off-screen voice-over narrator. Do not add a presenter or narrator character unless the scene explicitly names one.",
        "Choose visual hierarchy, viewpoint, distance, detail density and negative space for "
        "the authored subject and scene purpose. A landscape, map, natural process, built "
        "system or changed world may fill the frame without people. Do not illustrate each "
        "narration sentence literally or substitute a reacting character for the mechanism.",
        "Keep the selected medium, color logic, geography, object identity and branch state coherent "
        "with neighboring scenes. Character identity is conditional on presence and does "
        "not lock viewpoint, framing or composition. Use original designs; do not imitate "
        "a named studio, film, publisher or artist.",
        "No paper collage, torn edges, scrapbook layers, magazine clippings, halftone print, title card, captions, logos, watermarks, borders, or UI.",
        f"Aspect ratio {doc.get('aspect', '16:9')}.",
    ])
    if style_name == REALISTIC_STYLE:
        parts.append("Use natural anatomy and credible optics. Avoid Chibi proportions, cartoon outlines, cel shading, fabricated archival stamps or an exaggerated disaster state. Match uncertain details conservatively to the research notes. Do not add visible AI/illustration disclosure labels; keep factual role and provenance in internal records.")
    parts.append(_people_prompt(people_policy))
    channel = doc.get("channel") if isinstance(doc.get("channel"), dict) else {}
    text_direction = str(channel.get("visual_text_direction") or "").strip()
    if text_direction:
        parts.append(f"CHANNEL-SPECIFIC IN-IMAGE TEXT GUIDANCE: {text_direction}")
    parts.append(compose_in_scene_text_prompt(doc, shot))
    return "\n\n".join(parts)


def compose_animation_motion_prompt(doc, beat, shot):
    """Describe a text-to-video Chibi scene with one continuous, causal action."""
    style_name = episode_style(doc)
    style = ANIMATION_STYLES.get(style_name, style_name)
    animation = _animation(shot)
    start = animation.get("start") or "Begin with the subject, state or relationship clearly legible."
    action = animation.get("action") or shot.get("element_motion") or "Use the authored process, reveal or calm hold that explains the scene's idea."
    end = animation.get("end") or "Settle on the intended state or explanatory relationship for the next scene."
    camera = animation.get("camera") or shot.get("camera_move") or "locked-off static camera"
    continuity = animation.get("continuity") or ""
    framing = (animation.get("framing") or shot.get("framing") or "").strip()
    mood = beat.get("feel") or "warm, clear, and story-led"
    palette = beat.get("bg") or "the established palette in the visual bible"
    scene = (shot.get("scene") or beat.get("scene") or "").strip()
    bible_data = doc.get("visual_bible") or {}
    character_entries = bible_data.get("characters", []) if isinstance(bible_data, dict) else []
    character_ids = visible_character_ids(shot)
    people_policy = resolve_people_policy(shot)
    selected_characters = [
        item for item in character_entries
        if isinstance(item, dict) and str(item.get("id")) in character_ids
    ]
    bible = _bible_text(doc.get("visual_bible"), character_ids)

    parts = [
        f"Create one original animated scene from text in this visual style: {style}. "
        "Design the scene and generate its motion as one continuous video shot; there is no supplied scene frame.",
        f"SCENE: {_sentence(scene, 'Create a scene consistent with the researched baseline or specified hypothetical branch that supports the narration')}",
        f"START: {_sentence(start)}",
        f"MAIN ACTION: {_sentence(action)}",
        f"PAYOFF: {_sentence(end)}",
        f"CAMERA: {_sentence(camera)} Follow this instruction exactly; do not add another camera move or drift without purpose.",
        f"TONE AND COLOR: {_sentence(f'{mood}; {palette}')}",
        "Prioritize the authored process, action or readable hold. If it has multiple causal steps, show them in order and leave time for the payoff to read; add at most subtle secondary motion that supports the narration. Show cause before consequence. Let the motion settle on the payoff; no looping, reset, internal edit, or unrelated movement.",
        "The film uses an off-screen voice-over narrator. Do not add a presenter, narrator character, or speaking mouth movement.",
        "Keep the selected visual medium consistent and preserve object identity, geography, visual "
        "hierarchy and scientific scale. Motion may be a natural process, a flow, an "
        "environmental change or a calm hold, not necessarily character acting. "
        "Do not invent extra subjects, subtitles, logos or collage textures.",
    ]
    intent = compose_visual_intent(shot)
    if intent:
        parts.append(intent)
    parts.append(_people_prompt(people_policy))
    if selected_characters:
        names = ", ".join(
            str(item.get("display_name") or item.get("id"))
            for item in selected_characters
        )
        parts.insert(1, (
            f"CHARACTER REFERENCES: Attach and use the approved character reference image(s) for {names} "
            "as identity references only. Preserve each character's face, silhouette, proportions, "
            "hair, clothing, colors, and props; do not copy the reference-sheet layout into the scene."
        ))
    if framing:
        parts.insert(5, f"FRAMING: {_sentence(framing)} Keep the authored subject or relationship readable during the move.")
    if style_name == "chibi-2d" and people_policy != "none":
        parts.append(CHIBI_MOTION_GUARD)
    parts.append(compose_in_scene_text_prompt(doc, shot))
    parts.append(HISTORICAL_CONTEXT_GUARD)
    parts.append(SCENARIO_CONTEXT_GUARD)
    scenario = compose_scenario_context(beat, shot)
    if scenario:
        parts.append(scenario)
    if continuity:
        parts.append(f"SHOT CONTINUITY: {_sentence(continuity)}")
    if bible:
        parts.append(f"VISUAL BIBLE:\n{bible}")
    sound = animation.get("audio") or shot.get("audio_prompt")
    if sound:
        parts.append(
            f"AUDIO: {sound}. No spoken dialogue, narrator, or music; the approved voice-over is added in the edit."
        )
    else:
        parts.append(
            "AUDIO: Keep the clip silent. Do not generate speech, narration, or music; the approved voice-over is added in the edit."
        )
    return "\n\n".join(parts)
