from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path


PROJECT = Path(sys.argv[1])
BEATS = PROJECT / "beats.json"
doc = json.loads(BEATS.read_text(encoding="utf-8-sig"))

# A 120-shot all-still plan gives this 903.8-second narration an average hold
# of 7.53 seconds while keeping every shot inside the configured 3-10s range.
counts = [4, 6, 8, 6, 8, 7, 11, 10, 7, 8, 11, 13, 11, 10]
assert sum(counts) == 120

visuals = {
    "B01": [
        "Toàn cảnh tàu container đang nổi trên mặt hồ Gatún giữa các đảo rừng nhiệt đới; cảnh tái dựng khái quát, không gắn tàu với sự kiện cụ thể.",
        "Tàu hàng nhìn chếch từ xa trên vùng nước hồ rộng, nhấn mạnh mặt nước phẳng và bờ rừng thấp.",
        "Quan hệ quy mô giữa con tàu, mặt hồ nước ngọt và đường chân trời rừng; không thể hiện âu tàu.",
        "Hình cắt lớp khái quát mặt biển và hồ Gatún cao hơn, đặt câu hỏi về việc nâng tàu và dùng nước chung.",
    ],
    "B02": [
        "Sơ đồ định hướng eo đất Panama giữa biển Caribe ở phía bắc và Thái Bình Dương ở phía nam; sơ đồ khái quát, không theo tỷ lệ.",
        "Mặt cắt địa hình khái quát cho thấy phần đất cao nằm giữa hai bờ biển.",
        "Tuyến kênh băng qua eo đất được thể hiện trên bản đồ giản lược, không thêm số đo chưa kiểm chứng.",
        "Đối chiếu bằng sơ đồ giữa tuyến qua kênh và đường vòng quanh Nam Mỹ; khoảng cách không đo theo tỷ lệ.",
        "Cận cảnh sườn đồi nhiệt đới và đường phân thủy để giải thích vì sao đào rãnh không làm đất tự hạ xuống.",
        "Sơ đồ cao độ: mực nước đại dương ở hai đầu và vùng đất cao ở giữa, không gắn nhãn độ cao chính xác.",
    ],
    "B03": [
        "Sơ đồ vị trí hồ Gatún trong tuyến kênh Panama, nối các âu và đoạn kênh; ghi rõ là sơ đồ khái quát.",
        "Toàn cảnh mặt hồ Gatún và các đảo có rừng, tái dựng phong cảnh hiện nay.",
        "Mặt cắt đập đất và hồ chứa ở mức giải thích nguyên lý, không mô tả cấu tạo chính xác của đập Gatún.",
        "Sơ đồ khái quát vùng đất bị ngập khi hình thành hồ, không vẽ ranh giới lịch sử giả chính xác.",
        "Tàu hàng đi giữa các bờ hồ xanh, thể hiện hồ là một đoạn của tuyến hàng hải.",
        "Sơ đồ tuyến kênh chuyển từ âu tàu lên mặt hồ cao rồi tiếp tục qua eo đất.",
        "Cảnh bờ rừng và mặt nước rộng cho biết hồ chứa là một vùng nước nội địa chứ không phải kênh bê tông hẹp.",
        "Mặt cắt khái quát từ biển lên âu tàu rồi đến hồ, nhấn mạnh mặt nước làm đường nâng tàu.",
    ],
    "B04": [
        "Tàu hàng tiến vào âu Gatún từ phía Caribe, cảnh minh họa khái quát.",
        "Tàu nằm trong buồng âu giữa hai cửa đóng, không thể hiện chuyển động mực nước.",
        "Cửa âu thép lớn và tường bê tông nhìn từ phía trong buồng, minh họa cấu kiện chứ không đo kích thước.",
        "Sơ đồ hai buồng âu với hai mực nước khác nhau, cửa ngăn cách ở giữa.",
        "Mặt cắt giải thích đường nước từ hồ vào buồng âu qua cống bên dưới, là sơ đồ nguyên lý.",
        "Tàu trong chuỗi buồng âu nhìn từ trên cao, cho thấy các bậc nước kế tiếp nhau.",
    ],
    "B05": [
        "Tàu container băng qua vùng hồ rộng Gatún, tái dựng hiện đại không xác định tàu hoặc ngày.",
        "Sơ đồ hướng đi của kênh từ hồ Gatún về phía Thái Bình Dương, không theo tỷ lệ.",
        "Toàn cảnh tàu đi qua một đoạn đào trong địa hình đồi xanh, không khẳng định vị trí chính xác.",
        "Đối chiếu mặt nước hồ rộng với kênh hẹp giữa hai bờ đã đào, dạng minh họa giải thích.",
        "Tàu nhìn từ sau khi rời hồ và tiến về khu vực âu phía Thái Bình Dương.",
        "Sơ đồ tuyến tàu đi qua hồ rồi xuống các bậc âu phía Thái Bình Dương.",
        "Phong cảnh hồ với tàu nhỏ trong khung rộng, lấy địa hình làm chủ thể.",
        "Sơ đồ mặt cắt độ cao từ hồ về phía Thái Bình Dương, không gắn số liệu chưa dẫn nguồn.",
    ],
    "B06": [
        "Cửa âu đóng giữ hai mực nước khác nhau ở hai phía; hình minh họa cơ chế.",
        "Sơ đồ cặp cửa và cống dẫn nước trong kết cấu âu tàu, nguyên lý giản lược.",
        "Mặt cắt buồng âu cho thấy cống dẫn nước nằm trong kết cấu, không mô phỏng chi tiết kỹ thuật đo đạc.",
        "Sơ đồ van kiểm soát dòng nước vào hoặc ra buồng âu, các mũi tên có hướng rõ ràng.",
        "Tàu đứng yên trong buồng âu kín, mặt nước ổn định trong một thời điểm.",
        "Đối chiếu hai ngăn âu trước khi mở cửa: mực nước cần cân bằng, sơ đồ giải thích.",
        "Cận cảnh cơ cấu cửa lớn bên thành âu như một cấu kiện công nghiệp, không giả vờ là ảnh chi tiết thực tế.",
    ],
    "B07": [
        "Sơ đồ một chu trình âu tàu lấy nước hồ để nâng tàu, phần nước thoát ra biển được thể hiện rõ.",
        "Mặt cắt buồng âu và dòng nước chảy vào khi cửa đóng, minh họa nguyên lý.",
        "Sơ đồ các bể tiết kiệm nước bên cạnh buồng âu mới, thể hiện một phần nước được giữ lại.",
        "Đối chiếu buồng âu thường và buồng có bể tiết kiệm, không đưa ra tỷ lệ chưa nêu nguồn.",
        "Tàu trong buồng âu với các bể phụ ở cạnh được biểu diễn trong cutaway giản lược.",
        "Sơ đồ dòng nước có phần được tái sử dụng và phần vẫn rời hệ thống qua chu trình.",
        "Cận cảnh mặt nước và tường âu giúp giải thích thể tích buồng gắn với lượng nước.",
        "Sơ đồ mưa, hồ chứa, âu tàu và đại dương theo dòng nước một chiều có nhánh tiết kiệm.",
        "Toàn cảnh bể tiết kiệm nước bên cạnh một âu mới, hình minh họa không gán địa điểm cụ thể.",
        "Sơ đồ so sánh khái niệm giữa nước dùng cho chu trình và nước được giữ lại, không đặt con số.",
        "Hình kết nối tàu, hồ và cửa xả để củng cố rằng chu trình không kín tuyệt đối.",
    ],
    "B08": [
        "Bản đồ khái quát lưu vực kênh đào Panama với hướng nước mưa về hồ Gatún và Alajuela, không vẽ ranh giới chi tiết.",
        "Mưa rơi trên sườn rừng nhiệt đới và chảy thành suối, cảnh tái dựng minh họa quá trình tự nhiên.",
        "Sơ đồ lưu vực: mưa, dòng chảy, hồ chứa và điểm lấy nước, không gắn vị trí nhà máy chính xác.",
        "Mặt cắt đất và dòng chảy mặt từ đồi xuống hồ, minh họa quan hệ thủy văn.",
        "Toàn cảnh hồ chứa nhiệt đới được nhìn từ cao, không nhận diện là một cảnh thực cụ thể.",
        "Nhà máy xử lý nước cạnh vùng hồ và cây xanh, ảnh tái dựng chung không định danh cơ sở.",
        "Sơ đồ các công đoạn lấy nước, lắng lọc và phân phối, không khẳng định mọi đô thị dùng cùng tuyến.",
        "Bể lắng của một nhà máy xử lý nước kiểu nhiệt đới, tái dựng AI không phải cơ sở ACP cụ thể.",
        "Sơ đồ khái quát nhánh nước cấp cho sinh hoạt và nhánh vận hành kênh, không ám chỉ một đường ống chung.",
        "Cận cảnh công trình xử lý và ống dẫn như minh họa hạ tầng, không gắn nhãn địa điểm.",
    ],
    "B09": [
        "Sơ đồ hồ chứa và các vùng dân cư được cấp nước ở mức khái quát, không vẽ phạm vi phục vụ chính xác.",
        "Đồ họa con số ‘hơn một nửa dân số’ kèm chú thích phạm vi theo tài liệu ACP, không diễn giải thành từng hộ.",
        "Sơ đồ phân biệt dân số được hệ thống phục vụ với lượng nước mỗi hộ thực nhận.",
        "Một tuyến ống đô thị mang tính minh họa, không gắn địa chỉ hay người dân cụ thể.",
        "Sơ đồ hồ chứa – xử lý – mạng lưới đô thị với giới hạn dữ liệu được ghi chú.",
        "Cảnh sinh hoạt lấy nước trong đô thị ở mức chung, không đại diện cho mọi hộ Panama.",
        "Đồ họa chú thích nguồn ACP và giới hạn của câu ‘hơn một nửa’, không thêm phần trăm khác.",
    ],
    "B10": [
        "Đồ thị lượng mưa lưu vực năm 2023 so với mức trung bình lịch sử theo chuỗi ACP, trục và giai đoạn phải theo nguồn.",
        "Hồ chứa với bờ lộ ra trong mùa khô, tái dựng AI, không phải ảnh lưu trữ của năm 2023.",
        "Bản đồ khái quát hồ và lưu vực trong điều kiện khô, không tô ranh giới hạn hán đo đạc.",
        "Đồ họa chuỗi mưa thấp hơn – dòng vào hồ giảm – dự trữ chịu áp lực, nêu là quan hệ được tài liệu mô tả.",
        "Phong cảnh sườn hồ mùa khô với mực bờ thấp, không dùng vết nứt đất cường điệu.",
        "Sơ đồ lượng mưa và dòng chảy vào hồ theo thời gian, không tự tạo số liệu.",
        "Mặt hồ và rừng nhiệt đới dưới ánh sáng mùa khô, cảnh minh họa AI.",
        "Đồ thị nguyên bản từ dữ liệu ACP (chỉ dựng sau khi nhập đúng trị số, đơn vị, kỳ so sánh và nguồn).",
    ],
    "B11": [
        "Sơ đồ hồ chứa làm bộ đệm giữa mưa theo mùa và các nhu cầu hằng ngày.",
        "Hồ chứa mực nước thấp tái dựng, dùng để minh họa dự trữ chứ không đo mực nước thực.",
        "Sơ đồ dòng vào hồ, lượng nước phục vụ đô thị và nhu cầu kênh trong cùng hệ thống.",
        "Đồ họa quyết định vận hành: dự trữ, dự báo dòng vào và nhu cầu, không giả làm bảng điều độ ACP.",
        "Cảnh công trình lấy nước hồ mang tính tổng quát, không định danh vị trí.",
        "Sơ đồ bể nước như bộ đệm thời gian giữa mùa mưa và mùa ít mưa.",
        "Đối chiếu một giai đoạn có dòng vào cao và một giai đoạn thấp bằng sơ đồ khái quát, không đặt số.",
        "Hồ, âu tàu và đô thị trong một sơ đồ hệ thống, chỉ thể hiện các mối phụ thuộc đã được nêu.",
        "Cận cảnh cửa lấy nước hồ như một điểm nối giữa trữ lượng và sử dụng.",
        "Sơ đồ nhấn mạnh các nhu cầu cùng phụ thuộc vào nguồn trữ, không vẽ xung đột giữa nhóm người.",
        "Đồ họa tổng hợp mưa, trữ lượng, nhu cầu và điều hành theo mùa, minh họa khái niệm.",
    ],
    "B12": [
        "Mặt cắt thân tàu qua buồng âu cho thấy mớn nước là phần thân chìm dưới mặt nước.",
        "Sơ đồ khoảng hở giữa thân tàu và đáy luồng, không đặt trị số giới hạn chưa xác nhận.",
        "Đối chiếu hình dáng hai tàu khác kích thước trong cùng buồng âu, sơ đồ giải thích không theo tỷ lệ.",
        "Cận cảnh mực nước quanh thân tàu trong buồng, không hàm ý tải trọng đo đạc.",
        "Sơ đồ buồng âu và bể tiết kiệm nước với hướng dòng chảy rõ ràng.",
        "Mặt cắt giải thích thể tích buồng liên quan đến kích thước và độ chìm của tàu.",
        "Tàu container trong buồng âu nhìn từ trên cao để làm rõ bề rộng tương đối.",
        "Đồ họa các yếu tố vận hành: kích thước buồng, mớn nước, mực nước và hạn chế luồng.",
        "Sơ đồ khác biệt giữa lượng nước của chu trình và khối lượng hàng trên tàu.",
        "Tàu đi qua âu mới với bể tiết kiệm nước, cảnh tái dựng không mô phỏng hoạt động cụ thể.",
        "Đồ họa lượng nước qua từng bậc âu, không dùng tỷ lệ nếu chưa gắn với dữ liệu nguồn.",
        "Mặt cắt thân tàu, đáy buồng và mực nước như mô hình kỹ thuật giải thích.",
        "Sơ đồ tổng hợp giới hạn tàu và cách thiết kế bể góp phần giảm nước ngọt dùng cho lượt qua.",
    ],
    "B13": [
        "Sơ đồ El Niño và lượng mưa khu vực, thể hiện tác động năm cụ thể theo mô tả ACP chứ không phải quy luật mọi năm.",
        "Phong cảnh hồ trong mùa khô tái dựng, không mô tả một ngày hay năm đo đạc cụ thể.",
        "Đồ họa chuỗi khí hậu – mưa – dòng chảy – nhu cầu theo mùa với phần bất định được ghi rõ.",
        "Đối chiếu biểu tượng mùa mưa và mùa khô ở lưu vực, không dự báo chính xác.",
        "Bản đồ khái quát vùng nhiệt đới Panama và lưu vực, không dùng ranh giới dự báo.",
        "Biểu đồ mưa và nhu cầu theo mùa khi có đủ dữ liệu ACP, giữ nguyên đơn vị và kỳ đo.",
        "Sơ đồ phân biệt một đợt El Niño cụ thể với xu hướng khí hậu dài hạn.",
        "Toàn cảnh rừng, mây và mặt hồ cho thấy bối cảnh khí hậu, không biểu diễn nguyên nhân trực tiếp.",
        "Đồ họa các nguồn bất định: mưa, biến thiên theo mùa, nhu cầu đô thị và vận hành.",
        "Sơ đồ gắn điều kiện khô năm 2023 vào bối cảnh cụ thể, không biến thành dự báo chắc chắn.",
        "Hình kết nối hồ chứa với nhu cầu nước trong các mùa, nhấn mạnh phụ thuộc vào lượng mưa.",
    ],
    "B14": [
        "Sơ đồ hành trình một con tàu từ Đại Tây Dương, qua âu, hồ Gatún, rồi xuống Thái Bình Dương.",
        "Sơ đồ dòng nước từ lưu vực vào hồ, qua chu trình âu và phần dùng cho sinh hoạt theo hệ thống riêng.",
        "Tàu trên mặt hồ Gatún tái dựng, hình gọi lại nghịch lý phần mở đầu.",
        "Mặt cắt tổng hợp biển – âu – hồ – âu – biển, không theo tỷ lệ.",
        "Đồ họa hai chức năng của hồ chứa: nâng tàu và góp nguồn nước cho dân cư theo ACP.",
        "Phong cảnh hồ, bờ rừng và tàu hàng trong khung rộng, cảnh kết luận minh họa.",
        "Sơ đồ dòng nước cho thấy mưa và dự trữ là điều kiện giới hạn của cả hai chức năng.",
        "Đồ họa nhắc lại các giới hạn: chu trình không kín, số dân phục vụ không nói lên từng hộ.",
        "Sơ đồ một hệ thống chung với các nhánh sử dụng, không vẽ cạnh tranh giả định giữa người và tàu.",
        "Toàn cảnh khái quát kênh, hồ và tàu để kết thúc bằng cơ chế nơi chốn.",
    ],
}

