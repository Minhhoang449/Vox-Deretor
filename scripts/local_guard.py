"""Stop Atlas calls, and keep local episodes out of the repo out/ folder."""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "out")


def refuse_out_dir(project_dir):
    """Local films are delivered to D:\\Vox-Video\\<channel>\\<episode>, never out/."""
    proj = os.path.normcase(os.path.abspath(project_dir))
    out = os.path.normcase(OUT_DIR)
    if proj == out or proj.startswith(out + os.sep):
        raise SystemExit(
            "Do not write episodes under out/. "
            "Create one with: python scripts/channels.py bind <channel-id> <slug>\n"
            "That folder is D:\\Vox-Video\\<channel>\\<slug>."
        )


def refuse_if_local(doc):
    if doc.get("pipeline") == "local":
        raise SystemExit(
            "pipeline=local: Codex renders stills, Muse.ai animates them, "
            "VoiceStudio speaks the narration. Do not call Atlas. "
            "See references/local-pipeline.md"
        )
