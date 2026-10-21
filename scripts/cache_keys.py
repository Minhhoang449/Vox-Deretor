"""Small helpers for stable, content-aware production cache keys."""
import hashlib
import json
import os


def stable_hash(value):
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_fingerprint(path, include_content=False):
    """Describe a file for cache invalidation; optionally include its SHA-256."""
    absolute = os.path.abspath(os.fspath(path)) if path else ""
    result = {"path": absolute, "exists": bool(absolute and os.path.isfile(absolute))}
    if not result["exists"]:
        return result

    stat = os.stat(absolute)
    result.update({"size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    if include_content:
        digest = hashlib.sha256()
        with open(absolute, "rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        result["sha256"] = digest.hexdigest()
    return result
