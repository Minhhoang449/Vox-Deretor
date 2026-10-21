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
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from local_guard import ROOT, refuse_out_dir


CHANNELS_FILE = os.path.join(ROOT, "config", "channels.json")
API_ROOT = "https://www.googleapis.com/youtube/v3"
BREAKOUT_VIEWS_PER_SUB = 0.8
VALID_ORDERS = ("relevance", "date", "viewCount")


class NetworkUnavailable(RuntimeError):
    """Transport failure (DNS, socket, proxy, sandbox). Triggers the yt-dlp fallback."""


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
        raise NetworkUnavailable(
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
        raise NetworkUnavailable(
            "Could not reach the YouTube Data API. " + format_network_error(exc)
        ) from None
    except (socket.timeout, TimeoutError, ConnectionError) as exc:
        raise NetworkUnavailable(
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


def add_ratios(row, now):
    """Add views_per_day and views_per_sub. Missing inputs stay None (rendered 'unavailable')."""
    views = row.get("views")
    subs = row.get("subscribers")
    published = row.get("published_at") or ""
    row["age_days"] = None
    row["views_per_day"] = None
    if published:
        try:
            row["age_days"] = round(age_days(published, now), 2)
        except ValueError:
            pass
    if isinstance(views, int) and row["age_days"]:
        row["views_per_day"] = round(views / row["age_days"], 1)
    if isinstance(views, int) and isinstance(subs, int) and subs > 0:
        row["views_per_sub"] = round(views / subs, 3)
    else:
        row["views_per_sub"] = None
    row["breakout"] = bool(
        row["views_per_sub"] is not None and row["views_per_sub"] >= BREAKOUT_VIEWS_PER_SUB
    )
    return row


def parse_ytdlp_date(value):
    """yt-dlp upload_date YYYYMMDD -> ISO8601 Z string, or ''."""
    if not value or not re.fullmatch(r"\d{8}", str(value)):
        return ""
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}T00:00:00Z"


def row_from_ytdlp(info, rank):
    """Build a report row from a yt-dlp per-video JSON dict. Hidden subs stay None."""
    video_id = info.get("id") or ""
    def as_int(key):
        value = info.get(key)
        return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    thumbs = info.get("thumbnails") or []
    thumb = info.get("thumbnail") or (thumbs[-1].get("url") if thumbs and isinstance(thumbs[-1], dict) else "")
    return {
        "video_id": video_id,
        "title": info.get("title") or "",
        "channel_title": info.get("channel") or info.get("uploader") or "",
        "channel_id": info.get("channel_id") or "",
        "published_at": parse_ytdlp_date(info.get("upload_date")),
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail_url": thumb or "",
        "description": info.get("description") or "",
        "search_result_rank": rank,
        "details_available": True,
        "views": as_int("view_count"),
        "duration_seconds": as_int("duration"),
        "subscribers": as_int("channel_follower_count"),
    }


def parse_ytdlp_search(stdout, entries=None):
    """Parse `--flat-playlist -j` output (one JSON per line) into video ids.

    If `entries` is a dict, flat metadata (title, channel, duration) is stored per id.
    Flat view_count is not trusted (often 0), so it is never used as a view count.
    """
    ids = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        vid = entry.get("id")
        if vid and vid not in ids and entry.get("ie_key", "Youtube") in ("Youtube", None):
            ids.append(vid)
            if entries is not None:
                entries[vid] = entry
    return ids


def _run_ytdlp(args, timeout=120):
    return subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--no-warnings", "--ignore-config", *args],
        capture_output=True, text=True, timeout=timeout,
    )


