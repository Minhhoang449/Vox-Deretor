#!/usr/bin/env python3
"""Collect public YouTube search metadata before an episode is written.

The key is read from YOUTUBE_API_KEY in the repo .env, or from the process
environment if that is already set. The key is never printed or written into
the report.

Discovery scan, using the queries stored on the channel:

  python scripts/research_youtube.py --channel vi-sao-noi-nay

One episode, before the beat map. Write the report inside that episode:

  python scripts/research_youtube.py --channel vi-sao-noi-nay --query "..." --tag <slug> --region-code VN --output-dir "<episode>\\research"

Use --region-code when the episode targets a different country from the channel default.
Use --relevance-language to override the channel language for a deliberate cross-language discovery scan.
For topic-specific scans, a cross-language override also requires --cross-language-note; keep the
channel-language scan as the primary market comparison. Declare the query text language with
--query-language so the scan cannot silently inherit a mismatched channel language.
"""
from __future__ import annotations

import json
import errno
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from local_guard import ROOT, refuse_out_dir


CHANNELS_FILE = os.path.join(ROOT, "config", "channels.json")
API_ROOT = "https://www.googleapis.com/youtube/v3"


def configure_console():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_project_env():
    """Load KEY=VALUE lines from the repo .env. An existing process value wins."""
    env_path = os.path.join(ROOT, ".env")
    try:
        with open(env_path, encoding="utf-8-sig") as handle:
            lines = handle.read().splitlines()
    except FileNotFoundError:
        return
    for line in lines:
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        if entry.startswith("export "):
            entry = entry[len("export "):].lstrip()
        if "=" not in entry:
            continue
        name, value = entry.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or name in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ[name] = value


def _is_refused_sink_proxy(exc):
    """Return true only for a refused loopback discard proxy, not normal proxies."""
    reason = getattr(exc, "reason", None)
    if not isinstance(reason, OSError) or getattr(reason, "errno", None) not in (
        errno.ECONNREFUSED,
        10061,  # WSAECONNREFUSED on Windows
    ):
        return False

    # Some sandboxed environments set HTTP(S)_PROXY to localhost:9 as a
    # network-blocking placeholder. If that socket refuses the request, retry
    # directly. Keep using any functioning or non-placeholder proxy as normal.
    for proxy in urllib.request.getproxies().values():
        parsed = urllib.parse.urlsplit(proxy if "://" in proxy else "//" + proxy)
        if parsed.hostname in {"127.0.0.1", "localhost", "::1"} and parsed.port == 9:
            return True
    return False


def _open_api_request(request, timeout):
    # urllib's proxy handler mutates Request when it routes through a proxy.
    # Keep the original request data so the direct fallback targets Google,
    # rather than reusing a proxy-mutated URL.
    url = request.full_url
    data = request.data
    headers = dict(request.header_items())
    method = request.get_method()
    try:
        return urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.URLError as exc:
        if not _is_refused_sink_proxy(exc):
            raise

    # Bypass only the known dead localhost:9 placeholder. A real proxy is still
    # tried first and remains the normal route when it is available.
    print(
        "YouTube API: localhost:9 placeholder proxy refused the request; retrying directly.",
        file=sys.stderr,
    )
    direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    direct_request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        return direct.open(direct_request, timeout=timeout)
    except urllib.error.HTTPError:
        raise
    except urllib.error.URLError as direct_exc:
        raise RuntimeError(
            "Could not reach the YouTube Data API: the localhost:9 proxy refused "
            "the request and the direct connection also failed. "
            f"{format_network_error(direct_exc)}"
        ) from None


