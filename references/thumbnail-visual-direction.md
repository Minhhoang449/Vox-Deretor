# DNA thumbnail — luật studio (Chibi 2D cho mọi kênh)

Revision: `studio-chibi-thumbnail-v4`, cập nhật 22/10/2026 theo quyết định của người dùng ngày 21/10/2026. Kiểm tra cứng nằm ở `scripts/thumbnail_visual_direction.py` (`check_thumbnail_candidate`). Hướng biên tập: [everyday ancient curiosity](everyday-ancient-curiosity.md).

## Luật bắt buộc (bộ nguyên tắc chung cho cả 6 kênh, chốt 22/10/2026)

Tất cả thumbnail là Chibi 2D dễ thương, hài hước, hơi tinh nghịch. Kênh phân biệt nhau bằng bảng màu, bối cảnh và bố cục trong `packaging_direction.thumbnail_identity` (`config/channels.json`).

1. **Một nhân vật Chibi ở giữa khung, chiếm khoảng 40–60% ảnh.** Nét mặt phóng đại, tinh nghịch, đọc ra cảm xúc ngay cả khi ảnh thu nhỏ còn 160 px. *(Chặn tự động: `character_count == 1`, `subject_area_ratio` 0.40–0.60, `character.position = center`, `expression_readable_160px: true`.)*
2. **Một đồ vật chính, đúng hiện vật trong video.** Nhân vật làm một hành động với đồ vật, không chỉ đứng cạnh.
3. **Chữ tối đa 3 từ (tiếng Nhật tối đa 8 ký tự),** không lặp cụm nào của tiêu đề, chỉ bổ sung cho tiêu đề. Từ chức năng ngắn (no, the, of…) không tính là lặp. Câu hỏi đời thường được phép. *(Chặn tự động.)*
4. **Chỉ hứa điều video trả lời,** thường là con số hoặc câu hỏi chính của video; ưu tiên số cụ thể hoặc câu hỏi đời thường ("1.2 KM AWAY", 「苦すぎる木の実」, "NO WELL?!"). Ghi `text_source_line`; con số phải có trong câu đó.
5. **Tối đa 3 màu chính, nền đơn giản,** nhân vật nổi trên nền. Không đặt chữ ở góc dưới bên phải (nhãn thời lượng che). *(Chặn tự động: `main_colors` 1–3 màu, `text_position` khác bottom-right.)*
6. **Mỗi video có 2 phương án A và B,** chỉ khác chữ hoặc biểu cảm, cả hai cùng qua luật 3. So CTR ở mốc 48 giờ; bản cao hơn rõ thì giữ. Nếu CTR sau 48 giờ thấp rõ so với CTR trung bình của chính kênh đó, đổi thumbnail và tiêu đề trước, chưa sửa nội dung. Ngưỡng này sẽ được thay bằng con số đo được sau khoảng 5 video, ghi trong [post-publish-tracking.md](post-publish-tracking.md); mọi lần thử A/B cũng ghi vào file đó. *(Chặn tự động: `variants` đúng 2 mục nhãn A/B.)*
7. **Không chế giễu người thật, không thêm chi tiết nguồn không có.** Mỗi chi tiết nhìn thấy được ghi trong `details` kèm `source`. Không sơ đồ, mũi tên, bản đồ tuyến hay mặt cắt trên thumbnail. Ảnh bảo tàng chỉ dùng khi có `licence` (Open Access) và `licence_url`/`source_url`.

### Ảnh bìa Shorts

Chọn khung Chibi tinh nghịch nhất trong ảnh của tập (biểu cảm phóng đại, một chi tiết tinh nghịch). Dọc 9:16, mặt nhân vật nằm trong vùng an toàn ở giữa. Chữ tối đa 3 từ, không lặp tiêu đề Short và không lặp chữ thumbnail của video dài. Khung phải thể hiện đúng chủ đề của chính Short đó.


### Bài học từ bài thử bữa trưa (22/10/2026)

