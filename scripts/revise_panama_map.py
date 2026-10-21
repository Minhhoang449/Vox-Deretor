import json
import sys
from pathlib import Path

project = Path(sys.argv[1])
path = project / "beats.json"
doc = json.loads(path.read_text(encoding="utf-8-sig"))
for beat in doc["beats"]:
    for shot in beat.get("shots", []):
        if beat["id"] + shot["id"] == "B02S01":
            scene = "Sơ đồ giản lược, không theo tỷ lệ: eo đất Panama chạy chéo từ tây-bắc sang đông-nam; biển Caribe ở phía bắc, Thái Bình Dương ở phía nam; kênh nối vùng Colón tây-bắc với Panama City đông-nam, hồ Gatún ở giữa lệch về tây-bắc. Không có đường bờ lặp, đảo giả, nhãn hoặc trị số."
            shot["scene"] = scene
            shot["visual_intent"]["subject"] = scene
            shot["visual_intent"]["representation"] = "original schematic map, not to scale"
            shot["visual_intent"]["framing"] = "diagram"
            shot["visual_intent"]["evidence_boundary"] = "Sơ đồ định hướng khái quát theo ACP, không dùng như bản đồ địa lý đo đạc."
            shot["animation"]["start"] = scene
            shot["animation"]["keyframe"] = scene
            shot["animation"]["end"] = scene
            shot["visual_source"]["reason"] = "Sơ đồ định hướng mới theo nguồn ACP; hình AI trước đó bị sai bố cục địa lý và bị loại."
            shot.pop("keyframe_prompt", None)
            shot.pop("keyframe_prompt_current_hash", None)
            shot.pop("keyframe_prompt_hash", None)
            shot.pop("keyframe_path", None)
            break
path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Updated B02S01 with north/south coasts and the northwest-southeast canal orientation.")
