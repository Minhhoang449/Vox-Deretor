"""Mandatory research-gap step when a draft is shorter than its target length.

Usage:
  python scripts/research_gaps.py --draft <script.md> --packaging <beats.json> [--scan <youtube-market-scan.json>]
  python scripts/research_gaps.py --draft <script.md> --target-minutes 16 --scan <scan.json>

Writes <draft-stem>-research-gaps.json/.md next to the draft (or --out-dir). An existing
checklist JSON is reloaded so filled items keep their status. Exit code 2 while the draft is
under 85% of target and any item is still open; 0 when there is no gap or every item is closed.

Never pad. Close an item as "sourced" with a real citation, or as "sources_exhausted" with
what was searched; when sources are exhausted, accept the shorter length.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from draft_review_checks import review  # noqa: E402  (narration-only runtime estimate, 150 wpm)

GAP_RATIO = 0.85
MINUTES_PER_ITEM = 1.5
CLOSED = {"sourced", "sources_exhausted"}
RULE = ("Never pad. Fill the gap only with sourced material that advances the episode question. "
        "If sources are exhausted, record 'sources exhausted' with what was searched and accept the shorter length.")


def target_from_packaging(doc):
    if not isinstance(doc, dict):
        return None
    for holder in (doc.get("youtube_metadata") or {}, doc):
        t = holder.get("target_length")
        if isinstance(t, dict) and isinstance(t.get("target_minutes"), (int, float)):
            return float(t["target_minutes"])
        if isinstance(holder.get("target_minutes"), (int, float)):
            return float(holder["target_minutes"])
    return None


def models_from_scan(scan, n=3):
    if not isinstance(scan, dict):
        return []
    out = []
    for m in (scan.get("top_models") or [])[:n]:
        out.append({"title": m.get("title", ""), "url": m.get("url", ""),
                    "channel": m.get("channel_title", ""),
                    "length_minutes": round(m["duration_seconds"] / 60, 1)
                    if isinstance(m.get("duration_seconds"), int) and m["duration_seconds"] else None})
    return out


def build_items(gap_minutes, models):
    count = max(3, math.ceil(gap_minutes / MINUTES_PER_ITEM))
    hints = [m["title"] for m in models if m.get("title")]
    items = []
    for i in range(count):
        hint = hints[i % len(hints)] if hints else ""
        items.append({
            "id": f"Q{i + 1}",
            "status": "open",
            "question": "[FILL] A source question for a passage this draft lacks, answering the episode question"
                        + (f" (subtopic hint from model title: \"{hint}\")" if hint else ""),
            "passage": "[FILL] which passage it would serve",
            "source": "",
            "searched": [],
            "note": "",
        })
    return items


def item_closed(item):
    status = item.get("status")
    if status == "sourced":
        return bool(str(item.get("source", "")).strip()) and "[FILL]" not in item.get("question", "")
    if status == "sources_exhausted":
        return bool(item.get("searched"))
    return False


def evaluate(draft_text, target, models, previous=None):
    measured = review(draft_text)["estimated_minutes"] or 0.0
    threshold = round(target * GAP_RATIO, 1)
    gap = measured < threshold
    result = {"draft_minutes": measured, "target_minutes": target, "threshold_minutes": threshold,
              "gap": gap, "minutes_to_fill": round(max(target - measured, 0), 1) if gap else 0.0,
              "models": models, "rule": RULE, "items": []}
    if gap:
        items = (previous or {}).get("items") or build_items(result["minutes_to_fill"], models)
        result["items"] = items
    open_items = [i["id"] for i in result["items"] if not item_closed(i)]
    result["open_items"] = open_items
    result["status"] = "open" if gap and open_items else ("no_gap" if not gap else "closed")
    return result


def render(result, draft_path):
    lines = ["# Research gaps", "", f"Draft: `{draft_path}`",
             f"Measured narration: {result['draft_minutes']} min · target {result['target_minutes']} min · "
             f"gap threshold {result['threshold_minutes']} min (85%).", ""]
    if not result["gap"]:
        lines += ["No gap: the draft is at least 85% of target.", ""]
        return "\n".join(lines)
    lines += [f"**Status: {result['status']}.** Minutes to fill: {result['minutes_to_fill']}.", "",
              f"> {result['rule']}", "", "## Model videos (subtopic hints from titles only, not facts)", ""]
    for m in result["models"] or []:
        length = f"{m['length_minutes']} min" if m.get("length_minutes") else "length unavailable"
        lines.append(f"- [{m['title']}]({m['url']}) · {m['channel']} · {length}")
    if not result["models"]:
        lines.append("- None available (pass --scan).")
    lines += ["", "## Source questions to research", "",
              "Fill each item in the JSON: `sourced` needs a real citation in `source`; "
              "`sources_exhausted` needs the list of what was searched in `searched`.", "",
              "| ID | Status | Question | Passage | Source / searched |", "|---|---|---|---|---|"]
    for i in result["items"]:
        src = i.get("source") or "; ".join(i.get("searched") or []) or "—"
        lines.append(f"| {i['id']} | {i['status']} | {i['question']} | {i['passage']} | {src} |")
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--draft", required=True)
    p.add_argument("--packaging", help="beats.json (youtube_metadata.target_length) or JSON with target_minutes")
    p.add_argument("--scan", help="youtube-market-scan JSON (top_models)")
    p.add_argument("--target-minutes", type=float)
    p.add_argument("--out-dir")
    a = p.parse_args(argv)
    with open(a.draft, encoding="utf-8") as h:
        text = h.read()
    target = a.target_minutes
    if target is None and a.packaging:
        with open(a.packaging, encoding="utf-8") as h:
            target = target_from_packaging(json.load(h))
    if target is None:
        raise SystemExit("No target length: pass --packaging with target_length or --target-minutes.")
    scan = None
    if a.scan:
        with open(a.scan, encoding="utf-8") as h:
            scan = json.load(h)
    out_dir = a.out_dir or os.path.dirname(os.path.abspath(a.draft))
    stem = os.path.splitext(os.path.basename(a.draft))[0]
    json_path = os.path.join(out_dir, f"{stem}-research-gaps.json")
    md_path = os.path.join(out_dir, f"{stem}-research-gaps.md")
    previous = None
    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as h:
            previous = json.load(h)
    result = evaluate(text, target, models_from_scan(scan), previous)
    os.makedirs(out_dir, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as h:
        json.dump(result, h, ensure_ascii=False, indent=2)
        h.write("\n")
    with open(md_path, "w", encoding="utf-8") as h:
        h.write(render(result, a.draft))
    print(f"Draft {result['draft_minutes']} min / target {target} min: {result['status']}; "
          f"open items: {len(result['open_items'])}")
    print(f"Checklist: {md_path}\nJSON: {json_path}")
    return 2 if result["status"] == "open" else 0


if __name__ == "__main__":
    sys.exit(main())