def format_network_error(exc):
    """Describe transport failures without printing request URLs or API keys."""
    reason = getattr(exc, "reason", exc)
    if isinstance(reason, PermissionError):
        return (
            "The operating system denied socket access (PermissionError). "
            "This usually means the current sandbox/runtime blocks outbound network access; "
            "rerun with approved network access."
        )
    if isinstance(reason, socket.gaierror):
        return f"DNS lookup failed for the API host ({reason})."
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "The connection to the API host timed out."
    if isinstance(reason, OSError):
        code = getattr(reason, "errno", None)
        detail = getattr(reason, "strerror", None) or type(reason).__name__
        code_text = f" (errno {code})" if code is not None else ""
        return f"Network connection failed: {type(reason).__name__}: {detail}{code_text}."
    if isinstance(reason, str):
        return f"Network connection failed: {reason}."
    return f"Network connection failed: {type(reason).__name__}."


def api_get(resource, params, api_key):
    query = dict(params)
    query["key"] = api_key
    url = f"{API_ROOT}/{resource}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with _open_api_request(request, timeout=35) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # The request URL contains the key. Do not include it in the error.
        try:
            body = json.loads(exc.read().decode("utf-8", errors="replace"))
            error = body.get("error", {}) if isinstance(body, dict) else {}
            if not isinstance(error, dict):
                error = {}
            message = error.get("message") or ""
            if not isinstance(message, str):
                message = str(message)
            if api_key:
                message = message.replace(api_key, "[redacted]")
            reasons = [
                item.get("reason")
                for item in (error.get("errors") or [])
                if isinstance(item, dict) and item.get("reason")
            ]
        except (ValueError, AttributeError):
            message = ""
            reasons = []
        detail = f"YouTube Data API returned HTTP {exc.code}"
        if reasons:
            detail += f" ({', '.join(dict.fromkeys(reasons))})"
        if message:
            detail += f". {message}"
        raise RuntimeError(detail + ".") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Could not reach the YouTube Data API. " + format_network_error(exc)
        ) from None


def parse_duration(value):
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return 0
    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def age_days(published_at, now):
    published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    return max((now - published).total_seconds() / 86400, 1 / 24)


def normalize_tag(value):
    """Use the same ASCII-safe tag in report filenames and episode gates."""
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value or "").strip("-")


def render_report(report, top_per_query):
    order_label = report["method"]["order"]
    lines = [
        "# YouTube public search scan",
        "",
        f"Scanned at: {report['scanned_at_utc']}",
        f"Search region: {report['method'].get('region_code_override') or 'channel defaults'}",
        "",
        f"> Search order: `{order_label}`. This is a packaging and topic snapshot, not factual evidence. "
        "The API result order is query relevance/order only. Public view counts are a snapshot and do not show "
        "retention, satisfaction, click-through rate, or whether a new channel can reproduce the result. "
        "Region and language filters are search slices, not audience analytics.",
        "",
    ]
    cross_language_note = report["method"].get("cross_language_note")
    if cross_language_note:
        lines.extend([
            f"> Supplemental cross-language scan: {cross_language_note} The primary audience-language scan "
            "must be kept and interpreted separately.",
            "",
        ])
    for channel in report["channels"]:
        lines.extend([
            f"## {channel['display_name']}",
            "",
            f"Language: `{channel['relevance_language']}` · Region: `{channel['region_code'] or 'YouTube default'}`",
            "",
        ])
        for query in channel["queries"]:
            lines.extend([f"### {query['query']}", ""])
            total_estimate = query.get("api_total_results_estimate")
            estimate_note = (
                f"API total-results estimate: {total_estimate:,}"
                if isinstance(total_estimate, int)
                else "API total-results estimate unavailable"
            )
            lines.append(
                f"Returned {query.get('api_returned_results', len(query['results']))} of up to "
                f"{query.get('requested_max_results', len(query['results']))} requested results; "
                f"{estimate_note}; more results available: "
                f"{'yes' if query.get('has_more_results') else 'no'}. "
                "The API total is approximate; only the first page was requested."
            )
            lines.append("")
            rows = query["results"][:top_per_query]
            if not rows:
                lines.extend(["No results returned for this query.", ""])
                continue
            lines.extend([
                "| Search result | Video | Thumbnail | Public views at scan | Published | Length |",
                "|---:|---|---|---:|---|---:|",
            ])
            for result_rank, video in enumerate(rows, start=1):
                result_rank = video.get("search_result_rank", result_rank)
                title = video["title"].replace("|", "\\|").replace("\n", " ")
                channel_name = video["channel_title"].replace("|", "\\|")
                label = f"[{title}]({video['url']}) · {channel_name}"
                thumbnail = f"[open]({video['thumbnail_url']})" if video.get("thumbnail_url") else "—"
                views = video.get("views")
                views_label = f"{views:,}" if isinstance(views, int) else "unavailable"
                duration = video.get("duration_seconds")
                duration_label = f"{duration}s" if isinstance(duration, int) else "unavailable"
                lines.append(
                    f"| {result_rank} | {label} | {thumbnail} | {views_label} | "
                    f"{video['published_at'][:10]} | {duration_label} |"
                )
            lines.append("")
            lines.extend(["#### Description excerpts", ""])
            for video in rows:
                description = " ".join((video.get("description") or "").split())
                if len(description) > 360:
                    description = description[:357].rstrip() + "..."
                description = description.replace("|", "\\|") or "(no description returned)"
                lines.append(f"- **{video['title']}** — {description}")
            lines.append("")
    lines.extend([
        "## How to use this scan",
        "",
        "Compare the question, the opening, the title promise, the thumbnail focus, and what the videos leave out. "
        "Open the thumbnails by hand: the API does not say what the image communicates. "
        "Do not copy scripts, titles, thumbnails, or visual identity. "
        "Verify every important fact with a primary or authoritative source before writing narration. "
        "A high view count can be an old upload, a large existing audience, paid distribution, or a one-off hit.",
        "",
    ])
    return "\n".join(lines)


