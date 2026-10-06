#!/usr/bin/env python3
"""Collect public YouTube search metadata before an episode is written.

The key is read from YOUTUBE_API_KEY in the repo .env, or from the process
environment if that is already set. The key is never printed or written into
the report.

Discovery scan, using the queries stored on the channel:

  python scripts/research_youtube.py --channel moc-vy

One episode, before the beat map. Write the report inside that episode:

  python scripts/research_youtube.py --channel moc-vy --query "..." --tag <slug> --output-dir "<episode>\\research"
"""
from __future__ import annotations

import json
import os
import re
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


def api_get(resource, params, api_key):
    query = dict(params)
    query["key"] = api_key
    url = f"{API_ROOT}/{resource}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # The request URL contains the key. Do not include it in the error.
        try:
            body = json.loads(exc.read().decode("utf-8", errors="replace"))
            message = body.get("error", {}).get("message", "")
        except (ValueError, AttributeError):
            message = ""
        raise RuntimeError(f"YouTube Data API returned HTTP {exc.code}. {message}".strip()) from None
    except urllib.error.URLError:
        raise RuntimeError("Could not reach the YouTube Data API.") from None


def parse_duration(value):
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return 0
    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def age_days(published_at, now):
    published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    return max((now - published).total_seconds() / 86400, 1 / 24)


def render_report(report, top_per_query):
    order_label = report["method"]["order"]
    lines = [
        "# YouTube public search scan",
        "",
        f"Scanned at: {report['scanned_at_utc']}",
        "",
        f"> Search order: `{order_label}`. This is a packaging and topic snapshot, not factual evidence. "
        "Views and views/day do not show retention, satisfaction, click-through rate, or whether a new "
        "channel can reproduce the result. Region and language filters are search slices, not audience analytics.",
        "",
    ]
    for channel in report["channels"]:
        lines.extend([f"## {channel['display_name']}", ""])
        for query in channel["queries"]:
            lines.extend([f"### {query['query']}", ""])
            rows = query["results"][:top_per_query]
            if not rows:
                lines.extend(["No results returned for this query.", ""])
                continue
            lines.extend([
                "| Video | Thumbnail | Views | Avg views/day since upload (rough) | Published | Length |",
                "|---|---|---:|---:|---|---:|",
            ])
            for video in rows:
                title = video["title"].replace("|", "\\|").replace("\n", " ")
                channel_name = video["channel_title"].replace("|", "\\|")
                label = f"[{title}]({video['url']}) · {channel_name}"
                thumbnail = f"[open]({video['thumbnail_url']})" if video.get("thumbnail_url") else "—"
                lines.append(
                    f"| {label} | {thumbnail} | {video['views']:,} | {video['views_per_day']:,} | "
                    f"{video['published_at'][:10]} | {video['duration_seconds']}s |"
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
    if args["queries"] and len(set(args["channels"])) != 1:
        raise SystemExit("A topic query needs exactly one --channel.")
    if args["queries"] and not args["tag"]:
        raise SystemExit("A topic query also needs --tag so it does not replace another scan.")
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
    now = datetime.now(timezone.utc)
    report = {
        "scanned_at_utc": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "method": {
            "endpoint": "YouTube Data API v3 search.list and videos.list",
            "order": args["order"],
            "max_results_per_query": args["max_results"],
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
                "relevanceLanguage": research["relevance_language"],
                "safeSearch": "moderate",
            }
            if research.get("region_code"):
                params["regionCode"] = research["region_code"]
            result = api_get("search", params, api_key)
            query_result = {"query": query_text, "results": []}
            for item in result.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                if not video_id:
                    continue
                snippet = item.get("snippet", {})
                thumbs = snippet.get("thumbnails", {})
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
                    "views": 0,
                    "views_per_day": 0,
                    "duration_seconds": 0,
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
            views = int(item.get("statistics", {}).get("viewCount", 0))
            duration = parse_duration(item.get("contentDetails", {}).get("duration", ""))
            snippet = item.get("snippet", {})
            published = snippet.get("publishedAt", "")
            age = age_days(published, now) if published else 1.0
            thumbs = snippet.get("thumbnails", {})
            for row in id_to_rows.get(video_id, []):
                row["views"] = views
                row["views_per_day"] = round(views / age)
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
        safe_tag = re.sub(r"[^a-zA-Z0-9_-]+", "-", args["tag"]).strip("-")
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
