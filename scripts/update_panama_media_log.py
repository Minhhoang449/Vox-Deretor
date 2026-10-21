import json
import sys
from pathlib import Path

project = Path(sys.argv[1])
beats = json.loads((project / "beats.json").read_text(encoding="utf-8-sig"))
manifest = json.loads((project / "imagegen" / "manifest.json").read_text(encoding="utf-8-sig"))
candidate_path = project / "research" / "ai-reconstruction-candidates.json"
candidate_doc = json.loads(candidate_path.read_text(encoding="utf-8-sig"))
shots = {beat["id"] + shot["id"]: shot for beat in beats["beats"] for shot in beat.get("shots", [])}
jobs = {asset["key"]: asset for asset in manifest.get("assets", [])}
notes = {
    "B03S02": "Toàn cảnh hồ và đảo rừng, không có tuyên bố đây là ảnh vệ tinh hoặc vị trí cụ thể.",
    "B07S03": "Minh họa ba bể tiết kiệm và dòng nước; chỉ dùng để giải thích khái niệm, không chứng minh bố trí công trình chính xác.",
    "B12S01": "Mặt cắt tàu trong buồng âu giúp giải thích mớn nước; cấu kiện không phải bản vẽ kỹ thuật.",
    "B02S05": "Phong cảnh đồi và các vùng nước dùng làm cảnh minh họa địa hình, không phải địa điểm đo đạc cụ thể.",
    "B14S10": "Toàn cảnh âu và hồ gọi lại tuyến nước; không dùng làm bản đồ hoặc bố trí chính xác.",
    "B08S04": "Mưa và dòng chảy trên mặt đất; phiên bản được giữ không thể hiện dòng ngầm hay quan hệ địa chất đo đạc.",
    "B03S05": "Tàu đi trên hồ Gatún trong cảnh tái dựng tổng quát, không xác định con tàu/ngày.",
    "B04S01": "Tàu tiến vào buồng âu trong cảnh tái dựng tổng quát, không dùng làm bằng chứng vị trí/cấu tạo cụ thể.",
    "B10S05": "Bờ hồ lộ ra trong cảnh mực nước thấp; gốc cây là chi tiết nền, không dùng để kết luận về sử dụng đất.",
    "B02S02": "Mặt cắt giản lược để giải thích đất cao giữa hai bờ biển, không phải khảo sát địa hình.",
    "B03S01": "Sơ đồ tuyến có hồ ở giữa và âu hai đầu; dùng để định hướng, không khẳng định tọa độ/hình dạng chính xác.",
    "B02S01": "Sơ đồ định hướng bắc–nam và tuyến tây-bắc–đông-nam; đối chiếu thêm bản đồ ACP khi QA, không dùng làm bản đồ đo đạc.",
    "B04S04": "Sơ đồ cắt lớp các buồng âu và mực nước khác nhau; không phải bản vẽ kỹ thuật.",
    "B06S02": "Sơ đồ khái niệm cống dẫn và hướng dòng vào buồng âu, gắn nguồn thiết kế ACP.",
    "B08S05": "Toàn cảnh mặt hồ và đảo rừng tái dựng, không nhận là ảnh hồ cụ thể.",
    "B06S03": "Cutaway cống dẫn nước để giải thích nguyên lý; không coi mũi tên/kiến trúc là bản vẽ ACP.",
    "B07S08": "Cảnh sơ đồ âu/bể tiết kiệm nước mang tính khái niệm; không khẳng định bố trí chính xác của một âu cụ thể.",
    "B11S09": "Cửa và dòng xả ở công trình chứa nước là minh họa chung, không khẳng định điểm lấy nước ACP cụ thể.",
    "B05S07": "Tàu đi qua mặt hồ trong cảnh tái dựng rộng; không xác định tàu hoặc ngày.",
    "B07S05": "Bể tiết kiệm và âu là minh họa khái niệm, không nhận là bố trí chính xác của một công trình.",
    "B11S07": "Toàn cảnh hồ chứa dùng làm minh họa, không phải ảnh mực nước đo đạc.",
    "B12S07": "Tàu trong buồng âu dùng để thể hiện quy mô tương đối, không nhận là ảnh tư liệu.",
    "B03S07": "Bờ rừng và mặt hồ nội địa dùng làm minh họa hồ Gatún; không nhận là ảnh vị trí đo đạc cụ thể.",
    "B06S04": "Sơ đồ dòng nước qua cống/van vào buồng âu; cấu kiện là diễn giải khái niệm, không phải bản vẽ kỹ thuật.",
    "B07S02": "Mặt cắt buồng âu minh họa nước đi vào khi cửa đóng; hình học chi tiết không phải bản vẽ ACP.",
    "B09S04": "Tuyến ống đô thị tổng quát, không gắn địa chỉ hoặc khẳng định là tuyến cấp nước cụ thể.",
    "B01S02": "Tàu hàng trên hồ trong cảnh minh họa rộng; không xác định tàu hoặc thời điểm.",
    "B01S03": "Tàu trên hồ nhấn mạnh quan hệ quy mô; cảnh không thể hiện âu tàu và không nhận là ảnh sự kiện.",
    "B01S04": "Mặt cắt minh họa chênh cao mặt biển và hồ qua các buồng âu; hình học không theo tỷ lệ khảo sát.",
    "B02S03": "Tái dựng nhìn từ trên cao để định hướng tuyến kênh qua eo đất; không dùng làm bản đồ chính xác hoặc dữ liệu địa lý.",
    "B02S04": "Sơ đồ đối chiếu tuyến kênh và vòng Nam Mỹ; đường đi chỉ định hướng, không đo khoảng cách.",
    "B02S06": "Mặt cắt địa hình khái quát để thấy đất cao giữa hai đại dương; không biểu diễn độ cao đo đạc.",
    "B03S03": "Minh họa nguyên lý đập đất và hồ chứa; không khẳng định vật liệu hay cấu tạo chính xác của đập Gatún.",
    "B03S04": "Tái dựng vùng địa hình ngập khi hình thành hồ; ranh nước không phải đường biên lịch sử chính xác.",
    "B03S06": "Sơ đồ tuyến đi từ biển qua âu lên hồ rồi tiếp tục; bố cục không phải bản đồ tỷ lệ.",
    "B03S08": "Mặt cắt khái quát biển–âu–hồ để giải thích độ cao mặt nước; không coi số bậc/chi tiết là bản vẽ chính xác.",
    "B04S05": "Sơ đồ nguyên lý nước qua cống bên dưới vào buồng âu; không xác nhận cấu trúc kỹ thuật cụ thể.",
    "B04S06": "Tái dựng góc nhìn trên cao dọc các buồng âu và tàu; không phải ảnh tư liệu của một lượt tàu cụ thể.",
    "B05S01": "Tàu container trên hồ Gatún là cảnh tái dựng, không xác định tàu hoặc thời điểm.",
    "B05S02": "Sơ đồ hướng từ hồ qua các âu về phía Thái Bình Dương; không định hướng chính xác theo tọa độ.",
    "B05S04": "Đối chiếu mặt hồ rộng và kênh đào hẹp để thấy khác biệt hình thái; không khẳng định kích thước đo đạc.",
    "B05S05": "Tàu rời vùng hồ/tiến về âu trong cảnh tái dựng tổng quát; không nhận là tuyến tàu cụ thể.",
    "B05S06": "Sơ đồ tàu qua hồ và xuống các bậc âu phía Thái Bình Dương; tuyến không theo tỷ lệ.",
    "B05S08": "Mặt cắt giải thích từ hồ xuống biển phía Thái Bình Dương; không có số liệu cao độ đo đạc.",
    "B06S01": "Cửa âu minh họa hai mực nước khác nhau khi cửa đóng; cấu kiện không phải bản vẽ kỹ thuật.",
    "B06S06": "Sơ đồ hai buồng sau cân bằng có cùng một mặt nước nằm ngang; hình học minh họa, không phải bản vẽ kỹ thuật.",
    "B06S07": "Cận cảnh cửa và bản lề công nghiệp tái dựng; không nhận là cấu kiện/kích thước của một cửa cụ thể.",
    "B07S01": "Sơ đồ khái niệm nước từ hồ nâng tàu qua buồng âu rồi nước thoát khỏi hệ thống; không theo tỷ lệ.",
    "B07S04": "Đối chiếu âu thông thường với bể tiết kiệm; bố trí minh họa, không phải sơ đồ đo đạc.",
    "B07S06": "Sơ đồ bể tiết kiệm thể hiện một phần tái sử dụng và phần nước còn lại rời chu trình; không dùng làm định lượng.",
    "B07S07": "Cận cảnh mực nước và thành buồng minh họa thể tích; không suy ra kích thước đo đạc từ ảnh.",
    "B07S09": "Tái dựng hệ bể cạnh âu để giải thích ý tưởng tiết kiệm; không khẳng định bố trí của công trình cụ thể.",
    "B07S10": "Sơ đồ so sánh khái niệm phần nước giữ lại và phần dùng trong chu trình; không đặt con số.",
    "B07S11": "Sơ đồ tuyến nước kết nối hồ, tàu, âu và điểm xả để nhấn mạnh nước không được giữ toàn bộ; không theo tỷ lệ.",
    "B08S01": "Sơ đồ lưu vực nước mưa về hồ trung tâm; ranh giới lưu vực và hướng dòng là khái niệm, không phải dữ liệu GIS.",
    "B08S03": "Sơ đồ mưa–dòng chảy–hồ và lấy nước; nhà máy/đường ống là minh họa, không định vị cơ sở thật.",
    "B08S07": "Sơ đồ giản lược lấy nước, lắng/lọc và phân phối; không khẳng định tuyến cụ thể cho mọi đô thị.",
    "B08S08": "Bể lắng tái dựng kiểu nhà máy nhiệt đới; không nhận là ảnh một cơ sở ACP cụ thể.",
    "B08S09": "Sơ đồ khái quát tách nhánh nước sinh hoạt và nhánh vận hành kênh; không khẳng định chúng dùng chung một đường ống.",
    "B09S01": "Sơ đồ vùng dân cư và hồ ở mức khái niệm; không thể hiện ranh giới phục vụ chính xác.",
    "B09S02": "Infographic về tỷ lệ dân số được phục vụ theo phạm vi tài liệu; biểu tượng không phải bộ đếm chính xác từng người.",
    "B09S03": "Sơ đồ phân biệt phục vụ theo hệ thống với lượng nước tới từng hộ; không dùng làm bản đồ mạng lưới.",
    "B09S05": "Sơ đồ hồ–xử lý–mạng đô thị ở mức khái niệm; nét ranh đứt chỉ thể hiện giới hạn dữ liệu, không phải ranh dịch vụ.",
    "B09S06": "Cảnh vòi và bồn chứa trong đô thị là minh họa chung, không đại diện cho mọi hộ Panama.",
    "B09S07": "Sơ đồ tách tuyến nước cho âu và tuyến nước sinh hoạt để nhắc phạm vi phát biểu; không khẳng định mọi mạng thực tế.",
    "B10S01": "Biểu đồ hai cột không chữ: trung bình 73 năm chuẩn hóa 100, năm 2023 là 74,4 vì thấp hơn 25,6%; không thể hiện số đo mm hoặc phân bố theo tháng.",
    "B10S03": "Cảnh quan hồ trong mùa khô với bờ lộ ra; AI minh họa, không xác định mực nước cụ thể hoặc đường ranh hạn hán.",
    "B10S04": "Sơ đồ quan hệ mưa thấp–dòng vào hồ giảm–dự trữ chịu áp lực; không gắn số liệu giả định.",
    "B10S07": "Bờ hồ lộ ra dưới ánh sáng mùa khô, minh họa chung chứ không phải ảnh đo đạc năm 2023.",
    "B10S06": "Sơ đồ định tính cho thấy mưa ít hơn làm giảm dòng chảy vào hồ và để lộ bờ; không có chuỗi đo theo ngày/tháng.",
    "B10S08": "Sơ đồ ba thanh tỷ lệ 7:10:3 cho dòng vào, dòng ra kết hợp và thiếu hụt mỗi ngày theo báo cáo ACP năm 2023; không phải cân bằng hiện tại.",
    "B11S01": "Sơ đồ khái quát hồ làm bộ đệm giữa mưa và các nhánh sử dụng; không theo tỷ lệ lưu lượng.",
    "B11S02": "Cảnh hồ lộ bờ dùng làm tái dựng mực thấp; không xác định mực đo hay ngày cụ thể.",
    "B11S03": "Sơ đồ tách dòng phục vụ đô thị và vận tải; vị trí cơ sở/ống chỉ minh họa.",
    "B11S04": "Đồ họa quyết định vận hành mang tính khái niệm; không mô phỏng bảng điều độ hay dự báo ACP.",
    "B11S05": "Tháp lấy nước và ống dẫn bờ hồ là tái dựng chung; dòng được thể hiện đi vào cửa hút, không phải cửa xả hay vị trí ACP cụ thể.",
    "B11S06": "Sơ đồ mùa mưa/mùa khô minh họa hồ làm bộ đệm thời gian; không có số đo hoặc đường mực nước lịch sử.",
    "B11S08": "Toàn cảnh sơ đồ hóa hồ, âu và nhu cầu đô thị; các mũi tên nêu quan hệ khái niệm, không phải vị trí hay luồng ống chính xác.",
    "B11S10": "Sơ đồ minh họa nhiều nhu cầu cùng phụ thuộc vào nguồn trữ, không mô tả tranh chấp hoặc phân bổ định lượng.",
    "B11S11": "Sơ đồ khái niệm mưa–hồ–âu–đô thị, không dùng chuỗi số liệu hoặc dự báo; công trình và mũi tên không định vị thực địa.",
    "B12S02": "Sơ đồ khoảng hở dưới đáy tàu chỉ giải thích mớn nước; mũi tên không biểu thị trị số/giới hạn đã xác nhận.",
    "B12S03": "Sơ đồ hai tàu xếp nối đuôi trong một buồng minh họa tandem lockage; không phải ảnh tư liệu hay thước tỷ lệ.",
    "B12S04": "Tái dựng cận thân tàu trong buồng âu; không dùng mực nước hoặc góc máy để suy ra tải trọng.",
    "B12S05": "Sơ đồ âu và các bể cạnh bên giải thích khả năng giữ lại nước; kiến trúc không phải mặt bằng công trình chính xác.",
    "B12S06": "So sánh trực quan thân tàu và độ sâu chìm; không đặt trị số mớn nước hoặc giới hạn vận hành.",
    "B12S08": "Minh họa dòng giữa hai làn/buồng để giải thích cross-filling; mũi tên và hình học không phải bản vẽ ACP.",
    "B12S09": "Bố cục nhiều ô tóm tắt các cách tiết kiệm nước; quan hệ biểu đồ là khái niệm, không theo tỷ lệ hay trị số.",
    "B12S10": "Tái dựng tàu trong hệ âu; bố cục không nhằm xác nhận số làn hoặc cấu hình thực tế tại thời điểm cụ thể.",
    "B12S11": "Ảnh tổng quát tàu trong buồng âu; không phải ảnh một lượt tàu tư liệu.",
    "B12S12": "Bố cục so sánh nhiều cơ chế âu/tàu; phần hình giải thích là khái niệm, không phải bản vẽ đo đạc.",
    "B12S13": "Sơ đồ mặt cắt mực nước và cống/bể cạnh buồng, chỉ giải thích hướng dòng, không định lượng.",
    "B13S01": "Sơ đồ nhiệt/đường mưa El Niño mang tính định hướng; không được dùng làm bản đồ dữ liệu khí hậu có tọa độ hoặc trị số.",
    "B13S02": "Cảnh hồ mùa khô tái dựng; bờ lộ ra không đại diện ngày, năm hay mực đo cụ thể.",
    "B13S03": "Sơ đồ định tính mưa–hồ–nhu cầu; dấu hỏi biểu thị giới hạn dự báo, không phải xác suất/chuỗi đo.",
    "B13S04": "Đối chiếu mùa mưa và mùa ít mưa bằng cảnh quan khái quát; không phải ảnh hai thời điểm đo cùng vị trí.",
}
for key, review in notes.items():
    item_path = jobs[key]["save_as"]
    prompt_path = project / jobs[key]["prompt_file"]
    prompt = prompt_path.read_text(encoding="utf-8")
    candidate_item = next((item for item in candidate_doc.get("items", []) if item.get("path") == item_path), None)
    if candidate_item is None:
        candidate_item = {
            "path": item_path,
        }
        candidate_doc.setdefault("items", []).append(candidate_item)
    candidate_item.update({
        "status": "registered" if jobs[key]["status"] == "ready" else "needs_review",
        "label": shots[key]["visual_source"]["label"],
        "visual_role": ("Source-derived explanatory diagram; the 2023 value is calculated as 100 - 25.6 = 74.4 on a normalized index, not a millimeter series." if key == "B10S01" else "Source-derived explanatory diagram using the ACP 2023 snapshot (7, 10 and 3 hm³/day)." if key == "B10S08" else "AI-generated illustrative reconstruction; not evidence of a named event, facility, date or measured condition."),
        "prompt_file": jobs[key]["prompt_file"],
        "prompt": prompt,
        "review": review,
    })