- **Chữ và mọi đồ vật/món ăn được vẽ phải có trong lời dẫn hoặc bảng nguồn.** Ví dụ "ONIONS" bị loại vì nguồn chỉ ghi ngũ cốc, rau và cá. Ghi các thứ được vẽ trong `depicted_items`; nếu có thêm nguồn ngoài lời dẫn thì ghi vào `source_table`.
- **Cấm đồ hiện đại** trong prompt và ảnh: giày thể thao, quần jeans, khóa kéo, nhựa, chai thủy tinh, điện thoại, đồng hồ đeo tay, kính, nĩa kim loại.
- **Vẽ đúng loại hiện vật/thức ăn:** hạt lúa mì emmer hoặc lúa mạch (không vẽ bông lúa mì hiện đại hay ổ bánh mì); hạt トチ (dẻ ngựa Nhật) có vết sẹo lớn màu nhạt (không vẽ quả sồi hay hạt dẻ).
- Cảm xúc phải gắn với tình huống trong tập (đã kiểm tra từ trước).

### Kiểm tra 160 px thật

Khi candidate có `thumbnail_path`, `check_thumbnail_image` thu ảnh về 160×90 (Pillow, LANCZOS), lưu bản xem trước `<tên>.160px.png` cạnh ảnh gốc, rồi chặn nếu:
- toàn ảnh quá nhạt (độ lệch chuẩn độ sáng < 32);
- vùng chữ khai báo ở `text_position` có độ chênh sáng (phân vị 95 trừ phân vị 5) < 90.

Khi không có `thumbnail_path`, vẫn bắt buộc `expression_readable_160px: true`.

**Giới hạn:** phép kiểm tra cho cùng kết quả mỗi lần chạy, nhưng nó không đọc được chữ, không nhận ra khuôn mặt và không đánh giá được biểu cảm. Nó chỉ loại những ảnh rõ ràng quá phẳng để đọc ở 160 px, nên người vẫn phải xem bản xem trước. Kiểm tra từ trong chữ là heuristic:
- Mọi từ không phải từ chức năng, số hay đơn vị đều được coi là danh từ cụ thể, và phải có trong lời dẫn hoặc `source_table` (khớp số ít/số nhiều đơn giản).
- Chỉ áp dụng cho chữ Latin; chữ Nhật không được kiểm tra.
- Chỉ chạy khi có lời dẫn.

## Trường candidate bắt buộc

`thumbnail_text`, `text_source_line`, `character` (`{description, position: "center"}`), `emotion`, `character_count`, `subject_area_ratio`, `expression_readable_160px`, `main_colors`, `text_position`, `variants [{label: "A"|"B", thumbnail_text, emotion}]`, `thumbnail_path` (khuyến nghị; thay cho `expression_readable_160px`), `depicted_items`, `source_table` (tùy chọn), `details [{detail, source}]`, và `museum_images [{licence, licence_url}]` nếu có dùng.

Chạy: `python scripts/thumbnail_visual_direction.py candidates.json --language en`.

## Kỹ thuật

- 1280×720, 16:9; nội dung quan trọng cách mép 6%; chừa góc dưới phải cho nhãn thời lượng.
- Tối đa 2 dòng chữ, đủ lớn ở cỡ 320×180; kiểm tra dấu tiếng Việt và kana/kanji bằng mắt.
- Không logo, watermark, collage giấy xé hay tài liệu lưu trữ giả. Không hình sốc, không hứa điều video không trả lời.

## Áp dụng

1. Sau khi khóa truyện, ghi tối đa ba candidate trong `youtube_metadata`; mỗi candidate khác nhau về cảm xúc, hành động hoặc khoảnh khắc của nhân vật trung tâm.
2. Chạy kiểm tra cứng; sửa đến khi PASS rồi mới tạo ảnh bằng Codex imagegen.
3. Kiểm tra ảnh thật ở 1280×720 và 320×180. Sau đăng, đọc CTR cùng thời lượng xem và giữ chân.

YouTube guidance: [thumbnail and title tips](https://support.google.com/youtube/answer/12340300), [Test & Compare](https://support.google.com/youtube/answer/13861714).
