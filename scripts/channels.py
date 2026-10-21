#!/usr/bin/env python3
"""
Bind one episode to an active channel and create its folder on D:\\Video.

Layout: D:\\Video\\<channel destination>\\<slug>\\
Never use the repo out/ folder.

  python scripts/channels.py list
  python scripts/channels.py show vi-sao-noi-nay
  python scripts/channels.py scout vi-sao-noi-nay
  python scripts/channels.py bind vi-sao-noi-nay new-slug --topic "<selected topic>"
  python scripts/channels.py context vi-sao-noi-nay new-slug
"""
import argparse
import json
import os
import re
import sys

from animation_prompts import default_image_text_policy
from visual_policy import load_visual_workflow, episode_style

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHANNELS_FILE = os.path.join(ROOT, "config", "channels.json")
PIPELINE_FILE = os.path.join(ROOT, "config", "pipeline.json")


def _console():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_channel_config():
    with open(CHANNELS_FILE, encoding="utf-8-sig") as f:
        return json.load(f)


def load_channels():
    return load_channel_config()["channels"]


def load_archived_channels():
    """Retired profiles are available for recorded production lookup only."""
    relative = load_channel_config().get("archived_channels_file")
    if not relative:
        return []
    path = os.path.join(ROOT, relative)
    if not os.path.isfile(path):
        return []  # archive not shipped in this checkout; active channels still resolve
    with open(os.path.join(ROOT, relative), encoding="utf-8-sig") as handle:
        profiles = json.load(handle).get("channels", [])
    return [dict(profile, profile_status="archived") for profile in profiles]


def load_visual_dna():
    """Resolve live image direction without changing saved production assets."""
    with open(PIPELINE_FILE, encoding="utf-8-sig") as handle:
        return json.load(handle).get("visual_dna", {})


def load_channel_visual_dna(channel):
    """Apply a channel's style override to the shared visual defaults."""
    return {**load_visual_dna(), **(channel.get("visual_dna_override") or {})}


def load_channel_visual_workflow(channel):
    """Keep the shared renderer while applying channel-specific image style."""
    return {**load_visual_workflow(), **(channel.get("visual_workflow_override") or {})}


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
    selected_slug = slugify(slug)
    current = os.path.normpath(os.path.join(root, selected_slug))
    if not os.path.exists(current):
        for legacy_root in channel.get('legacy_destinations', []):
            legacy = os.path.normpath(os.path.join(legacy_root, selected_slug))
            if os.path.isfile(os.path.join(legacy, 'beats.json')):
                return legacy
    return current


def resolve(selector):
    if any(sep in selector for sep in ("/", "\\")) or selector.lower().startswith("out"):
        raise SystemExit(
            "Episodes are not stored under out/.\n"
            "usage: python scripts/channels.py bind <channel-id> <slug>\n"
            "Folder: D:\\Video\\<channel>\\<slug>"
        )
    key = selector.strip().casefold()
    for channel in [*load_channels(), *load_archived_channels()]:
        names = (channel["id"].casefold(), channel.get("display_name", "").casefold(),
                 *(name.casefold() for name in channel.get('previous_display_names', [])))
        if key in names:
            return channel
    known = ", ".join(channel["id"] for channel in load_channels())
    raise SystemExit(f"Unknown channel {selector!r}. Use one of: {known}")


def list_channels():
    for channel in load_channels():
        print(f"{channel['id']}\t{channel['language']}\t{channel['display_name']}")
        print(f"  {channel['promise']}")


def list_voices():
    """Per-channel clone source: reference audio and transcript in channels.json."""
    print("channel_id\tlanguage\tprofile_id\tprofile_name\treference")
    for channel in load_channels():
        ref = (channel.get("voice_reference") or {}).get("audio", "")
        print(
            f"{channel['id']}\t{channel['language']}\t{channel['voice']}\t"
            f"{channel.get('voice_profile_name', '')}\t{ref}"
        )


def marketing_workflow():
    """Expose the project-scoped specialist without implying tool availability."""
    return {
        "reference": "references/youtube-marketing-integration.md",
        "topic_selection_reference": "references/topic-selection.md",
        "installed_skill": "youtube-marketing",
        "topic_modules": ["ideate", "competitor"],
        "packaging_modules": ["thumbnail", "seo", "metadata"],
        "coordination_reference": "references/script-packaging-coordination.md",
        "concept_modules_before_long_narration": ["thumbnail", "seo"],
        "coordination_policy": "Compare two title/thumbnail/opening treatments and native-market intent before long narration; review actual speech/package together before narration approval; finalize after story lock. Artwork retains narration approval and audio review gates.",
        "evidence_policy": "Missing analytics and keyword volumes remain unknown; no performance forecasts.",
        "delivery_policy": "Local reviewable export; publication requires explicit authorization.",
    }