rejected = candidate_doc.setdefault("rejected", [])
if not any(item.get("asset") == "B08S04 pre-revision groundwater-cutaway candidate" for item in rejected):
    rejected.append({
    "asset": "B08S04 pre-revision groundwater-cutaway candidate",
    "generated_on": "2026-10-19",
    "reason": "Image showed arrows and water below ground, which conflicted with the narration's surface-runoff passage. Replaced because it changed the mechanism, not for a minor visual detail.",
    })
if not any(item.get("asset") == "B02S01 first map candidate" for item in rejected):
    rejected.append({
        "asset": "B02S01 first map candidate",
        "generated_on": "2026-10-19",
        "reason": "Map composition reversed/misrepresented the requested Panama geography and duplicated coast-like shapes; replaced by a clearer north/south schematic.",
    })
if not any(item.get("asset") == "B08S09 treatment-and-lock composite candidate" for item in rejected):
    rejected.append({
        "asset": "B08S09 treatment-and-lock composite candidate",
        "generated_on": "2026-10-19",
        "reason": "Composite layout placed treatment works, homes and a canal lock together, which could imply an unsupported physical route/proximity; excluded from the episode.",
    })
if not any(item.get("asset") == "B06S06 first candidate" for item in rejected):
    rejected.append({
        "asset": "B06S06 first candidate",
        "generated_on": "2026-10-19",
        "reason": "Hai phía cửa hiện mực nước khác nhau dù shot yêu cầu mực nước đã cân bằng trước khi mở. Loại vì minh họa ngược cơ chế, không phải sai khác nhỏ.",
    })
