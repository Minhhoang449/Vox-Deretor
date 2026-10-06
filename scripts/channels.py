#!/usr/bin/env python3
"""
Bind one episode to a channel and create its folder on D:\\Vox-Video.

Layout: D:\\Vox-Video\\<channel destination>\\<slug>\\
Never use the repo out/ folder.

  python scripts/channels.py list
  python scripts/channels.py show moc-vy
  python scripts/channels.py bind moc-vy gia-gao
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHANNELS_FILE = os.path.join(ROOT, "config", "channels.json")


def _console():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_channels():
    with open(CHANNELS_FILE, encoding="utf-8-sig") as f:
        data = json.load(f)
    return data["channels"]


def slugify(value):
    value = value.strip().lower()
    value = re.sub(r"[^\w-]+", "-", value, flags=re.UNICODE)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    if not value:
        raise SystemExit("Slug must contain at least one letter or number.")
    return value


def episode_dir(channel, slug):
    root = channel.get("destination")
    if not root:
        raise SystemExit(f"Channel {channel['id']} has no destination.")
    return os.path.normpath(os.path.join(root, slugify(slug)))


def resolve(selector):
    if any(sep in selector for sep in ("/", "\\")) or selector.lower().startswith("out"):
        raise SystemExit(
            "Episodes are not stored under out/.\n"
            "usage: python scripts/channels.py bind <channel-id> <slug>\n"
            "Folder: D:\\Vox-Video\\<channel>\\<slug>"
        )
    key = selector.strip().casefold()
    for channel in load_channels():
        names = (channel["id"].casefold(), channel.get("display_name", "").casefold())
        if key in names:
            return channel
    known = ", ".join(channel["id"] for channel in load_channels())
    raise SystemExit(f"Unknown channel {selector!r}. Use one of: {known}")


def list_channels():
    for channel in load_channels():
        print(f"{channel['id']}\t{channel['language']}\t{channel['display_name']}")
        print(f"  {channel['promise']}")


def list_voices():
    """Per-channel VoiceStudio profile map stored on each channel in channels.json."""
    print("channel_id\tlanguage\tprofile_id\tprofile_name\treference")
    for channel in load_channels():
        ref = (channel.get("voice_reference") or {}).get("audio", "")
        print(
            f"{channel['id']}\t{channel['language']}\t{channel['voice']}\t"
            f"{channel.get('voice_profile_name', '')}\t{ref}"
        )


def show(selector):
    print(json.dumps(resolve(selector), ensure_ascii=False, indent=2))


def bind(selector, slug):
    channel = resolve(selector)
    project_dir = episode_dir(channel, slug)
    os.makedirs(project_dir, exist_ok=True)
    path = os.path.join(project_dir, "beats.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            doc = json.load(f)
    else:
        doc = {
            "project": slugify(slug),
            "topic": "",
            "aspect": "16:9",
            "style": "collage",
            "beats": [],
        }
    voice = doc.get("voice") if isinstance(doc.get("voice"), dict) else {}
    ref = channel.get("voice_reference") or {}
    for stale in ("instruct", "tone", "model", "speed"):
        voice.pop(stale, None)
    voice.update({
        "voice_id": channel["voice"],
        "language": channel["language"],
        "profile_name": channel.get("voice_profile_name", channel["display_name"]),
        "gender": channel.get("voice_gender", ""),
        "market": channel.get("voice_market", ""),
        "reference_audio": ref.get("audio", ""),
        "reference_transcript": ref.get("transcript", ""),
    })
    doc["pipeline"] = "local"
    doc["channel_id"] = channel["id"]
    doc["language"] = channel["language"]
    doc["project"] = slugify(slug)
    doc["episode_slug"] = slugify(slug)
    doc["episode_dir"] = project_dir
    doc["destination"] = channel.get("destination", "")
    doc["voice"] = voice
    doc["channel"] = channel
    doc.setdefault("youtube_metadata", {
        "promise": "",
        "search_phrases": [],
        "packaging_research": [],
        "candidates": [],
        "selected_candidate_id": "",
        "description": "",
        "hashtags": [],
        "studio_tags": [],
        "experiment": {"mode": "thumbnail_and_title", "hypothesis": ""},
    })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"bound {channel['id']} ({channel['display_name']}, {channel['language']})")
    print(f"voice {channel['voice']}  {voice['profile_name']}")
    print(f"episode {project_dir}")
    print(f"wrote {path}")
    print("Research this episode before the beat map:")
    print(f"  python scripts/research_youtube.py --channel {channel['id']} --query \"<question>\" --tag {slugify(slug)} --output-dir \"{project_dir}\\research\"")


if __name__ == "__main__":
    _console()
    if len(sys.argv) < 2 or sys.argv[1] not in ("list", "voices", "show", "bind"):
        raise SystemExit(
            "usage:\n"
            "  python scripts/channels.py list\n"
            "  python scripts/channels.py voices\n"
            "  python scripts/channels.py show <channel-id>\n"
            "  python scripts/channels.py bind <channel-id> <slug>"
        )
    cmd = sys.argv[1]
    if cmd == "list":
        list_channels()
    elif cmd == "voices":
        list_voices()
    elif cmd == "show":
        if len(sys.argv) < 3:
            raise SystemExit("usage: python scripts/channels.py show <channel-id>")
        show(sys.argv[2])
    else:
        if len(sys.argv) < 4:
            raise SystemExit("usage: python scripts/channels.py bind <channel-id> <slug>")
        bind(sys.argv[2], sys.argv[3])
