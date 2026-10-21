#!/usr/bin/env python3
"""Research public titles, thumbnails, descriptions, and tag language for one episode.

YouTube's API does not return another channel's Studio tags. This scan uses
public titles, description openings, hashtags, and thumbnail links. The agent
looks at the thumbnails, writes one packaging observation, then fills
youtube_metadata. export_youtube.py waits for that observation.

  python scripts/research_packaging.py "<episode>" --query "..." --query "..."

The key is YOUTUBE_API_KEY in the repo .env. It is never printed or saved.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone

from local_guard import refuse_out_dir
from research_youtube import (
    CHANNELS_FILE,
    age_days,
    api_get,
    configure_console,
    load_project_env,
    parse_duration,
)


HASHTAG = re.compile(r"#[\w]{2,}", re.UNICODE)
WORD = re.compile(r"[^\W\d_]{3,}", re.UNICODE)


def fold(text):
    text = unicodedata.normalize("NFD", (text or "").casefold())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def query_words(queries, language):
    stop = {fold(word) for word in STOP.get(language, set())}
    words = []
    for query in queries:
        for word in WORD.findall(fold(query)):
            if word in stop or word in words:
                continue
            words.append(word)
    return words


def on_topic(video, words):
    if not words:
        return True
    title_words = set(WORD.findall(fold(video.get("title") or "")))
    overlap = [word for word in words if word in title_words]
    return len(overlap) >= 2 or any(len(word) >= 5 for word in overlap)
STOP = {
    "en": {"the", "and", "for", "how", "what", "why", "with", "from", "that", "this", "video", "explained", "are", "you", "your", "into", "about"},
    "es": {"los", "las", "una", "uno", "para", "por", "con", "que", "como", "cómo", "del", "video", "explicado", "esta", "este"},
    "vi": {"của", "cho", "một", "các", "với", "trong", "được", "này", "không", "khi", "đến", "trên", "video", "cách", "những", "theo", "hoặc", "vào", "nào", "thế"},
}


def load_episode(project_dir):
    refuse_out_dir(project_dir)
    path = os.path.join(project_dir, "beats.json")
    if not os.path.isfile(path):
        raise SystemExit("No beats.json. Bind the episode first: python scripts/channels.py bind <channel-id> <slug>")
    with open(path, encoding="utf-8-sig") as handle:
        doc = json.load(handle)
    if not doc.get("channel_id"):
        raise SystemExit("No channel bound on this episode.")
    return path, doc


def channel_research(channel_id):
    with open(CHANNELS_FILE, encoding="utf-8-sig") as handle:
        channels = json.load(handle)["channels"]
    for channel in channels:
        if channel["id"] == channel_id:
            research = channel.get("youtube_research") or {}
            if not research.get("relevance_language"):
                raise SystemExit(f"Channel {channel_id} has no youtube_research.relevance_language.")
            return channel, research
    raise SystemExit(f"Unknown channel {channel_id}.")


def parse_args(argv):
    if not argv:
        raise SystemExit('usage: python scripts/research_packaging.py <episode_dir> --query "..." [--query "..."] [--region-code MX] [--max-results 8] [--orders relevance,date,viewCount]')
    args = {"episode": os.path.abspath(argv[0]), "queries": [], "max_results": 8, "orders": ["relevance", "date", "viewCount"], "region_code": ""}
    i = 1
    while i < len(argv):
        token = argv[i]
        if token == "--query":
            i += 1
            if i >= len(argv):
                raise SystemExit("--query needs a value")
            args["queries"].append(argv[i].strip())
        elif token == "--max-results":
            i += 1
            args["max_results"] = int(argv[i])
        elif token == "--orders":
            i += 1
            args["orders"] = [part.strip() for part in argv[i].split(",") if part.strip()]
        elif token == "--region-code":
            i += 1
            if i >= len(argv):
                raise SystemExit("--region-code needs a value")
            args["region_code"] = argv[i].strip().upper()
        else:
            raise SystemExit(f"Unknown argument {token}")
        i += 1
    if not 5 <= args["max_results"] <= 15:
        raise SystemExit("--max-results must be from 5 to 15.")
    allowed = {"relevance", "date", "viewCount"}
    if not args["orders"] or any(order not in allowed for order in args["orders"]):
        raise SystemExit("--orders must be a comma list of relevance, date, viewCount.")
    if args["region_code"] and (len(args["region_code"]) != 2 or not args["region_code"].isalpha()):
        raise SystemExit("--region-code must be a two-letter country code, such as VN, MX, or ES.")
    args["queries"] = [query for query in args["queries"] if query]
    return args


def search_once(query, order, research, max_results, api_key, region_code=""):
    params = {
        "part": "snippet",
        "type": "video",
        "order": order,
        "maxResults": max_results,
        "q": query,
        "relevanceLanguage": research["relevance_language"],
        "safeSearch": "moderate",
    }
    region_code = region_code or research.get("region_code") or ""
    if region_code:
        params["regionCode"] = region_code
    result = api_get("search", params, api_key)
    rows = []
    for item in result.get("items", []):
        video_id = (item.get("id") or {}).get("videoId")
        if not video_id:
            continue
        snippet = item.get("snippet") or {}
        thumbs = snippet.get("thumbnails") or {}
        rows.append({
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
            "description": snippet.get("description", ""),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "thumbnail_url": (
                thumbs.get("high", {}).get("url")
                or thumbs.get("medium", {}).get("url")
                or thumbs.get("default", {}).get("url", "")
            ),
            "orders": [order],
            "queries": [query],
            "views": 0,
            "duration_seconds": 0,
        })
    return rows


def merge_details(videos, api_key, now):
    ids = list(videos)
    for start in range(0, len(ids), 50):
        result = api_get(
            "videos",
            {"part": "snippet,statistics,contentDetails", "id": ",".join(ids[start:start + 50])},
            api_key,
        )
        for item in result.get("items", []):
            row = videos.get(item["id"])
            if not row:
                continue
            snippet = item.get("snippet") or {}
            published = snippet.get("publishedAt") or row["published_at"]
            thumbs = snippet.get("thumbnails") or {}
            row["title"] = snippet.get("title") or row["title"]
            row["channel_title"] = snippet.get("channelTitle") or row["channel_title"]
            row["description"] = snippet.get("description") or row["description"]
            row["published_at"] = published
            row["views"] = int((item.get("statistics") or {}).get("viewCount", 0))
            row["duration_seconds"] = parse_duration((item.get("contentDetails") or {}).get("duration", ""))
            row["views_per_day"] = round(row["views"] / age_days(published, now)) if published else 0
            row["thumbnail_url"] = (
                thumbs.get("maxres", {}).get("url")
                or thumbs.get("high", {}).get("url")
                or row["thumbnail_url"]
            )


def opening(description):
    text = " ".join((description or "").split())
    if len(text) > 180:
        return text[:177].rstrip() + "..."
    return text or "(no description returned)"


def title_stats(videos):
    lengths = sorted(len(video["title"]) for video in videos)
    if not lengths:
        return {"count": 0, "shortest": 0, "median": 0, "longest": 0, "questions": 0}
    mid = len(lengths) // 2
    median = lengths[mid] if len(lengths) % 2 else round((lengths[mid - 1] + lengths[mid]) / 2)
    questions = sum(1 for video in videos if "?" in video["title"] or "¿" in video["title"])
    return {"count": len(videos), "shortest": lengths[0], "median": median, "longest": lengths[-1], "questions": questions}


def repeated_words(videos, language):
    if language in ("ja", "ko"):
        return []
    stop = STOP.get(language, set())
    counts = {}
    for video in videos:
        seen = set()
        for word in WORD.findall(video["title"].casefold()):
            if word in stop or word in seen:
                continue
            seen.add(word)
            counts[word] = counts.get(word, 0) + 1
    ranked = sorted((count, word) for word, count in counts.items() if count >= 2)
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [word for _, word in ranked[:12]]


def hashtag_counts(videos):
    counts = {}
    for video in videos:
        for tag in HASHTAG.findall(video.get("description") or ""):
            key = tag.casefold()
            counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:8]


def tag_pool(queries, words):
    pool = []
    for query in queries:
        if query not in pool:
            pool.append(query)
    for word in words:
        if word not in pool:
            pool.append(word)
    text = ", ".join(pool)
    return pool, len(text)


def render(channel, queries, orders, videos, language, region_code, skipped):
    stats = title_stats(videos)
    words = repeated_words(videos, language)
    tags, tag_chars = tag_pool(queries, words)
    hashtags = hashtag_counts(videos)
    lines = [
        "# Packaging research",
        "",
        f"Channel: {channel['display_name']} ({channel['id']}) | Language: {language}",
        f"Search region: {region_code or 'YouTube default'}",
        f"Orders: {', '.join(orders)}",
        "",
        "Public search only. Region and language are discovery filters, not audience analytics. "
        "Views are not retention or proof that a title works. "
        "Do not copy a title, thumbnail, description, or visual identity. "
        "YouTube does not return another channel's Studio tags. "
        f"Videos whose titles do not share enough words with the search phrases are left out ({skipped} left out).",
        "",
        "## Search phrases",
        "",
    ]
    lines.extend(f"- {query}" for query in queries)
    lines.extend(["", "## Titles", ""])
    if videos:
        lines.append(
            f"{stats['count']} distinct videos. Title length: shortest {stats['shortest']}, "
            f"median {stats['median']}, longest {stats['longest']}. "
        f"{stats['questions']} titles contain a question mark. "
            "Studio title limit is 60 characters (Japanese 32); the autocomplete-observed phrase sits in the first 40 characters (Japanese 20). Keep titles accurate. "
            "Make one candidate searchable and another curiosity-led while still naming the subject. "
            "The title, thumbnail, and opening must share one promise. Public view counts do not reveal audience preference."
        )
    else:
        lines.append("No videos returned. Try a closer query in this channel's language.")
    lines.extend(["", "## Description openings", ""])
    lines.append("Use a unique opening that says what this episode explains and its country or time scope. Include one or two natural search phrases; do not stuff keywords. Add source links and useful chapter timestamps after the opening when available.")
    lines.append("")
    for video in videos:
        title = video["title"].replace("\n", " ")
        lines.append(f"- **{title}** — {opening(video['description'])}")
    lines.extend(["", "## Hashtags seen in public descriptions", ""])
    if hashtags:
        lines.append("Use at most three, each starting with #, and only when they name this episode.")
        lines.append("")
        lines.extend(f"- {tag} ({count})" for tag, count in hashtags)
    else:
        lines.append("None returned. Add a hashtag only if it names this episode. Three is enough.")
    lines.extend(["", "## Studio tag pool", ""])
    lines.append(
        "This is a heuristic idea pool from search phrases and repeated public-title words, not competitor tag data. "
        f"Pasting all of it would use {tag_chars} characters. The upload limit is 500. "
        "Tags play a minimal role in discovery; prioritize an accurate title, a clear thumbnail, and a useful description. "
        "Keep only episode-specific names and useful spelling, diacritic, transliteration, or abbreviation variants. "
        "Drop broad or duplicate tags."
    )
    lines.append("")
    if tags:
        lines.extend(f"- {tag}" for tag in tags)
    else:
        lines.append("- (add variants of the episode question by hand)")
    lines.extend(["", "## Thumbnails to open", ""])
    lines.append("Open each image. Note its focal subject/action, contrast, the question the picture asks, and what it leaves out. Check whether the real subject is visible without a forced host character. Views are discovery context, not evidence that its thumbnail earns clicks or viewing time; the API cannot judge what the image communicates.")
    lines.append("")
    lines.append("| Title | Length | Views | Published | Thumbnail |")
    lines.append("|---|---:|---:|---|---|")
    for video in videos:
        title = video["title"].replace("|", "\\|").replace("\n", " ")
        label = f"[{title}]({video['url']})"
        thumb = f"[open]({video['thumbnail_url']})" if video.get("thumbnail_url") else "—"
        published = (video.get("published_at") or "")[:10]
        lines.append(f"| {label} | {len(video['title'])} | {video['views']:,} | {published} | {thumb} |")
    lines.extend([
        "",
        "## Write this before export",
        "",
        "Add one object to `youtube_metadata.packaging_research` in beats.json:",
        "",
        "```json",
        '{ "observation": "What the titles name first, what the thumbnails show, and the gap this episode can answer. Do not copy." }',
        "```",
        "",
        "Then fill `promise`, up to three materially different `candidates`, `description`, `hashtags`, and a short relevant `studio_tags` list. "
        "If available after upload, test up to three genuinely different title/thumbnail options together in YouTube Studio. The native result uses watch-time share, so judge CTR in context and check retention to confirm the promise brought the right viewers. "
        "`export_youtube.py` stops until that observation exists.",
        "",
    ])
    return "\n".join(lines)


def remember(doc, queries, orders, report_rel, video_count, region_code):
    metadata = doc.setdefault("youtube_metadata", {})
    phrases = [item for item in (metadata.get("search_phrases") or []) if isinstance(item, str) and item.strip()]
    for query in queries:
        if query not in phrases:
            phrases.append(query)
    metadata["search_phrases"] = phrases
    notes = [item for item in (metadata.get("packaging_research") or []) if isinstance(item, dict) and item.get("kind") != "scan"]
    notes.append({
        "kind": "scan",
        "report": report_rel.replace("\\", "/"),
        "queries": queries,
        "orders": orders,
        "videos": video_count,
        "region_code": region_code or "",
    })
    metadata["packaging_research"] = notes


def main(argv):
    configure_console()
    args = parse_args(argv)
    path, doc = load_episode(args["episode"])
    channel, research = channel_research(doc["channel_id"])
    region_code = args["region_code"] or research.get("region_code") or ""
    queries = args["queries"] or [item.strip() for item in (doc.get("youtube_metadata") or {}).get("search_phrases") or [] if isinstance(item, str) and item.strip()]
    if not queries and (doc.get("topic") or "").strip():
        queries = [doc["topic"].strip()]
    if not queries:
        raise SystemExit('Pass at least one --query, or set beats.json topic / youtube_metadata.search_phrases.')
    load_project_env()
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("YOUTUBE_API_KEY is not set. Put it in the repo .env. Do not paste it into the command.")
    now = datetime.now(timezone.utc)
    videos = {}
    for query in queries:
        for order in args["orders"]:
            for row in search_once(query, order, research, args["max_results"], api_key, region_code):
                existing = videos.get(row["video_id"])
                if existing:
                    for key in ("orders", "queries"):
                        for value in row[key]:
                            if value not in existing[key]:
                                existing[key].append(value)
                else:
                    videos[row["video_id"]] = row
            time.sleep(0.1)
    merge_details(videos, api_key, now)
    language = doc.get("language") or channel.get("language") or "unknown"
    words = query_words(queries, language)
    matched = [video for video in videos.values() if on_topic(video, words)]
    skipped = len(videos) - len(matched)
    ranked = sorted(matched, key=lambda video: (-len(video["orders"]), -video["views"]))[:15]
    research_dir = os.path.join(args["episode"], "research")
    os.makedirs(research_dir, exist_ok=True)
    slug = doc.get("episode_slug") or doc.get("project") or "episode"
    safe_slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", slug).strip("-") or "episode"
    name = f"packaging-{now.strftime('%Y-%m-%d')}-{safe_slug}.md"
    report_path = os.path.join(research_dir, name)
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(render(channel, queries, args["orders"], ranked, language, region_code, skipped))
    remember(doc, queries, args["orders"], os.path.join("research", name), len(ranked), region_code)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Packaging scan: {len(ranked)} videos")
    print(f"Report: {report_path}")
    print("Open the thumbnail links, then add packaging_research.observation before export_youtube.py.")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (OSError, ValueError, KeyError, RuntimeError, json.JSONDecodeError) as exc:
        configure_console()
        raise SystemExit(f"Error: {exc}")