# Six currently reviewed photorealistic reconstructions; originals are copied
# into canonical keyframe names after this plan is written.
existing = {
    "B01S01": "lake_ship_ai_reconstruction.png",
    "B04S02": "lock_chamber_ai_reconstruction.png",
    "B08S06": "water_treatment_ai_reconstruction.png",
    "B04S03": "panama_lock_chamber_illustrative.png",
    "B10S02": "panama_reservoir_low_water_illustrative.png",
    "B08S10": "panama_treatment_illustrative.png",
    "B05S03": "panama_cut_channel_illustrative.png",
    "B06S05": "panama_lock_gates_closed_illustrative.png",
    "B08S02": "panama_watershed_rain_illustrative.png",
}

assert set(visuals) == {beat["id"] for beat in doc["beats"]}
assert all(len(visuals[beat["id"]]) == count for beat, count in zip(doc["beats"], counts))

doc["pipeline"] = "local"
doc["visual_mode"] = "hybrid"
doc["animation_style"] = "documentary-realistic"
doc["style"] = "photorealistic-documentary-stills"
doc["visual_dna"] = {
    "revision": "documentary-visual-v3-imagegen-stills",
    "reference": "references/visual-dna.md",
    "default_style": "documentary-realistic",
    "style_name": "Photorealistic documentary stills + explanatory graphics",
    "subject_selection": "Use the selected channel's visual grammar and the actual narration span.",
    "character_presence": "People serve supported action, scale or experience; natural human proportions; no mandatory protagonist.",
    "consistency": "Generate photorealistic documentary stills matched in geography, period, materials, lighting, color and texture; distinguish reconstruction from source evidence.",
    "scene_options": "Photorealistic AI-generated still reconstructions, explanatory maps, cross-sections and diagrams; no video clips or montage.",
    "prompt_policy": "Use Codex imagegen for original stills after narration approval and audio review. Do not use Montage or search for video. Keep exact localized labels and visible cast references when relevant.",
    "review": "Review generated images for factual grounding, reconstruction disclosure, crop, continuity and explanatory value. Prompt quality alone does not establish visual accuracy.",
}
doc["visual_workflow"] = {
    "revision": "imagegen-stills-v1",
    "reference": "references/imagegen-stills.md",
    "source_order": "imagegen_stills",
    "retrieval_tool": "Codex imagegen",
    "providers": [],
    "default_visual_mode": "revideo_stills",
    "generated_still_style": "documentary-realistic",
    "source_plan_required": False,
    "existing_episode_policy": "User explicitly requested image-only revision; no video clips or Montage.",
}
doc["visual_bible"] = {
    "style": "Photorealistic documentary still reconstructions for scenes; simple, uncluttered explanatory graphics for maps and mechanisms. No imitation of a publisher or animation studio.",
    "palette": "Restrained humid tropical greens, concrete gray, natural water tones and neutral daylight. Keep map and diagram colors functional and consistent.",
    "world": "Contemporary Panama Canal, Lake Gatún, the isthmus and associated water system. Generic reconstructions must not claim an exact facility, ship, date or measured water level.",
    "film_language": "Place-led explanation: orient with geography, show the real system or supported state, then use a sourced schematic for hidden processes. The narration is voice-over; no presenter character.",
    "scale_rules": "Keep ships, lock walls and reservoirs at plausible relative scale. Maps are labeled as schematic unless copied from a cited source. Avoid unsupported precise boundaries, depths or values.",
    "continuity_rules": "Keep the Caribbean side north of the canal and Pacific side south in explanatory maps; Gatún Lake is a broad inland reach between lock systems. Separate water supply for people from water used in navigation where the evidence does.",
}