if not any(item.get("asset") == "B09S02 first map candidate" for item in rejected):
    rejected.append({
        "asset": "B09S02 first map candidate",
        "generated_on": "2026-10-19",
        "reason": "The highlighted local service area implied a geographic boundary the national-level population-share source does not establish. Replaced with an abstract share diagram.",
    })
if not any(item.get("asset") == "B10S01 first AI chart candidate" for item in rejected):
    rejected.append({
        "asset": "B10S01 first AI chart candidate",
        "generated_on": "2026-10-19",
        "reason": "The generated month-by-month rainfall profile was invented; ACP source supports a cumulative deficit of 25.6% versus the 73-year average, not those monthly values. Replace with a source-derived aggregate comparison.",
    })
if not any(item.get("asset") == "B10S06 first AI chart candidate" for item in rejected):
    rejected.append({
        "asset": "B10S06 first AI chart candidate",
        "generated_on": "2026-10-19",
        "reason": "The AI chart invented a time series of rainfall bars and line values that were not in the sourced episode evidence. Replace with a qualitative mechanism diagram, not synthetic measurements.",
    })
if not any(item.get("asset") == "B11S05 first intake candidate" for item in rejected):
    rejected.append({
        "asset": "B11S05 first intake candidate",
        "generated_on": "2026-10-19",
        "reason": "Ảnh thể hiện nước xả qua đập tràn, sai cơ chế của shot lấy nước vào hệ thống; thay vì sửa lỗi hình thức, ảnh mới thể hiện cửa hút và ống dẫn vào bờ.",
    })
