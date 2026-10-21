# Dùng lại nguyên ảnh cảnh có liên quan

Quyết định của người dùng ngày 2026-10-13: ưu tiên dùng lại **ảnh đã tạo trước đó** khi ảnh vẫn đúng với đoạn kể. Dùng nguyên ảnh gốc; **không cắt cận, không phóng lớn để biến một ảnh thành nhiều góc nhìn**. Quy tắc này thay thế yêu cầu cũ phải tạo một ảnh mới cho mỗi shot. Giữ thiết lập dựng/camera đã duyệt; việc dùng lại ảnh không thêm thao tác cắt hay phóng mới.

## Chọn đoạn phù hợp

- Có thể quay lại ảnh chợ, căn phòng, con đường, bản đồ hoặc giao dịch đã xuất hiện khi câu chuyện trở lại đúng không gian, nhân vật và trạng thái đó.
- Mỗi lần xuất hiện phải giúp đoạn kể hiện tại. Tránh lặp liền nhiều shot giống nhau hoặc dùng một ảnh liên tục chỉ để lấp thời lượng.
- Tạo ảnh mới khi hành động, biểu cảm, trang phục, đạo cụ, địa điểm, thời kỳ, ánh sáng có ý nghĩa trong truyện, nhãn bản đồ hoặc thông tin nhìn thấy thay đổi. Chỉ cùng bối cảnh không đủ để dùng lại ảnh có hành động không phù hợp.
- Ảnh dùng lại giữ nguyên nhân vật và chữ có sẵn. Không thể bỏ người, sửa bảng giá hoặc thay biển hiệu qua chỉ dẫn của shot dùng lại.
- Kiểm tra ảnh với lời kể và phụ đề ở từng lần xuất hiện. Phần mềm kiểm tra tham chiếu, nhân vật và chữ; tính phù hợp của hành động/bối cảnh vẫn cần người lập shot và QA đánh giá.
- Giới hạn shot dùng lại ảnh ở mức tối đa 35% tổng shot của một tập. Tính mỗi shot có `reuse_image_from` một lần chia tổng số shot; số shot dùng lại tối đa là `floor(0.35 × tổng số shot)` (ví dụ tập 100 shot thì tối đa 35 shot dùng lại, còn ít nhất 65 shot cần ảnh mới). Mỗi ảnh gốc chỉ được dùng lại tối đa 2 lần sau lần xuất hiện đầu tiên, tức tối đa 3 lần xuất hiện tổng cộng; tính theo ảnh nguồn gốc cuối cùng, kể cả khi có chuỗi tham chiếu ảnh dùng lại. Character reference và thumbnail là tài sản riêng, không tính vào các giới hạn này. Theo dõi riêng số ảnh gốc và số shot; đừng để giới hạn làm sai nhịp kể hoặc biện minh dùng ảnh không còn phù hợp.

## Khai báo trong beats.json

Shot có ảnh gốc giữ cấu trúc hiện tại. Shot dùng lại thêm `reuse_image_from` là **key của shot nguồn** trong manifest (beat ID ghép với shot ID, ví dụ beat `B01`, shot `A` thành `B01A`) và `reuse_reason` giải thích vì sao nguyên ảnh đó phù hợp. Chỉ tham chiếu shot trong cùng tập. Ảnh đã đăng ký của shot nguồn được dùng trực tiếp; không tạo bản sao. Các tập cũ không có trường này tiếp tục chạy như trước.

Ví dụ shot ở beat `B03` quay lại ảnh nguồn `B01A`:

```json
{
  "id": "A",
  "dur": 7,
  "scene": "Quay lại giao dịch tại quầy gạo đã thấy ở phần đầu khi lời kể nhắc chi phí bữa ăn.",
  "reuse_image_from": "B01A",
  "reuse_reason": "Cùng giao dịch, nhân vật, hàng hóa và biển giá; lời kể đang nhắc lại chi phí đã giới thiệu.",
  "animation": {
    "start": "Giữ đúng trạng thái trong ảnh nguồn.",
    "action": "Giữ nguyên ảnh để người xem đối chiếu với lời kể.",
    "end": "Giữ nguyên trạng thái giao dịch.",
    "camera": "locked-off",
    "continuity": "Dùng nguyên ảnh B01A, giữ nguyên nhân vật, vật phẩm và chữ; không cắt cận hoặc phóng lớn."
  }
}
```