def parse_args(argv):
    args = {
        "output_dir": os.path.join(ROOT, "references", "research"),
        "max_results": 12,
        "top_per_query": 3,
        "order": "viewCount",
        "channels": [],
        "queries": [],
        "tag": "",
        "api_key_env": "YOUTUBE_API_KEY",
        "region_code": "",
        "relevance_language": "",
        "query_language": "",
        "cross_language_note": "",
    }
    i = 0
    while i < len(argv):
        token = argv[i]
        def need(flag):
            nonlocal i
            if i + 1 >= len(argv):
                raise SystemExit(f"{flag} needs a value")
            i += 1
            return argv[i]
        if token == "--output-dir":
            args["output_dir"] = need(token)
        elif token == "--max-results":
            args["max_results"] = int(need(token))
        elif token == "--top-per-query":
            args["top_per_query"] = int(need(token))
        elif token == "--order":
            args["order"] = need(token)
        elif token == "--channel":
            args["channels"].append(need(token))
        elif token == "--query":
            args["queries"].append(need(token))
        elif token == "--tag":
            args["tag"] = need(token)
        elif token == "--api-key-env":
            args["api_key_env"] = need(token)
        elif token == "--region-code":
            args["region_code"] = need(token).strip().upper()
        elif token == "--relevance-language":
            args["relevance_language"] = need(token).strip().lower()
        elif token == "--query-language":
            args["query_language"] = need(token).strip().lower()
        elif token == "--cross-language-note":
            args["cross_language_note"] = need(token).strip()
        elif token in ("-h", "--help"):
            raise SystemExit(__doc__.strip())
        else:
            raise SystemExit(f"Unknown argument {token}. Run with --help.")
        i += 1
    if args["order"] not in ("relevance", "date", "viewCount"):
        raise SystemExit("--order must be relevance, date, or viewCount.")
    if not 5 <= args["max_results"] <= 50:
        raise SystemExit("--max-results must be between 5 and 50.")
    if args["top_per_query"] < 1:
        raise SystemExit("--top-per-query must be at least 1.")
    if args["region_code"] and (len(args["region_code"]) != 2 or not args["region_code"].isalpha()):
        raise SystemExit("--region-code must be a two-letter country code, such as VN, MX, or ES.")
    if args["relevance_language"] and (
        len(args["relevance_language"]) != 2 or not args["relevance_language"].isalpha()
    ):
        raise SystemExit("--relevance-language must be a two-letter language code, such as en, vi, or ja.")
    if args["query_language"] and (
        len(args["query_language"]) != 2 or not args["query_language"].isalpha()
    ):
        raise SystemExit("--query-language must be a two-letter language code, such as en, vi, or ja.")
    if args["queries"] and len(set(args["channels"])) != 1:
        raise SystemExit("A topic query needs exactly one --channel.")
    if args["queries"] and not args["tag"]:
        raise SystemExit("A topic query also needs --tag so it does not replace another scan.")
    if args["queries"] and not args["query_language"]:
        raise SystemExit("A topic query also needs --query-language matching the query text.")
    if args["queries"] and args["relevance_language"] and args["query_language"] != args["relevance_language"]:
        raise SystemExit("--query-language and --relevance-language must match for a topic-specific scan.")
    if args["cross_language_note"] and not args["relevance_language"]:
        raise SystemExit("--cross-language-note requires an explicit --relevance-language override.")
    return args