def ytdlp_query(query_text, order, max_results, failures, language=""):
    """Search with yt-dlp; returns list of rows. Records failed cells in `failures`."""
    extra = ["--extractor-args", f"youtube:lang={language}"] if language else []
    if order == "date":
        target = ("https://www.youtube.com/results?search_query="
                  + urllib.parse.quote_plus(query_text) + "&sp=CAI%253D")
        limit = ["--playlist-end", str(max_results)]
    else:
        target, limit = f"ytsearch{max_results}:{query_text}", []
    flat = {}
    try:
        proc = _run_ytdlp([*extra, *limit, "--flat-playlist", "-j", target])
    except (OSError, subprocess.TimeoutExpired) as exc:
        failures.append({"query": query_text, "order": order, "cell": "search", "error": str(exc)[:200]})
        return []
    ids = parse_ytdlp_search(proc.stdout, flat)[:max_results]
    if proc.returncode != 0 and not ids:
        failures.append({"query": query_text, "order": order, "cell": "search",
                         "error": (proc.stderr.strip().splitlines() or ["yt-dlp failed"])[-1][:200]})
        return []
    rows = []
    for rank, vid in enumerate(ids, start=1):
        try:
            proc = _run_ytdlp([*extra, "--skip-download", "-j", f"https://www.youtube.com/watch?v={vid}"], timeout=90)
            info = json.loads(proc.stdout.splitlines()[0]) if proc.returncode == 0 and proc.stdout.strip() else None
        except (OSError, subprocess.TimeoutExpired, ValueError, IndexError):
            info = None
            proc = None
        if not info:
            err = ""
            if proc is not None:
                err = (proc.stderr.strip().splitlines() or [""])[-1][:200]
            failures.append({"query": query_text, "order": order, "cell": f"video {vid} views/subs/length",
                             "error": err or "metadata unavailable"})
            entry = flat.get(vid, {})
            dur = entry.get("duration")
            rows.append({"video_id": vid, "title": entry.get("title") or vid,
                         "channel_title": entry.get("channel") or entry.get("uploader") or "",
                         "channel_id": entry.get("channel_id") or "", "published_at": "",
                         "url": f"https://www.youtube.com/watch?v={vid}", "thumbnail_url": "",
                         "description": "", "search_result_rank": rank, "details_available": False,
                         "views": None,
                         "duration_seconds": int(dur) if isinstance(dur, (int, float)) else None,
                         "subscribers": None})
            continue
        rows.append(row_from_ytdlp(info, rank))
    return rows


def breakout_summary(rows):
    """Group breakout rows by channel, highest ratio first."""
    hits = sorted((r for r in rows if r.get("breakout")), key=lambda r: -r["views_per_sub"])
    by_channel = {}
    for row in hits:
        by_channel.setdefault(row.get("channel_title") or "unknown", []).append(row)
    return by_channel