total = float(sum(float(b.get("narration_dur") or 0) for b in doc["beats"]))
for beat, count in zip(doc["beats"], counts):
    beat.pop("clip_path", None)
    beat.pop("source_in_seconds", None)
    beat.pop("visual_source", None)
    old_duration = float(beat.get("narration_dur") or 0)
    durations = [old_duration / count] * count
    # Keep sum exact despite float serialization.
    durations[-1] = old_duration - sum(durations[:-1])
    shots = []
    for i, scene in enumerate(visuals[beat["id"]], 1):
        sid = f"S{i:02d}"
        key = beat["id"] + sid
        is_diagram = scene.startswith(("Sơ đồ", "Mặt cắt", "Đồ họa", "Đối chiếu", "Bản đồ"))
        source_url = (
            "https://pancanal.com/en/design-of-the-locks/" if beat["id"] in {"B04", "B06", "B07", "B12"}
            else "https://pancanal.com/cuenca-hidrografica/" if beat["id"] in {"B02", "B03", "B05", "B08", "B09", "B10", "B11", "B13", "B14"}
            else "https://pancanal.com/agua/"
        )
        shot = {
            "id": sid,
            "dur": round(durations[i-1], 5),
            "scene": scene,
            "visual_intent": {
                "purpose": f"Làm rõ ý riêng của đoạn {beat['title']}.",
                "subject": scene,
                "representation": "original explanatory diagram" if is_diagram else "photorealistic AI reconstruction",
                "framing": "diagram" if is_diagram else "wide view",
                "evidence_boundary": "Tái dựng/sơ đồ minh họa theo nguồn đã nghiên cứu; không phải bản ghi sự kiện hoặc bản vẽ đo đạc.",
            },
            "people_policy": "none",
            "characters": [],
            "image_text_policy": "none",
            "animation": {
                "start": scene,
                "keyframe": scene,
                "action": "Giữ một trạng thái tĩnh để làm rõ quan hệ được lời dẫn giải thích.",
                "end": scene,
                "camera": "auto",
                "continuity": "No physical change is added by camera motion. Keep maps schematic and AI reconstructions explicitly illustrative.",
            },
            "visual_source": {
                "decision": "ai_reconstruction" if not is_diagram else "diagram",
                "reason": "Ảnh tĩnh/sơ đồ được thiết kế riêng theo đoạn lời dẫn; không dùng footage hoặc Montage.",
                "label": "Sơ đồ minh họa" if is_diagram else "Tái dựng bằng AI",
                "factual_role": "illustrative",
                "source_url": source_url if is_diagram else "",
                "accessed_on": "2026-10-19",
            },
        }
        if key in existing:
            shot["keyframe_path"] = str(PROJECT / "keyframes" / f"kf_{key}.png")
        shots.append(shot)
    beat["shots"] = shots