Có thể bỏ `characters`, `in_scene_text`, `text_placement` ở shot dùng lại vì ảnh đã có sẵn các nội dung này. Nếu khai báo nhân vật hoặc chữ thì chúng phải khớp ảnh nguồn. Không đặt `image_text_policy: none` để xóa chữ khỏi ảnh có chữ.

## Xuất, tạo, đăng ký và dựng

1. `python scripts/codex_prompts.py <episode>` kiểm tra các nguồn trước khi ghi prompt. `imagegen/manifest.json` có `assets` cho các ảnh gốc và `shots` cho mọi lần xuất hiện. `image_summary` báo số shot, ảnh gốc và shot dùng lại.
2. Chỉ tạo ảnh trong `assets` có `status: needs_image`; kiểm tra các ảnh `needs_review`. Shot có `action: reuse` không có prompt riêng và không phải yêu cầu tạo ảnh. Các prompt cũ còn trên đĩa không phải danh sách công việc; dùng manifest hiện tại.
3. Dùng Codex imagegen cho ảnh mới và lưu đúng `save_as`. Kiểm tra ảnh nguồn cùng tất cả đoạn kể dùng nó, rồi chạy `--register`. Mọi shot dùng lại nhận đúng đường dẫn/fingerprint của ảnh nguồn, kể cả khi shot nguồn đã có ảnh từ trước.
4. `assemble.py` giải lại nguồn từ `reuse_image_from`, nên đường dẫn ảnh cũ ghi ở shot dùng lại không lấn át ảnh nguồn. Ảnh nguồn thiếu sẽ dừng dựng. Cache render tiếp tục theo nội dung ảnh, camera và thời lượng như trước; thay ảnh nguồn làm các lần sử dụng và chuyển cảnh liên quan được dựng lại.

Không tự ghép những cảnh có vẻ giống nhau bằng tên file hoặc từ khóa. Việc tiết kiệm ảnh được quyết định ở bước lập shot sau khi narration được duyệt; không sửa narration/TTS hoặc video đã giao chỉ để thêm dùng lại ảnh.

## People and representation

Under [visual DNA](visual-dna.md), character-free scenes cannot reuse a full image containing people to remove them. Explicit `people_policy` must agree with the source; anonymous crowds also count as human presence. Omitting cast fields on a reuse shot retains the source image, not an automatic character removal. Different viewpoint, illustration type, visible mechanism or changed-world state needs a suitable new original; identity consistency is not a reason to recycle the same layout.


## Kiểm lại trước dựng — 16/10/2026

Assemble kiểm lại trần số shot/lần dùng ngay khi giải tham chiếu; sau khi đo và phân bổ thời lượng, kiểm cả nội dung file ảnh. Ảnh trùng byte ở đường dẫn khác vẫn tính cùng ảnh gốc, không dùng đổi tên/copy để vượt trần. QA ghi `image-reuse-qa.json`, gồm tỷ lệ thời lượng, lần quay lại cách nhau tối đa một shot khác và yêu cầu xem lại trạng thái với narration. Không thêm shot lấp chỗ để hợp thức hóa tỷ lệ.

Có thể khai báo `visual_state` (chuỗi hoặc object) cho ảnh gốc và shot quay lại. Nếu shot dùng lại khai báo trạng thái thì phải trùng trạng thái đã khai báo của ảnh gốc; khác hoặc thiếu trạng thái nguồn sẽ chặn. Đây là kiểm metadata, không đọc hiểu hành động trong ảnh. Tập cũ thiếu trường này vẫn chạy qua QA; mọi lần dùng lại vẫn cần người xem đối chiếu hành động, bối cảnh, chữ và thông tin nhìn thấy. Khi trạng thái đổi, tạo ảnh mới.

35% là trần số shot, không phải chỉ tiêu phải dùng hết. Tỷ lệ thời lượng và các lần ảnh lặp sát nhau là chỉ dấu cần biên tập, không tự chứng minh nhịp kể tốt/xấu hoặc đặt thêm trần thời lượng bắt buộc.
