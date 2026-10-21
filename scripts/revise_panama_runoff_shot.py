import json
import sys
from pathlib import Path

project = Path(sys.argv[1])
path = project / "beats.json"
doc = json.loads(path.read_text(encoding="utf-8-sig"))
for beat in doc["beats"]:
    for shot in beat.get("shots", []):
        if beat["id"] + shot["id"] == "B08S04":
            scene = "Mưa và dòng chảy mặt trên sườn đồi nhiệt đới; nước chảy trên bề mặt đất theo rãnh nhỏ xuống suối rồi về hồ. Không thể hiện nước ngầm, mặt cắt hoặc mũi tên dữ liệu."
            shot["scene"] = scene
            shot["visual_intent"]["subject"] = scene
            shot["visual_intent"]["representation"] = "photorealistic AI reconstruction"
            shot["visual_intent"]["framing"] = "landscape wide"
            shot["animation"]["start"] = scene
            shot["animation"]["keyframe"] = scene
            shot["animation"]["end"] = scene
            shot.pop("keyframe_prompt", None)
            shot.pop("keyframe_prompt_current_hash", None)
            shot.pop("keyframe_prompt_hash", None)
            shot.pop("keyframe_path", None)
            break
path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Updated B08S04 to show surface runoff only; rejected the groundwater cutaway candidate.")