def _num(value, fmt="{:,}"):
    return fmt.format(value) if isinstance(value, (int, float)) else "unavailable"


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
        f"Data source: `{report['method'].get('source', 'youtube-data-api')}`",
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
            lines.extend([f"### {query['query']} (order: {query.get('order', order_label)})", ""])
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
                "| Search result | Video | Thumbnail | Public views at scan | Subs | Views/sub | Views/day | Published | Length | Breakout |",
                "|---:|---|---|---:|---:|---:|---:|---|---:|---|",
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
                    f"{_num(video.get('subscribers'))} | {_num(video.get('views_per_sub'), '{:.2f}')} | "
                    f"{_num(video.get('views_per_day'), '{:,.1f}')} | "
                    f"{(video.get('published_at') or 'unavailable')[:10]} | {duration_label} | "
                    f"{'**yes**' if video.get('breakout') else ''} |"
                )
            lines.append("")
            lines.extend([f"#### Breakout videos (>={BREAKOUT_VIEWS_PER_SUB} views/sub)", ""])
            groups = breakout_summary(query["results"])
            if not groups:
                lines.append("None in this slice (or subscriber counts unavailable).")
            for channel_name, hits in groups.items():
                subs = hits[0].get("subscribers")
                lines.append(f"- **{channel_name}** ({_num(subs)} subs): " + "; ".join(
                    f"[{h['title']}]({h['url']}) {h['views_per_sub']:.2f} views/sub, "
                    f"{_num(h.get('views_per_day'), '{:,.1f}')} views/day" for h in hits))
            lines.append("")
            lines.extend(["#### Description excerpts", ""])
            for video in rows:
                description = " ".join((video.get("description") or "").split())
                if len(description) > 360:
                    description = description[:357].rstrip() + "..."
                description = description.replace("|", "\\|") or "(no description returned)"
                lines.append(f"- **{video['title']}** — {description}")
            lines.append("")
    failures = report.get("failed_cells") or []
    if failures:
        lines.extend(["## Cells that could not be fetched", "",
                      "These cells are missing because the fetch failed (often a YouTube bot block). "
                      "They are unknown, not zero.", ""])
        for item in failures:
            lines.append(f"- `{item['query']}` ({item['order']}) · {item['cell']}: {item['error']}")
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
        "top_per_query": 10,
        "order": "relevance,date",
        "published_after_days": 365,
        "force_ytdlp": False,
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
        elif token == "--published-after-days":
            args["published_after_days"] = int(need(token))
        elif token == "--yt-dlp":
            args["force_ytdlp"] = True
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
    orders = list(dict.fromkeys(o.strip() for o in args["order"].split(",") if o.strip()))
    if not orders or any(o not in VALID_ORDERS for o in orders):
        raise SystemExit("--order must be a comma list of relevance, date, viewCount.")
    args["orders"] = orders
    if args["published_after_days"] < 0:
        raise SystemExit("--published-after-days must be 0 (off) or more.")
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