def scouting_context(selector):
    """Return live discovery guidance without binding or touching an episode."""
    channel = resolve(selector)
    if channel.get("profile_status") == "archived":
        raise SystemExit("This channel is retired. Scout new topics for one of the six active channels.")
    config = load_channel_config()
    dna = config.get("narration_dna", {})
    market = channel.get("youtube_research") or {}
    language = market.get("relevance_language") or channel["language"]
    region = market.get("region_code")
    if not region:
        raise SystemExit("The live channel has no discovery region; resolve its market before searching.")
    from topic_memory import summaries
    remembered = summaries(channel=channel["id"], config=config)
    return {
        "channel_id": channel["id"],
        "display_name": channel["display_name"],
        "language": channel["language"],
        "query_contract": {"query_language": language, "relevance_language": language,
                           "region_code": region},
        "channel_lens": {key: channel.get(key) for key in
                         ("promise", "lanes", "avoid", "story_format", "narration_direction", "writing_contract")},
        "topic_scope": dna.get("topic_scope", {}),
        "question_design": dna.get("question_design", {}),
        "script_packaging_coordination": dna.get("script_packaging_coordination", {}),
        "packaging_direction": channel.get("packaging_direction", {}),
        "marketing_workflow": marketing_workflow(),
        "topic_discovery": config.get("topic_discovery", {}),
        "topic_memory": {
            "total_candidates": len(remembered),
            "recent_candidates": remembered[:12],
            "history_command": f"python scripts/topic_memory.py list --channel {channel['id']}",
            "cross_channel_search_command": "python scripts/topic_memory.py list --query <topic-term>",
            "policy": "Decision provenance, not authoring instructions, verified facts or narration approval. Read full history before rejecting a repeat or reviving a deferred idea.",
        },
        "references": ["references/topic-selection.md", "references/topic-research.md",
                       "references/templates/topic-shortlist.md",
                       "references/topic-memory.md",
                       "references/youtube-marketing-integration.md"],
        "status": "research_context_only",
        "episode_created": False,
        "approval_policy": "Recommendations do not approve narration, bind an episode, or start production.",
    }


def show(selector):
    """Show the current authoring profile, including shared Script DNA."""
    profile = dict(resolve(selector))
    profile["authoring_allowed"] = profile.get("profile_status") != "archived"
    profile["narration_dna"] = load_channel_config().get("narration_dna", {})
    profile["visual_dna"] = load_channel_visual_dna(profile)
    profile["visual_workflow"] = load_channel_visual_workflow(profile)
    profile["marketing_workflow"] = marketing_workflow()
    profile["topic_discovery"] = load_channel_config().get("topic_discovery", {})
    from playlists import channel_playlists
    profile["playlists"] = channel_playlists(profile['id'])
    print(json.dumps(profile, ensure_ascii=False, indent=2))


def _topic_text(value):
    return " ".join(str(value or "").split())


def _validate_episode_identity(doc, channel, slug):
    """Refuse to turn an existing episode into a different project by rebinding."""
    if not isinstance(doc, dict):
        raise SystemExit("beats.json must contain an episode object.")
    slug = slugify(slug)
    recorded = doc.get("episode_context") or {}
    if not isinstance(recorded, dict):
        raise SystemExit("episode_context must be an object; inspect this episode before editing.")
    snapshot = doc.get("channel") or {}
    if not isinstance(snapshot, dict):
        raise SystemExit("channel snapshot must be an object; inspect this episode before editing.")
    for actual in (doc.get("channel_id"), snapshot.get("id"), recorded.get("channel_id")):
        if actual and actual != channel["id"]:
            raise SystemExit("Episode channel mismatch. Use the selected channel's own episode folder.")
    for actual in (doc.get("episode_slug"), recorded.get("episode_slug")):
        if actual and slugify(actual) != slug:
            raise SystemExit("Episode slug mismatch. Create a new slug for a new topic.")
    topic = _topic_text(doc.get("topic"))
    anchor = _topic_text(recorded.get("topic"))
    if topic and anchor and topic.casefold() != anchor.casefold():
        raise SystemExit("Episode topic conflicts with its recorded context. Inspect the brief and handoff; use a new slug for a new topic.")
    return topic or anchor


def _new_story_premise(channel=None):
    dna = load_channel_config().get("narration_dna", {})
    return {
        "format": (channel or {}).get("story_format") or dna.get("default_format", "channel_documentary"),
        "dna_revision": dna.get("revision", ""),
        "editorial_revision": dna.get("editorial_revision", ""),
        "subject": "",
        "period": "",
        "place": "",
        "central_question": "",
        "promise": "",
        "opening": "",
        "evidence_anchors": [],
        "baseline": "",
        "sequence": [],
        "mechanisms": [],
        "turning_points": [],
        "human_stakes": "",
        "answer": "",
        "consequences": [],
        "uncertainty": "",
        "reconstruction_boundaries": "",
        "illustrative_examples": [],
        "optional_scenario": {},
    }