def main(argv):
    configure_console()
    args = parse_args(argv)
    load_project_env()
    api_key = os.environ.get(args["api_key_env"], "").strip()
    if not api_key:
        raise SystemExit(
            f"{args['api_key_env']} is not set. Put it in the repo .env as {args['api_key_env']}=... "
            "The file stays out of Git."
        )
    output_dir = os.path.abspath(args["output_dir"])
    refuse_out_dir(output_dir)
    with open(CHANNELS_FILE, encoding="utf-8-sig") as handle:
        config = json.load(handle)
    selected = set(args["channels"])
    channels = config["channels"]
    if selected:
        channels = [channel for channel in channels if channel["id"] in selected]
        if len(channels) != len(selected):
            known = ", ".join(channel["id"] for channel in config["channels"])
            raise SystemExit(f"Unknown channel. Use one of: {known}")
    if args["queries"]:
        channel = next(iter(channels))
        research = channel.get("youtube_research") or {}
        primary_language = research.get("relevance_language", "").lower()
        selected_language = args["query_language"]
        if selected_language != primary_language and not args["cross_language_note"]:
            raise SystemExit(
                f"This topic scan targets {channel['id']} ({primary_language}) but requested "
                f"{selected_language} query text. Keep the primary-language scan and add "
                "--cross-language-note with the supplemental scan's purpose."
            )
    now = datetime.now(timezone.utc)
    report = {
        "scanned_at_utc": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "method": {
            "endpoint": "YouTube Data API v3 search.list and videos.list",
            "order": args["order"],
            "max_results_per_query": args["max_results"],
            "region_code_override": args["region_code"] or None,
            "relevance_language_override": args["relevance_language"] or None,
            "query_language": args["query_language"] or None,
            "cross_language_note": args["cross_language_note"] or None,
            "note": "Search region and language are discovery filters, not channel audience analytics.",
        },
        "channels": [],
    }
    id_to_rows = {}
    for channel in channels:
        research = channel.get("youtube_research")
        if not research:
            continue
        channel_result = {
            "channel_id": channel["id"],
            "display_name": channel["display_name"],
            "relevance_language": args["relevance_language"] or research["relevance_language"],
            "query_language": args["query_language"] or research["relevance_language"],
            "region_code": args["region_code"] or research.get("region_code", ""),
            "queries": [],
        }
        query_texts = args["queries"] or research["queries"]
        for query_text in query_texts:
            params = {
                "part": "snippet",
                "type": "video",
                "order": args["order"],
                "maxResults": args["max_results"],
                "q": query_text,
                "relevanceLanguage": args["relevance_language"] or research["relevance_language"],
                "safeSearch": "moderate",
            }
            region_code = args["region_code"] or research.get("region_code")
            if region_code:
                params["regionCode"] = region_code
            result = api_get("search", params, api_key)
            items = result.get("items") or []
            page_info = result.get("pageInfo") or {}
            query_result = {
                "query": query_text,
                "query_language": args["query_language"] or research["relevance_language"],
                "order": args["order"],
                "region_code": region_code or "",
                "relevance_language": args["relevance_language"] or research["relevance_language"],
                "requested_max_results": args["max_results"],
                "api_returned_results": len(items),
                "api_total_results_estimate": page_info.get("totalResults"),
                "has_more_results": bool(result.get("nextPageToken")),
                "results": [],
            }
            for api_rank, item in enumerate(items, start=1):
                video_id = (item.get("id") or {}).get("videoId")
                if not video_id:
                    continue
                snippet = item.get("snippet") or {}
                thumbs = snippet.get("thumbnails") or {}
                row = {
                    "video_id": video_id,
                    "title": snippet.get("title", ""),
                    "channel_title": snippet.get("channelTitle", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail_url": (
                        thumbs.get("maxres", {}).get("url")
                        or thumbs.get("high", {}).get("url")
                        or thumbs.get("medium", {}).get("url")
                        or thumbs.get("default", {}).get("url", "")
                    ),
                    "description": snippet.get("description", ""),
                    "search_result_rank": api_rank,
                    "details_available": False,
                    "views": None,
                    "duration_seconds": None,
                }
                query_result["results"].append(row)
                id_to_rows.setdefault(video_id, []).append(row)
            channel_result["queries"].append(query_result)
            time.sleep(0.1)
        report["channels"].append(channel_result)

    video_ids = list(id_to_rows)
    for start in range(0, len(video_ids), 50):
        result = api_get(
            "videos",
            {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(video_ids[start:start + 50]),
            },
            api_key,
        )
        for item in result.get("items", []):
            video_id = item["id"]
            statistics = item.get("statistics") or {}
            views = int(statistics["viewCount"]) if "viewCount" in statistics else None
            duration_text = (item.get("contentDetails") or {}).get("duration")
            duration = parse_duration(duration_text) if duration_text else None
            snippet = item.get("snippet", {})
            published = snippet.get("publishedAt", "")
            thumbs = snippet.get("thumbnails", {})
            for row in id_to_rows.get(video_id, []):
                row["details_available"] = True
                row["views"] = views
                row["duration_seconds"] = duration
                row["published_at"] = published or row["published_at"]
                row["channel_title"] = snippet.get("channelTitle", row["channel_title"])
                row["title"] = snippet.get("title", row["title"])
                row["description"] = snippet.get("description", row["description"])
                row["thumbnail_url"] = (
                    thumbs.get("maxres", {}).get("url")
                    or thumbs.get("high", {}).get("url")
                    or thumbs.get("medium", {}).get("url")
                    or thumbs.get("default", {}).get("url", row["thumbnail_url"])
                )

    os.makedirs(output_dir, exist_ok=True)
    date_tag = now.strftime("%Y-%m-%d")
    if args["tag"]:
        safe_tag = normalize_tag(args["tag"])
        if not safe_tag:
            raise SystemExit("--tag must contain letters or numbers.")
        date_tag += f"-{safe_tag}"
    json_path = os.path.join(output_dir, f"youtube-market-scan-{date_tag}.json")
    markdown_path = os.path.join(output_dir, f"youtube-market-scan-{date_tag}.md")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with open(markdown_path, "w", encoding="utf-8") as handle:
        handle.write(render_report(report, args["top_per_query"]))
    print(f"Scanned {len(report['channels'])} channels and {len(id_to_rows)} distinct videos.")
    print(f"Markdown report: {markdown_path}")
    print(f"Raw metadata: {json_path}")
    print("Read the report before writing the beat map. Views are not evidence for facts.")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (OSError, ValueError, KeyError, RuntimeError, json.JSONDecodeError) as exc:
        configure_console()
        raise SystemExit(f"Error: {exc}")
