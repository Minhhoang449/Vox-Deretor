"""Local topic decision history. Immutable events; never production approvals.

  python scripts/topic_memory.py list --channel battlefield-bearings
  python scripts/topic_memory.py list --query laundry
  python scripts/topic_memory.py show --channel battlefield-bearings --candidate pompeii-laundry
  python scripts/topic_memory.py record path/to/decision.json
"""
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
DISPOSITIONS = {"research_next", "ready_for_drafting", "defer", "reject", "selected_for_development"}
FIELDS = {"event_type", "channel_id", "candidate_id", "question", "reason", "evidence_refs",
          "disposition", "decision_source", "decision_reference", "source_date", "comparison_packet", "outcome"}


def load_config():
    return json.loads((ROOT / "config/channels.json").read_text(encoding="utf-8-sig"))


def memory_root(config=None):
    config = config if config is not None else load_config()
    relative = config.get("topic_discovery", {}).get("decision_memory", {}).get("root", "research/topic-memory")
    result = (ROOT / relative).resolve()
    if not result.is_relative_to(ROOT.resolve()):
        raise ValueError("Topic memory must stay inside the repository.")
    return result


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string.")
    return value.strip()


def _texts(value, field, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{field} must be a list" + (" with evidence." if nonempty else "."))
    return [_text(item, field) for item in value]


def validate_payload(payload, config=None):
    if not isinstance(payload, dict):
        raise ValueError("Record must be a JSON object.")
    if set(payload) - FIELDS:
        raise ValueError("Unknown record fields: " + ", ".join(sorted(set(payload) - FIELDS)))
    data = dict(payload)
    config = config if config is not None else load_config()
    active = {p["id"] for p in config["channels"] if p.get("profile_status") != "archived"}
    for field in ("channel_id", "candidate_id", "question", "reason", "decision_source"):
        data[field] = _text(data.get(field), field)
    for field in ("channel_id", "candidate_id"):
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", data[field]):
            raise ValueError(f"Invalid {field}.")
    if data["channel_id"] not in active:
        raise ValueError("New memory records require an active channel ID.")
    if data["decision_source"] not in {"agent", "user", "documented_history"}:
        raise ValueError("decision_source must be agent, user or documented_history.")
    data["event_type"] = data.get("event_type", "decision")
    data["evidence_refs"] = _texts(data.get("evidence_refs", []), "evidence_refs")
    for field in ("source_date", "comparison_packet", "decision_reference"):
        if field in data:
            data[field] = _text(data[field], field)
    if "source_date" in data:
        date.fromisoformat(data["source_date"])
    if data["event_type"] == "decision":
        data["disposition"] = _text(data.get("disposition"), "disposition")
        if data["disposition"] not in DISPOSITIONS:
            raise ValueError("Invalid topic disposition.")
        if "outcome" in data:
            raise ValueError("Observed outcomes belong in a separate outcome event.")
        if data["disposition"] == "selected_for_development":
            _text(data.get("decision_reference"), "decision_reference")
    elif data["event_type"] == "outcome":
        if "disposition" in data:
            raise ValueError("Outcome events do not overwrite the topic selection decision.")
        outcome = data.get("outcome")
        if not isinstance(outcome, dict):
            raise ValueError("An outcome object is required.")
        if set(outcome) - {"source", "period", "published_version", "video_url", "observations", "hypotheses"}:
            raise ValueError("Unknown outcome fields; separate observations from hypotheses.")
        for field in ("source", "period", "published_version", "video_url"):
            _text(outcome.get(field), "outcome." + field)
        url = urlparse(outcome["video_url"])
        if url.scheme != "https" or url.hostname not in {"youtube.com", "www.youtube.com", "youtu.be"} or not url.path.strip("/"):
            raise ValueError("Outcome video_url must identify a YouTube video over HTTPS.")
        _texts(outcome.get("observations"), "outcome.observations", nonempty=True)
        _texts(outcome.get("hypotheses", []), "outcome.hypotheses")
        if not data["evidence_refs"]:
            raise ValueError("An outcome needs a traceable evidence reference.")
    else:
        raise ValueError("event_type must be decision or outcome.")
    return data


def record_event(payload, root=None, config=None):
    """Create a new event exclusively; leave previous decisions and files intact."""
    data = validate_payload(payload, config)
    root = Path(root).resolve() if root is not None else memory_root(config)
    folder = (root / data["channel_id"]).resolve()
    if not folder.is_relative_to(root):
        raise ValueError("Memory path escapes its root.")
    record = {"schema_version": 1, "event_id": uuid4().hex,
              "recorded_at_utc": datetime.now(timezone.utc).isoformat(), **data}
    serialized = json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (record["event_id"] + ".json")
    with target.open("x", encoding="utf-8") as handle:
        handle.write(serialized)
    return {"path": str(target), "event": record}


def history(channel=None, candidate=None, query=None, root=None, config=None):
    """Read provenance, not instructions; a missing memory directory is empty."""
    root = Path(root) if root is not None else memory_root(config)
    events = []
    for path in sorted(root.glob("*/*.json")):
        try:
            event = json.loads(path.read_text(encoding="utf-8"))
            if event["schema_version"] != 1 or event["channel_id"] != path.parent.name:
                raise ValueError("Inconsistent schema/channel")
            if channel and event["channel_id"] != channel:
                continue
            if candidate and event["candidate_id"] != candidate:
                continue
            haystack = " ".join(str(event.get(k, "")) for k in ("candidate_id", "question", "reason"))
            if query and query.casefold() not in haystack.casefold():
                continue
            events.append(event)
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError(f"Unreadable topic history at {path}: {exc}") from exc
    return sorted(events, key=lambda e: (e["recorded_at_utc"], e["event_id"]))


def summaries(channel=None, query=None, limit=None, root=None, config=None):
    candidates = {}
    events = history(channel=channel, root=root, config=config)
    matched = {(e["channel_id"], e["candidate_id"]) for e in events if not query or query.casefold() in
               " ".join(str(e.get(k, "")) for k in ("candidate_id", "question", "reason")).casefold()}
    for event in events:
        key = (event["channel_id"], event["candidate_id"])
        if key not in matched:
            continue
        item = candidates.setdefault(key, {"channel_id": key[0], "candidate_id": key[1], "latest_disposition": None, "outcome_count": 0})
        item.update(question=event["question"], last_recorded_at_utc=event["recorded_at_utc"])
        if event["event_type"] == "decision":
            item.update(latest_disposition=event["disposition"], reason=event["reason"],
                        decision_source=event["decision_source"], evidence_refs=event["evidence_refs"])
        else:
            item["outcome_count"] += 1
    result = sorted(candidates.values(), key=lambda x: x["last_recorded_at_utc"], reverse=True)
    return result if limit is None else result[:limit]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list")
    listing.add_argument("--channel")
    listing.add_argument("--query")
    showing = commands.add_parser("show")
    showing.add_argument("--channel", required=True)
    showing.add_argument("--candidate", required=True)
    recording = commands.add_parser("record")
    recording.add_argument("input", help="JSON decision or observed outcome; no production approval fields.")
    args = parser.parse_args()
    try:
        if args.command == "record":
            result = record_event(json.loads(Path(args.input).read_text(encoding="utf-8-sig")))
        elif args.command == "show":
            result = history(channel=args.channel, candidate=args.candidate)
        else:
            result = summaries(channel=args.channel, query=args.query)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