def _authoring_premise(doc, channel=None):
    """Use the current format unless this episode records an explicit exception."""
    premise = doc.get("story_premise") or {}
    if not isinstance(premise, dict):
        raise SystemExit("story_premise must be an object; inspect this episode before drafting.")
    current = _new_story_premise(channel)
    default_format = current["format"]
    if _topic_text(premise.get("exception_reason")):
        # A specific user-requested format stays visible; the live DNA is separate.
        current.update(premise)
    else:
        # Field names overlap between the retired mission and documentary DNA.
        # Renaming only format/revision would relabel an old plot as a new draft.
        same_revision = premise.get("dna_revision") == current["dna_revision"]
        same_format = premise.get("format") == default_format
        same_editorial = premise.get("editorial_revision", "") == current["editorial_revision"]
        if same_revision and same_format and same_editorial:
            current.update({key: value for key, value in premise.items() if key in current})
        else:
            # Keep setting orientation only. The recorded production premise
            # stays intact below for continuity, never as current draft content.
            current.update({key: premise[key] for key in ("period", "place") if key in premise})
        current["format"] = default_format
        current["dna_revision"] = load_channel_config().get("narration_dna", {}).get("revision", "")
    return current


def authoring_context(selector, slug):
    """Read one episode's subject with live writing DNA, never its stale snapshot."""
    channel = resolve(selector)
    project_dir = episode_dir(channel, slug)
    path = os.path.join(project_dir, "beats.json")
    if not os.path.isfile(path):
        raise SystemExit("No episode at this slug. Bind the selected topic first.")
    with open(path, encoding="utf-8-sig") as handle:
        doc = json.load(handle)
    topic = _validate_episode_identity(doc, channel, slug)
    if not topic:
        raise SystemExit("No selected episode topic. Set it with bind <channel-id> <slug> --topic \"<selected topic>\" before drafting.")
    return {
        "channel_id": channel["id"],
        "language": channel["language"],
        "episode_slug": slugify(slug),
        "episode_dir": project_dir,
        "topic": topic,
        "narration_dna": load_channel_config().get("narration_dna", {}),
        "topic_scope": load_channel_config().get("narration_dna", {}).get("topic_scope", {}),
        "question_design": load_channel_config().get("narration_dna", {}).get("question_design", {}),
        "topic_discovery": load_channel_config().get("topic_discovery", {}),
        "editorial_revision": channel.get("editorial_revision", ""),
        "visual_dna": load_channel_visual_dna(channel),
        "visual_workflow": load_channel_visual_workflow(channel),
        "recorded_visual_workflow": doc.get("visual_workflow") or {},
        "recorded_animation_style": episode_style(doc),
        "narration_direction": channel.get("narration_direction", ""),
        "story_format": channel.get("story_format", ""),
        "visual_grammar": channel.get("visual_grammar", ""),
        "image_text_policy": channel.get("image_text_policy", default_image_text_policy()),
        "visual_text_direction": channel.get("visual_text_direction", ""),
        "writing_contract": channel.get("writing_contract", {}),
        "narration_calibration": channel.get("narration_calibration", {}),
        "research_basis": channel.get("research_basis", []),
        "avoid": channel.get("avoid", []),
        "packaging_direction": channel.get("packaging_direction", {}),
        "marketing_workflow": marketing_workflow(),
        "story_premise": _authoring_premise(doc, channel),
        "recorded_story_premise": doc.get("story_premise") or {},
        "recorded_context_policy": (
            "Recorded story is production history, not current writing instructions. "
            "Without an explicit format exception, only a matching live DNA revision "
            "and editorial revision and channel format may supply plot fields to story_premise; an incompatible "
            "or unversioned premise supplies period/place only. Review it before reusing "
            "any opening, sequence, answer, consequence or scenario in a new revision."
        ),
        "identity_documents": [os.path.join(project_dir, name) for name in
                               ("brief.json", "PROJECT_HANDOFF.md")
                               if os.path.isfile(os.path.join(project_dir, name))],
        "production_note": "Current DNA governs new drafts and requested rewrites; existing approved narration requires fresh revision approval.",
    }


