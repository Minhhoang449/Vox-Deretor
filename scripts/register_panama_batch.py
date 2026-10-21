import json
import sys
from pathlib import Path

project = Path(sys.argv[1])
beats_path = project / "beats.json"
manifest_path = project / "imagegen" / "manifest.json"
beats = json.loads(beats_path.read_text(encoding="utf-8-sig"))
manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
accepted = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else {"B03S02", "B07S03", "B12S01"}
assets = {item["key"]: item for item in manifest.get("assets", [])}
shots = {}
for beat in beats["beats"]:
    for shot in beat.get("shots", []):
        shots[beat["id"] + shot["id"]] = shot
for key in accepted:
    asset = assets[key]
    shot = shots[key]
    path = project / asset["save_as"]
    if not path.is_file():
        raise SystemExit(f"Missing image for {key}: {path}")
    if shot.get("keyframe_prompt_current_hash") != asset.get("prompt_hash"):
        raise SystemExit(f"Prompt fingerprint mismatch for {key}; leave it for review.")
    shot["keyframe_path"] = str(path)
    shot["keyframe_prompt_hash"] = asset["prompt_hash"]
    asset["existing_image"] = True
    asset["status"] = "ready"
beats_path.write_text(json.dumps(beats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"registered": sorted(accepted), "ready": sum(a.get("status") == "ready" for a in assets.values()),
                  "needs_review": sum(a.get("status") == "needs_review" for a in assets.values()),
                  "needs_image": sum(a.get("status") == "needs_image" for a in assets.values())}, ensure_ascii=False))
