"""Plan Montage retrieval, validate evidence, and reserve imagegen for gaps.

No provider call is made by this helper. Search results and rights checks must
describe actual work, never a successful API call inferred from configuration.
"""
import argparse
from datetime import date
import json
import math
from pathlib import Path

from local_guard import configure_console, refuse_out_dir
from visual_policy import footage_first, is_video_shot


def shot_rows(doc):
    for beat in doc.get("beats") or []:
        for shot in beat.get("shots") or [beat]:
            if shot.get("kind") != "host":
                key = str(beat["id"]) + (str(shot.get("id", "")) if beat.get("shots") else "")
                yield beat, shot, key


def path_in_project(project_dir, value):
    path = Path(value)
    return path if path.is_absolute() else Path(project_dir) / path


def require_fields(record, fields, key):
    for field in fields:
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise SystemExit(f"[{key}] visual_source needs {field}.")


def require_date(value, key):
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        raise SystemExit(f"[{key}] accessed_on must be an actual YYYY-MM-DD access date.")


def validate_source_plan(project_dir, doc):
    """Gate only the new workflow; historical productions retain their rules."""
    if not footage_first(doc):
        return
    rows = list(shot_rows(doc))
    if not rows:
        raise SystemExit("Plan approved narration spans and shots before visual sourcing.")
    keys = [key for _, _, key in rows]
    if len(set(keys)) != len(keys):
        raise SystemExit("Duplicate visual shot keys; use unique beat/shot IDs.")
    for _, shot, key in rows:
        record = shot.get("visual_source") or {}
        decision = record.get("decision")
        if decision not in {"video", "ai_reconstruction", "diagram", "reuse"}:
            raise SystemExit(f"[{key}] finish footage sourcing first: visual_source.decision is unresolved. See references/footage-first.md.")
        require_fields(record, ["reason"], key)
        if decision == "reuse":
            if not shot.get("reuse_image_from"):
                raise SystemExit(f"[{key}] reuse decision needs reuse_image_from.")
            continue
        if decision == "diagram":
            require_fields(record, ["source_url", "accessed_on"], key)
            require_date(record["accessed_on"], key)
            continue
        searches = record.get("searches") or []
        if not isinstance(searches, list) or not searches:
            raise SystemExit(f"[{key}] record actual footage searches before selecting video or generating a reconstruction.")
        for search in searches:
            require_fields(search, ["provider", "query", "query_language", "accessed_on", "outcome"], key)
            require_date(search["accessed_on"], key)
            if search["query_language"] != doc.get("language"):
                require_fields(search, ["cross_language_note"], key)
        if not any(search["query_language"] == doc.get("language") for search in searches):
            raise SystemExit(f"[{key}] record a primary audience-language footage search; cross-language archive queries are supplemental.")
        if decision == "ai_reconstruction":
            require_fields(record, ["source_url", "accessed_on"], key)
            require_date(record["accessed_on"], key)
        if decision == "video":
            require_fields(record, ["source_url", "rights_url", "rights_note", "accessed_on", "verification_note"], key)
            require_date(record["accessed_on"], key)
            if record.get("rights_status") != "verified":
                raise SystemExit(f"[{key}] verify this item's usage rights; provider-level public-domain assumptions are insufficient.")
            if record.get("factual_role") not in {"event_record", "illustrative"}:
                raise SystemExit(f"[{key}] factual_role must be event_record or illustrative.")
            clip = shot.get("clip_path")
            if not clip or not path_in_project(project_dir, clip).is_file():
                raise SystemExit(f"[{key}] download and inspect the selected footage first; clip_path is missing.")
            try:
                offset = float(shot.get("source_in_seconds", 0))
            except (ValueError, TypeError):
                raise SystemExit(f"[{key}] source_in_seconds must be a finite nonnegative number.")
            if not math.isfinite(offset) or offset < 0:
                raise SystemExit(f"[{key}] source_in_seconds must be a finite nonnegative number.")


def export_requests(project_dir, doc):
    lines = [
        "# Montage footage requests", "",
        f"Episode: {doc.get('project', '')} | Channel: {doc.get('channel_id', '')} | Narration language: {doc.get('language', '')}", "",
        "Use Montage from this Vox project as the retrieval tool. Read its live guide and run provider preflight. This request pack does not execute searches.",
        "Find and inspect suitable footage first, including illustrative stock when the passage allows it. Keep the approved narration, topic and runtime. Do not add a sign-off or quiet tail.",
        "Preserve record URLs, access dates, item-level rights and source in/out points. Metadata matching alone does not verify the depicted place, date, event or action.",
        "Use primary audience-language queries first; source-native archive terms may be supplemental and must record their language and reason.",
        "Do not run Montage's script, TTS or image stages. Fill each shot's visual_source with actual results. Return local clips into this episode's footage folder.",
        "Only then create photorealistic reconstruction or sourced explanatory graphics for the remaining gaps. Do not add visible AI/illustration disclosure labels to generated images or video; retain factual role and provenance in internal records.", "",
    ]
    for beat, shot, key in shot_rows(doc):
        lines += [f"## {key}", "", f"Narration: {beat.get('narration', '')}",
                  f"Visual purpose: {shot.get('visual_intent') or shot.get('scene', '')}",
                  f"Planned duration: {shot.get('dur', '?')} seconds", "",
                  "Current source plan:", "```json",
                  json.dumps(shot.get("visual_source") or {}, ensure_ascii=False, indent=2), "```", ""]
    path = Path(project_dir) / "research" / "montage-requests.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main():
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode")
    parser.add_argument("--init", action="store_true", help="Add unresolved source-plan slots; no narration or media changes")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    project_dir = Path(args.episode).resolve()
    refuse_out_dir(str(project_dir))
    path = project_dir / "beats.json"
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not footage_first(doc):
        raise SystemExit("This episode keeps its recorded workflow. Apply a requested visual revision explicitly before using this planner.")
    if args.init:
        for _, shot, _ in shot_rows(doc):
            shot.setdefault("visual_source", {"decision": "pending", "reason": "", "searches": []})
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.check:
        validate_source_plan(project_dir, doc)
        print("Visual source plan passed structural checks. Actual media, rights and factual-fit QA remains required.")
    print(f"Exported Montage retrieval requests (not executed): {export_requests(project_dir, doc)}")


if __name__ == "__main__":
    main()