if not any(item.get("asset") == "B11S11 first seasonal chart candidate" for item in rejected):
    rejected.append({
        "asset": "B11S11 first seasonal chart candidate",
        "generated_on": "2026-10-19",
        "reason": "Ảnh tự thêm cột và đường chuỗi theo mùa không có trong nguồn; thay bằng sơ đồ định tính không có trục hoặc trị số.",
    })
if not any(item.get("asset") == "B12S03 first side-by-side ship candidate" for item in rejected):
    rejected.append({
        "asset": "B12S03 first side-by-side ship candidate",
        "generated_on": "2026-10-19",
        "reason": "Hai tàu lớn đặt cạnh nhau trong buồng âu gây hiểu sai khả năng tandem lockage; thay bằng hai tàu xếp nối đuôi trong một buồng.",
    })
if not any(item.get("asset") == "B13S03 first seasonal chart candidate" for item in rejected):
    rejected.append({
        "asset": "B13S03 first seasonal chart candidate",
        "generated_on": "2026-10-19",
        "reason": "Ảnh đầu tự tạo các đường và cột khí hậu theo mùa không có trong nguồn; thay bằng sơ đồ nhân quả định tính có dấu hỏi cho phần bất định.",
    })
candidate_path.write_text(json.dumps(candidate_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

ready = sum(asset.get("status") == "ready" for asset in manifest.get("assets", []))
review = sum(asset.get("status") == "needs_review" for asset in manifest.get("assets", []))
pending = sum(asset.get("status") == "needs_image" for asset in manifest.get("assets", []))
handoff = project / "PROJECT_HANDOFF.md"
handoff.write_text(f"""# Project handoff — Kênh đào Panama và hồ Gatún

## Trạng thái hiện tại — cập nhật 19/10/2026

Episode mới đã bind cho kênh Vì Sao Nơi Này, tiếng Việt. Chủ đề được người dùng chọn ngày 18/10/2026. Lời dẫn draft 1 có SHA-256 `ed1267049230edb485c960f9ff0976d418b08539ebea79ef67147cc493dff4f`; người dùng yêu cầu triển khai ảnh. 14 WAV VieNeu v3 Turbo, tốc độ gốc 1.0, pause 0.8 giây, tổng 903.8 giây (15:03). Không đổi lời dẫn/TTS; chưa chọn BGM.

- Nghiên cứu chủ đề: `research/episode-brief.md`, `research/source-ledger.md`, `research/marketing-research.md`. Báo cáo quét YouTube tiếng Việt/VN ngày 18/10 có bản lưu theo tag tập tại `research/youtube-market-scan-2026-10-18-panama-ho-gatun-nang-tau-cap-nuoc.md`.
- Review copy narration: `review/narration/review.html`, `audio-review.wav`. Trạng thái nghe trong export vẫn `pending`; không tự ghi thành đã duyệt.
- Người dùng yêu cầu toàn ảnh tĩnh, không dùng video Montage. Các clip đã tìm trước đó không được gán vào shot. Ảnh Pexels cũ vẫn được lưu làm tư liệu nhưng không dùng trong shot map mới.
- Shot map: `pipeline: local`, `visual_mode: hybrid` chỉ để đưa nhãn disclosure lên ảnh; không có shot video. Có 120 shot/903.8 giây, trung bình 7.53 giây, mỗi shot 3–10 giây. Kế hoạch hiện dùng lại 0 ảnh; trần chính sách tối đa 42/120 shot, nhưng không ép dùng hết.
- Hình ảnh: {ready} ảnh khớp prompt đã đăng ký; {review} ảnh có trong thư mục nhưng cần xem xét prompt/fingerprint; {pending} ảnh gốc còn phải tạo. Các ảnh photorealistic đều là minh họa AI, không chứng minh sự kiện, cơ sở, ngày hoặc mực nước cụ thể; label `Tái dựng bằng AI`. Sơ đồ được gắn nguồn ACP và label `Sơ đồ minh họa`.
- QA đã loại candidate B08S04 đầu vì nó mô tả dòng ngầm thay vì dòng chảy mặt, và loại bản đồ B02S01 đầu vì bố cục địa lý sai. Ảnh chỉ được tạo lại khi sai cơ chế/địa lý cốt lõi; không tạo lại vì khác biệt nhỏ.
- QA trực quan 9 ảnh có sẵn ngày 19/10: 8 ảnh nhìn chung đúng vai trò cảnh gốc; riêng B04S02 mở cửa trước dù mô tả shot cần hai cửa đóng nên chưa đạt trạng thái. Prompt fingerprint của cả 9 chưa có, vì thế review vẫn cần được ghi nhận theo pipeline thay vì giả định prompt đã khớp.
- Reuse candidate đã đối chiếu với các shot còn thiếu: B10S02 → B13S02 (hồ lộ bờ mùa khô); B01S01 → B14S03 và B14S06 (tàu trên hồ Gatún, echo mở đầu/kết). Nếu áp dụng sau narration approval sẽ có 3/120 shot dùng lại, B01S01 xuất hiện tổng cộng ba lần, đều trong giới hạn policy. Sáu ảnh còn lại không khớp các shot pending dạng sơ đồ/khí hậu; chưa ép dùng.
- Chưa đủ ảnh cho 120 shot, chưa hoàn tất captions, nhạc hoặc render. Không render trong lượt triển khai ảnh này.

## Bước tiếp theo

1. Tiếp tục tạo các ảnh còn thiếu theo `imagegen/manifest.json`, rồi kiểm tra registration/crop/label và reuse.
2. Chọn BGM, hoàn thành captions và QA hình/audio trước khi render toàn ảnh.

Không đọc hay khôi phục V2. Không đổi chủ đề hoặc lời dẫn đã khóa.
""", encoding="utf-8")
print(json.dumps({"ready": ready, "needs_review": review, "needs_image": pending,
                  "registered_log_items": len(candidate_doc.get("items", []))}, ensure_ascii=False))