def collect_api(args, channels, api_key, now):
    report = {
        "scanned_at_utc": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "method": {
            "endpoint": "YouTube Data API v3 search.list, videos.list and channels.list",
            "source": "youtube-data-api",
            "order": ",".join(args["orders"]),
            "published_after_days": args["published_after_days"],
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
        for query_text, order in ((q, o) for q in query_texts for o in args["orders"]):
            params = {
                "part": "snippet",
                "type": "video",
                "order": order,
                "maxResults": args["max_results"],
                "q": query_text,
                "relevanceLanguage": args["relevance_language"] or research["relevance_language"],
                "safeSearch": "moderate",
            }
            region_code = args["region_code"] or research.get("region_code")
            if region_code:
                params["regionCode"] = region_code
            if order == "date" and args["published_after_days"]:
                after = now - timedelta(days=args["published_after_days"])
                params["publishedAfter"] = after.isoformat(timespec="seconds").replace("+00:00", "Z")
            result = api_get("search", params, api_key)
            items = result.get("items") or []
            page_info = result.get("pageInfo") or {}
            query_result = {
                "query": query_text,
                "query_language": args["query_language"] or research["relevance_language"],
                "order": order,
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
                if not video_id or any(r["video_id"] == video_id for r in query_result["results"]):
                    continue
                snippet = item.get("snippet") or {}
                thumbs = snippet.get("thumbnails") or {}
                row = {
                    "video_id": video_id,
                    "title": snippet.get("title", ""),
                    "channel_title": snippet.get("channelTitle", ""),
                    "channel_id": snippet.get("channelId", ""),
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
                    "subscribers": None,
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

    channel_ids = list(dict.fromkeys(
        row.get("channel_id") for rows in id_to_rows.values() for row in rows if row.get("channel_id")))
    subs_by_channel = {}
    for start in range(0, len(channel_ids), 50):
        result = api_get("channels", {"part": "statistics", "id": ",".join(channel_ids[start:start + 50])}, api_key)
        subs_by_channel.update(parse_channel_stats(result))
    for rows in id_to_rows.values():
        for row in rows:
            row["subscribers"] = subs_by_channel.get(row.get("channel_id"))
    return report


def parse_channel_stats(result):
    """channels.list -> {channel_id: int subs or None if hidden}. Never guessed."""
    out = {}
    for item in (result or {}).get("items", []):
        stats = item.get("statistics") or {}
        if stats.get("hiddenSubscriberCount") or "subscriberCount" not in stats:
            out[item["id"]] = None
        else:
            out[item["id"]] = int(stats["subscriberCount"])
    return out


def collect_ytdlp(args, channels, now, reason):
    report = {
        "scanned_at_utc": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "method": {
            "endpoint": "yt-dlp ytsearch/ytsearchdate + per-video metadata",
            "source": "yt-dlp",
            "fallback_reason": reason,
            "order": ",".join(args["orders"]),
            "published_after_days": args["published_after_days"],
            "max_results_per_query": args["max_results"],
            "region_code_override": args["region_code"] or None,
            "relevance_language_override": args["relevance_language"] or None,
            "query_language": args["query_language"] or None,
            "cross_language_note": args["cross_language_note"] or None,
            "note": "yt-dlp search has no region filter; viewCount order is approximated by relevance.",
        },
        "channels": [],
        "failed_cells": [],
    }
    cutoff = None
    if args["published_after_days"]:
        cutoff = (now - timedelta(days=args["published_after_days"])).strftime("%Y-%m-%d")
    for channel in channels:
        research = channel.get("youtube_research")
        if not research:
            continue
        lang = args["relevance_language"] or research["relevance_language"]
        channel_result = {
            "channel_id": channel["id"], "display_name": channel["display_name"],
            "relevance_language": lang, "query_language": args["query_language"] or lang,
            "region_code": args["region_code"] or research.get("region_code", ""), "queries": [],
        }
        for query_text in (args["queries"] or research["queries"]):
            for order in args["orders"]:
                rows = ytdlp_query(query_text, order, args["max_results"], report["failed_cells"], lang)
                if order == "date" and cutoff:
                    rows = [r for r in rows if not r["published_at"] or r["published_at"][:10] >= cutoff]
                channel_result["queries"].append({
                    "query": query_text, "query_language": args["query_language"] or lang,
                    "order": order, "region_code": channel_result["region_code"],
                    "relevance_language": lang, "requested_max_results": args["max_results"],
                    "api_returned_results": len(rows), "api_total_results_estimate": None,
                    "has_more_results": False, "results": rows,
                })
        report["channels"].append(channel_result)
    return report


def main(argv):
    configure_console()
    args = parse_args(argv)
    load_project_env()
    api_key = os.environ.get(args["api_key_env"], "").strip()
    use_ytdlp = args["force_ytdlp"] or not api_key
    fallback_reason = "forced with --yt-dlp" if args["force_ytdlp"] else (
        f"{args['api_key_env']} is not set" if not api_key else "")
    if use_ytdlp:
        print(f"YouTube API unavailable ({fallback_reason}); using yt-dlp fallback.", file=sys.stderr)
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
    report = None
    if not use_ytdlp:
        try:
            report = collect_api(args, channels, api_key, now)
        except NetworkUnavailable as exc:
            fallback_reason = str(exc)
            print(f"{exc} Falling back to yt-dlp.", file=sys.stderr)
    if report is None:
        report = collect_ytdlp(args, channels, now, fallback_reason)
    for channel_result in report["channels"]:
        for query in channel_result["queries"]:
            for row in query["results"]:
                add_ratios(row, now)
    id_to_rows = {r["video_id"] for c in report["channels"] for q in c["queries"] for r in q["results"]}
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
    breakouts = sum(1 for c in report["channels"] for q in c["queries"] for r in q["results"] if r.get("breakout"))
    print(f"Source: {report['method']['source']}. Scanned {len(report['channels'])} channels and "
          f"{len(id_to_rows)} distinct videos; {breakouts} breakout rows; "
          f"{len(report.get('failed_cells') or [])} failed cells.")
    print(f"Markdown report: {markdown_path}")
    print(f"Raw metadata: {json_path}")
    print("Read the report before writing the beat map. Views are not evidence for facts.")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (OSError, ValueError, KeyError, RuntimeError, json.JSONDecodeError) as exc:
        configure_console()
        raise SystemExit(f"Error: {exc}")