doc["visual_plan"]["planning_note"] = (
    "120 still-image shots across 903.8 seconds, averaging 7.53 seconds; all shots are 3-10 seconds. "
    "Image reuse is optional and capped at floor(0.35 * shot count)=42 shots; no reuse is assumed unless individually justified."
)
BEATS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

candidate_path = PROJECT / "research" / "ai-reconstruction-candidates.json"
candidate_doc = json.loads(candidate_path.read_text(encoding="utf-8-sig"))
new_assets = [
    ("keyframes/kf_B04S03.png", "Tàu hàng nhìn chếch từ xa trên vùng nước hồ rộng, nhấn mạnh mặt nước phẳng và bờ rừng thấp. Generic AI reconstruction, not a specific vessel or event. No text, labels, logos or watermark.", "Một tàu container trong buồng âu rộng, hai cánh cửa lớn ở tiền cảnh; minh họa bối cảnh âu, không dùng để chứng minh kết cấu hoặc kích thước chính xác."),
    ("keyframes/kf_B10S02.png", "A wide view of a tropical reservoir shoreline at visibly low water, a natural exposed bank and forested hills beneath hazy dry-season light; keep it restrained and plausible, no dramatic drought cracks, no boats stranded, no people. Generic illustrative reconstruction, not a documented photograph, exact reservoir, water-level measurement or date. No text, labels, signs, logos, watermarks, maps or borders.", "Bờ hồ thấp và dải đất lộ ra nhìn hợp lý, nhưng chỉ là ảnh tái dựng minh họa; không dùng làm bằng chứng mực nước cụ thể năm 2023."),
    ("keyframes/kf_B08S10.png", "A modern water treatment plant beside a tropical freshwater reservoir: settling basins, filtration buildings, pipes and a small pump building integrated with a green wooded shoreline, viewed from an elevated wide angle in clear humid daylight. No people or signs. Generic illustrative reconstruction, not a named ACP plant or exact location. No text, numbers, logos, watermarks, maps or borders.", "Ảnh cho thấy tổ hợp xử lý nước và hồ theo yêu cầu chung; một số bố trí thiết bị có thể không đúng cơ sở thật nên chỉ dùng minh họa, không mô tả tuyến nước ACP."),
    ("keyframes/kf_B05S03.png", "A container ship moving through a cut channel in lush tropical Central American hills on the Panama Canal, the banks visibly excavated and maintained, no lock chamber in frame. Natural daylight, credible ship scale, quiet editorial realism. Generic AI reconstruction, not a specific date or exact canal section. No text, logos, flags, signs, map, collage, border, or watermark.", "Cảnh tàu trong đoạn đào giữa đồi giúp phân biệt với hồ và buồng âu; không xác định đoạn kênh thật cụ thể."),
    ("keyframes/kf_B06S05.png", "A large cargo ship held in a concrete lock chamber with the water calm at one level, viewed from above and slightly behind, massive closed lock gates ahead, lush green tropical hills in the distance. Depict one static moment; do not show water rising or simultaneous open/closed gates. Generic Panama Canal lock reconstruction, no exact lock, vessel or event claim. No text, labels, signs, logos, flags, watermarks, map, collage, border.", "Cảnh tĩnh tàu bên trong buồng âu, không dùng làm bằng chứng về trạng thái điều khiển cửa hoặc máy móc cụ thể."),
    ("keyframes/kf_B08S02.png", "Rain clouds over a forested tropical watershed in Panama, visible rain falling onto steep green slopes and runoff joining a small stream that flows toward a reservoir inlet. Natural, restrained, plausible hydrology, no flood, no measured water level, no dramatic disaster. Generic illustration, not a specific recorded event or exact watershed. No text, labels, signs, logos, watermark, map or border.", "Mưa, dòng chảy và hồ liên kết theo cảnh minh họa; không nhận là lưu vực ACP cụ thể hoặc mưa của một ngày thực."),
]
for path, prompt, review in new_assets:
    if not any(item.get("path") == path for item in candidate_doc.get("items", [])):
        candidate_doc.setdefault("items", []).append({
            "path": path, "status": "assigned_to_shot_needs_registration",
            "label": "Tái dựng bằng AI", "visual_role": "Illustrative only; not an event record or exact facility/location claim.",
            "prompt": prompt, "review": review,
        })