def bind(selector, slug, topic=None):
    channel = resolve(selector)
    project_dir = episode_dir(channel, slug)
    path = os.path.join(project_dir, "beats.json")
    existing = os.path.exists(path)
    if channel.get("profile_status") == "archived" and not existing:
        raise SystemExit("This channel is retired. Choose one of the six active channels for a new episode; legacy folders remain available for continuation.")
    if existing:
        with open(path, encoding="utf-8-sig") as f:
            doc = json.load(f)
    else:
        visual_dna = load_channel_visual_dna(channel)
        visual_workflow = load_channel_visual_workflow(channel)
        doc = {
            "project": slugify(slug),
            "topic": "",
            "aspect": "16:9",
            "style": "animation",
            "animation_style": visual_dna.get("default_style", "documentary-realistic"),
            "visual_workflow": visual_workflow,
            "visual_mode": visual_workflow.get("default_visual_mode", "revideo_stills"),
            "narration_dna": load_channel_config().get("narration_dna", {}),
            "visual_dna": visual_dna,
            "story_premise": _new_story_premise(channel),
            "beats": [],
            "narration_approval_required": True,
        }
    selected_topic = _validate_episode_identity(doc, channel, slug)
    if topic is not None:
        requested = _topic_text(topic)
        if not requested:
            raise SystemExit("--topic must name the selected episode topic.")
        if selected_topic and selected_topic.casefold() != requested.casefold():
            raise SystemExit(
                "This folder already belongs to another topic. "
                "Bind the new topic with a new slug; existing narration, research and metadata were not changed."
            )
        if existing and not selected_topic:
            metadata = doc.get("youtube_metadata") or {}
            production_files = ("master-narration.md", "PROJECT_HANDOFF.md", "brief.json")
            if (doc.get("beats") or metadata.get("candidates") or metadata.get("description")
                    or any(os.path.exists(os.path.join(project_dir, name)) for name in production_files)
                    or any(os.path.isdir(os.path.join(project_dir, name)) for name in ("audio", "keyframes", "video"))):
                raise SystemExit(
                    "Existing production has no recorded topic. Inspect its brief/handoff before assigning a subject; "
                    "bind a new slug for a new topic. Existing files were not changed."
                )
        # Preserve recorded spelling on a resume rather than rewriting a subject.
        selected_topic = selected_topic or requested
    doc["topic"] = selected_topic
    doc["episode_context"] = {
        "schema_version": 1,
        "channel_id": channel["id"],
        "episode_slug": slugify(slug),
        "topic": selected_topic,
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
        "clone_prompt": ref.get("prompt", ""),
        "vieneu_voice": ref.get("vieneu_voice", ""),
    })
    doc["pipeline"] = "local"
    doc.setdefault("visual_mode", "revideo_stills")
    doc.setdefault("image_text_policy", channel.get("image_text_policy", default_image_text_policy()))
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
        "playlists": {"primary_id": "", "additional_ids": [], "selection_reason": ""},
        "experiment": {"mode": "thumbnail_and_title", "hypothesis": ""},
    })
    doc['youtube_metadata'].setdefault('playlists', {"primary_id": "", "additional_ids": [], "selection_reason": ""})
    os.makedirs(project_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"bound {channel['id']} ({channel['display_name']}, {channel['language']})")
    print(f"voice {voice['profile_name']}  clone {voice['reference_audio']}")
    print(f"episode {project_dir}")
    print(f"wrote {path}")
    if selected_topic:
        print(f"topic {selected_topic}")
        print(f"Current writing context: python scripts/channels.py context {channel['id']} {slugify(slug)}")
    else:
        print("Choose this episode's topic with --topic before drafting; pilot topics are suggestions only.")
    print("Research this episode before the beat map:")
    print(f"  python scripts/research_youtube.py --channel {channel['id']} --query \"<question>\" --tag {slugify(slug)} --output-dir \"{project_dir}\\research\"")


if __name__ == "__main__":
    _console()
    parser = argparse.ArgumentParser(description="Bind or inspect one channel documentary without reusing another topic.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list")
    subparsers.add_parser("voices")
    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("channel")
    scout_parser = subparsers.add_parser("scout", help="Read live topic-discovery guidance without creating an episode.")
    scout_parser.add_argument("channel")
    bind_parser = subparsers.add_parser("bind")
    bind_parser.add_argument("channel")
    bind_parser.add_argument("slug")
    bind_parser.add_argument("--topic", help="Selected topic/question; a different topic requires a new slug.")
    context_parser = subparsers.add_parser("context")
    context_parser.add_argument("channel")
    context_parser.add_argument("slug")
    args = parser.parse_args()
    if args.command == "list":
        list_channels()
    elif args.command == "voices":
        list_voices()
    elif args.command == "show":
        show(args.channel)
    elif args.command == "scout":
        print(json.dumps(scouting_context(args.channel), ensure_ascii=False, indent=2))
    elif args.command == "context":
        print(json.dumps(authoring_context(args.channel, args.slug), ensure_ascii=False, indent=2))
    else:
        bind(args.channel, args.slug, topic=args.topic)
