"""Record an actual narration approval, then detect changes before TTS/render.

Recording is an editorial action: an agent may run it only AFTER the user has
approved the specified speech. A status flag, review score or this CLI is not
evidence that approval occurred. Existing unrecorded episodes remain resumable.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

FILENAME = "narration-approval.json"


def normalize(text):
    # Preserve punctuation, case and spelling: only layout whitespace may vary.
    return " ".join(text.split())


def digest(text):
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def beat_speech(doc):
    return normalize(" ".join(beat.get("narration") or "" for beat in doc.get("beats", [])))


def language(doc):
    return ((doc.get("voice") or {}).get("language")
            or (doc.get("channel") or {}).get("language") or doc.get("language"))


def read_source(path, section=None):
    text = Path(path).read_text(encoding="utf-8-sig")
    if section:
        lines = text.splitlines()
        matches = [(i, len(m.group(1))) for i, line in enumerate(lines)
                   if (m := re.match(r"^(#{1,6})\s+(.+?)\s*$", line))
                   and m.group(2) == section]
        if len(matches) != 1:
            raise ValueError("Speech section must occur exactly once: " + section)
        start, level = matches[0]
        end = next((i for i in range(start+1, len(lines))
                    if (m := re.match(r"^(#{1,6})\s+", lines[i]))
                    and len(m.group(1)) <= level), len(lines))
        text = "\n".join(lines[start+1:end])
    # Do not silently approve headings, source notes or an entire mixed document.
    if re.search(r"(?m)^#{1,6}\s", text):
        raise ValueError("Use --section for Markdown, or supply speech-only text.")
    if not normalize(text):
        raise ValueError("Approved speech cannot be empty.")
    return text


def load_doc(project_dir):
    return json.loads((Path(project_dir)/"beats.json").read_text(encoding="utf-8-sig"))


def record(project_dir, source, approval_note, section=None, replace=False):
    project = Path(project_dir).resolve()
    doc = load_doc(project)
    if not doc.get("channel_id") or not language(doc):
        raise ValueError("Bind one channel and language before recording approval.")
    if not approval_note.strip():
        raise ValueError("Record the actual user approval reference, not a self-review score.")
    source = Path(source).resolve()
    text = read_source(source, section)
    current = beat_speech(doc)
    if current and digest(current) != digest(text):
        raise ValueError("Beats differ from the specified speech. Stage the approved revision before recording it.")
    path = project/FILENAME
    if path.exists() and not replace:
        raise ValueError("Approval already recorded. --replace requires a new actual user approval.")
    manifest = {
        "schema_version": 1, "channel_id": doc["channel_id"], "language": language(doc),
        "episode_slug": doc.get("episode_slug") or doc.get("project") or project.name,
        "speech_sha256": digest(text), "approval_note": approval_note.strip(),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source": {"path": str(source), "section": section},
    }
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    temporary.replace(path)
    return manifest


def inspect(project_dir, doc=None):
    project = Path(project_dir).resolve()
    doc = load_doc(project) if doc is None else doc
    result = {"status": "legacy_unrecorded", "errors": [], "speech_sha256": digest(beat_speech(doc))}
    path = project/FILENAME
    if not path.exists():
        if doc.get("narration_approval_required"):
            result.update(status="blocked", errors=["Narration approval has not been recorded."])
        return result
    try:
        manifest = json.loads(path.read_text(encoding="utf-8-sig"))
        if manifest.get("schema_version") != 1 or not manifest.get("approval_note", "").strip():
            raise ValueError("Invalid approval record.")
        identity = (doc.get("channel_id"), language(doc),
                    doc.get("episode_slug") or doc.get("project") or project.name)
        if identity != (manifest.get("channel_id"), manifest.get("language"), manifest.get("episode_slug")):
            raise ValueError("Approval belongs to another channel, language or episode.")
        source = manifest["source"]
        if digest(read_source(source["path"], source.get("section"))) != manifest["speech_sha256"]:
            raise ValueError("The approved speech source has changed.")
        if not beat_speech(doc):
            raise ValueError("No beat narration is available to compare with approved speech.")
        if result["speech_sha256"] != manifest["speech_sha256"]:
            raise ValueError("Beat narration differs from the approved speech.")
        result["status"] = "matched"
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result.update(status="blocked", errors=[str(exc)])
    return result


def assert_approved(project_dir, doc=None):
    result = inspect(project_dir, doc)
    if result["status"] == "blocked":
        raise SystemExit("Narration version check failed: " + "; ".join(result["errors"]))
    if result["status"] == "legacy_unrecorded":
        print("[narration] Legacy approval is not machine-recorded; consult the brief/handoff and user approval.")
    return result


def inspect_audio(project_dir, doc):
    """Check speech receipts and file integrity without loading a speech model.

    Older caches lack speech receipts; report that limit instead of certifying
    them from a possibly overwritten narr_*.txt file.
    """
    from cache_keys import file_fingerprint

    project = Path(project_dir).resolve()
    result = {"errors": [], "warnings": [], "beats": []}
    strict = bool(doc.get("narration_approval_required") or (project/FILENAME).exists())
    for beat in doc.get("beats", []):
        if not normalize(beat.get("narration") or ""):
            continue
        identifier = str(beat.get("id", ""))
        path = Path(beat.get("narration_audio") or "")
        path = path if path.is_absolute() else project/path
        row = {"beat_id": identifier, "audio": str(path), "status": "unverified"}
        try:
            if not path.is_file():
                raise ValueError("Narration audio is missing.")
            cache_path = project/"audio"/f"narr_{identifier}.cache.json"
            cache = json.loads(cache_path.read_text(encoding="utf-8-sig")) if cache_path.is_file() else {}
            receipt = cache.get("narration_sha256")
            if receipt and receipt != digest(beat["narration"]):
                raise ValueError("WAV speech receipt differs from current beat narration.")
            if cache.get("audio_file") and cache["audio_file"] != file_fingerprint(str(path)):
                raise ValueError("Narration audio no longer matches its cache file record.")
            if cache.get("audio_sha256") and cache["audio_sha256"] != file_fingerprint(str(path), True).get("sha256"):
                raise ValueError("Narration audio content has changed.")
            if not receipt or not cache.get("audio_sha256"):
                if strict:
                    raise ValueError("Speech receipt missing. Run the TTS runner to verify/reuse the matching cache; do not force --redo.")
                result["warnings"].append(f"{identifier}: legacy audio lacks a complete speech receipt.")
            else:
                row["status"] = "matched"
        except (OSError, ValueError, TypeError, KeyError) as exc:
            row.update(status="blocked", error=str(exc))
            result["errors"].append(f"{identifier}: {exc}")
        result["beats"].append(row)
    return result


def assert_audio(project_dir, doc):
    result = inspect_audio(project_dir, doc)
    if result["errors"]:
        raise SystemExit("Narration audio check failed: " + "; ".join(result["errors"][:4]))
    if result["warnings"]:
        print(f"[narration] {len(result['warnings'])} legacy WAV(s) lack complete speech receipts; not certified against approved text.")
    return result


def main():
    from local_guard import configure_console
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("project_dir")
    capture = sub.add_parser("record", help="Only after actual user approval of this version")
    capture.add_argument("project_dir")
    capture.add_argument("--source", required=True)
    capture.add_argument("--section", help="Exact Markdown heading containing ONLY speech")
    capture.add_argument("--approval-note", required=True, help="Actual user approval reference")
    capture.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.command == "record":
        result = record(args.project_dir, args.source, args.approval_note, args.section, args.replace)
    else:
        result = inspect(args.project_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("status") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