candidate_doc["created_on"] = "2026-10-19"
candidate_path.write_text(json.dumps(candidate_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

handoff = PROJECT / "PROJECT_HANDOFF.md"
handoff_text = f"""# Project handoff — Kênh đào Panama và hồ Gatún

## Trạng thái hiện tại — cập nhật 19/10/2026

Episode mới đã bind cho kênh Vì Sao Nơi Này, tiếng Việt. Chủ đề được người dùng chọn ngày 18/10/2026. Lời dẫn draft 1 có SHA-256 `ed1267049230edb485c960f9ff0976d418b08539ebea79ef67147cc493dff4f`; người dùng cho phép tiếp tục sản xuất ảnh. 14 WAV VieNeu v3 Turbo, tốc độ gốc 1.0, pause 0.8 giây, tổng 903.8 giây (15:03). Không đổi lời dẫn/TTS trong lượt này; chưa chọn BGM.

- Nguồn nghiên cứu: `research/episode-brief.md`, `research/source-ledger.md`, `research/marketing-research.md`; YouTube discovery dùng tiếng Việt/region VN và chỉ làm discovery.
- Review copy narration: `review/narration/review.html`, `audio-review.wav`. Trạng thái nghe trong export vẫn `pending`; không tự ghi thành đã duyệt.
- Người dùng yêu cầu toàn ảnh tĩnh, không dùng video Montage. Các clip Montage từng kiểm tra ở lượt trước không được gán vào shot; hai ảnh Pexels vẫn nằm ở thư mục lưu trữ nhưng không được dùng trong shot map mới.
- Shot map đã chuyển sang `pipeline: local`, `visual_mode: hybrid` chỉ để hỗ trợ nhãn disclosure trên ảnh; trong shot map không có video clips. Có 120 shot theo 903.8 giây lời dẫn (trung bình 7.53 giây/shot), mọi shot trong khoảng 3–10 giây. Trần dùng lại ảnh là `floor(0.35 × 120) = 42` shot; chưa ép chỉ tiêu tái sử dụng.
- Có 9 ảnh AI tái dựng đã đặt vào keyframes cho cảnh tàu/hồ, buồng âu, đoạn kênh đào, bờ hồ mùa khô, mưa lưu vực và nhà máy xử lý nước. Tất cả là minh họa tổng quát, không chứng minh sự kiện, cơ sở, ngày hoặc mực nước cụ thể; cần nhãn `Tái dựng bằng AI` khi dựng.
- Chưa xuất `imagegen/manifest.json` sau shot-map mới, chưa đăng ký fingerprint prompt, chưa tạo đủ ảnh gốc cho 120 shot, chưa captions/render/QA chuỗi hình. Ảnh hiện có không tạo lại chỉ vì sai khác chi tiết nhỏ; chỉ thay khi sai chủ thể, địa điểm/mối quan hệ, trạng thái hoặc cơ chế cốt lõi.

## Bước tiếp theo

1. Xuất prompt/manifest cho shot map toàn ảnh và tiếp tục tạo ảnh gốc theo nhóm cảnh; dùng sơ đồ có nguồn cho địa lý/cơ chế cần độ chính xác.
2. Kiểm ảnh theo mục đích cảnh, giữ nhãn tái dựng/sơ đồ, cập nhật đăng ký tài sản mà không ghi sai fingerprint prompt.
3. Hoàn thành ảnh, chọn BGM, captions và QA hình/audio trước khi render; không dùng Montage video.

Không đọc hay khôi phục V2. Không đổi chủ đề hoặc lời dẫn đã khóa.
"""
handoff.write_text(handoff_text, encoding="utf-8")

print(json.dumps({"shot_count": sum(len(b["shots"]) for b in doc["beats"]), "narration_seconds": total,
                  "mean_shot_seconds": total / 120, "max_reuse": math.floor(120 * 0.35),
                  "visual_mode": doc["visual_mode"], "existing_assets": list(existing)}, ensure_ascii=False))
