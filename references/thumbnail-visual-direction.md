# DNA thumbnail — luật studio (Chibi 2D cho mọi kênh)

Revision: `studio-chibi-thumbnail-v4`, cập nhật 22/10/2026 theo quyết định của người dùng ngày 21/10/2026. Kiểm tra cứng nằm ở `scripts/thumbnail_visual_direction.py` (`check_thumbnail_candidate`). Hướng biên tập: [everyday ancient curiosity](everyday-ancient-curiosity.md).

## Luật bắt buộc

1. **Chibi 2D cho cả 6 kênh.** Kênh phân biệt nhau bằng bảng màu, bối cảnh và bố cục thumbnail lấy từ `packaging_direction.thumbnail_identity` trong `config/channels.json`, không bằng phong cách vẽ khác. Không dùng tranh tường, washi, bản vẽ kỹ thuật hay ảnh hiện thực cho thumbnail mới.
2. **Một nhân vật có cảm xúc ở giữa khung.** Nhân vật Chibi đang làm hoặc phản ứng với đúng việc có nguồn trong tập. Thumbnail không bao giờ chỉ là đồ vật, bản đồ hay sơ đồ. Nhân vật không được kéo theo chi tiết không có nguồn.
3. **Chữ ≤3 từ (số và đơn vị tính 2 từ; tiếng Nhật ≤8 ký tự),** là một khẳng định thật gây bất ngờ lấy từ kịch bản, ghi `text_source_line` (câu lời dẫn chứa nó; con số phải có trong câu đó). Không phải câu hỏi về đồ vật. Không lặp bất kỳ từ nội dung nào của tiêu đề (tiếng Nhật: cụm 2 ký tự kanji/kana).
4. **Không vẽ chi tiết nguồn không hỗ trợ.** Mỗi chi tiết nhìn thấy được ghi trong `details` kèm `source`. Phần hiện vật hỏng hoặc chỉ là diễn giải phải vẽ đúng là hỏng/diễn giải. Lỗi cũ không lặp lại: kéo đá, khăn nemes trên người lao động, giá bình trông như miệng giếng, con lừa chỉ là khả năng.
5. **Không sơ đồ, mũi tên, bản đồ tuyến hay mặt cắt trên thumbnail.** Sơ đồ chỉ dùng cho một cơ chế cốt lõi, trong video.
6. **Ảnh bảo tàng** chỉ được dùng khi có trường `licence` (Open Access đã kiểm tra) và `licence_url`/`source_url`.

## Trường candidate bắt buộc

`thumbnail_text`, `text_source_line`, `character` (mô tả hoặc `{description, position: "center"}`), `emotion`, `details [{detail, source}]`, và `museum_images [{licence, licence_url}]` nếu có dùng.

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
