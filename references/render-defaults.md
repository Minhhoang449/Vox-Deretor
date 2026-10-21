# Render mặc định — bàn giao cho agent ở chat mới

Cập nhật theo lựa chọn của người dùng ngày 2026-10-12. Đọc sau `local-pipeline.md` khi tiếp tục một tập hoặc chuẩn bị render. Cấu hình chạy thực tế nằm trong `../config/pipeline.json`; kiểm tra cấu hình và mã nguồn nếu hướng dẫn bị lệch.

Lựa chọn bổ sung ngày 2026-10-13: dùng lại **nguyên ảnh đã tạo trước đó** ở các shot liên quan, theo `image-reuse.md`. Không cắt cận hoặc phóng lớn để tạo góc nhìn mới. Đặt `reuse_image_from` và `reuse_reason` ở bước lập shot; chỉ tạo ảnh mới khi tình huống hoặc thông tin nhìn thấy cần thay đổi. Đây là dùng lại ảnh nguồn, khác với dùng lại cache video đã encode.

## Các lựa chọn đã chốt

| Hạng mục | Mặc định hiện tại |
|---|---|
| Render camera và chuyển cảnh từ ảnh | FFmpeg trực tiếp, `renderer.stills_renderer: ffmpeg` |
| Encoder GPU | `h264_nvenc`, preset `p4`, CQ `20` |
| Render shot song song | 2 worker, hiện lấy từ `revideo.workers` |
| Chuyển động camera | `renderer.stills_camera_policy: balanced` |
| Zoom phụ khi vào shot | `renderer.stills_incoming_zoom: 0.0` |
| Chuyển cảnh | Dissolve: 0.46 giây trong beat, 0.68 giây giữa beat |
| Text trong ảnh mới | `image_text_policy: contextual` |
| Phụ đề | Cụm từ tĩnh được đốt vào video và SRT cùng cấp cụm từ |
| Chữ phụ đề ở 1080p | Trắng, 50 px, viền đen đặc 2 px; font theo ngôn ngữ, tối đa hai dòng |
| Timeline phụ đề | SRT/ASS cùng lấy từ `captions-timeline.json` |
| Kiểm tra phụ đề | `captions-qa.json`, chạy trước render hình; lỗi cấu trúc/nội dung/độ phủ dừng render |

Tập mới dùng pipeline: local và visual_mode: revideo_stills với ảnh tĩnh do Codex imagegen tạo theo `visual_dna` của kênh. Cả sáu kênh dùng Chibi 2D nguyên bản, chủ động có người làm việc hoặc trải nghiệm điều đang giải thích. Không dùng Montage hoặc video clips cho tập mới. Đọc imagegen-stills.md; giữ hai worker/NVENC, camera balanced, cache theo nội dung và quy trình tái sử dụng ảnh. Không thêm nhãn AI/illustration disclosure hiển thị trong ảnh hoặc video; QA ảnh tập trung vào dữ kiện, vai trò minh họa, chữ giải thích, crop và continuity, còn provenance lưu nội bộ. Các tập đã ghi visual_mode khác vẫn tiếp tục theo cấu hình đó. Revideo chỉ dùng khi có yêu cầu chọn rõ backend; không chuyển sang CapCut khi tiếp tục ở chat khác.

## Tiếp tục một tập có sẵn

1. Đọc `AGENTS.md`, `local-pipeline.md`, trang này, rồi `brief.json` và `PROJECT_HANDOFF.md` của tập nếu có; xác nhận đúng chủ đề và trạng thái hiện tại.
2. Kiểm tra narration đã duyệt, WAV ở tốc độ tự nhiên, ảnh đã đăng ký, `beats.json` và cấu hình render. Theo `narration-review.md`, tập mới có hồ sơ duyệt lời; assembly kiểm tra lời và biên nhận WAV trước render. Tập cũ chưa lưu hồ sơ bằng máy vẫn cần đối chiếu brief/handoff. Giữ chất lượng TTS đã chọn; không giảm số bước hay kéo chậm giọng để tăng tốc hoặc bù thời lượng.
3. Với tập mới, tạo và đăng ký ảnh theo imagegen-stills.md, hoàn tất QA ảnh, rồi assemble. Chạy từ `D:\Coder\Vox-Deretor` khi tập đã đủ điều kiện assemble:

   ```powershell
   python scripts/assemble.py "D:\Video\<channel>\<slug>"
   ```

   Có thể chọn rõ backend bằng `--stills-renderer=ffmpeg`. Mặc định không cần cờ này.

4. FFmpeg tái sử dụng shot cache hợp lệ và WAV có fingerprint khớp. Chỉ dùng `--force-video` khi cần dựng lại toàn bộ shot; chỉ dùng `--redo` khi thực sự cần tạo lại TTS. Không tự dừng một render đang chạy để đổi backend: kiểm tra tiến trình và trạng thái tập trước.
5. Kiểm tra video cuối, tiếng, phụ đề, crop và chuyển cảnh trước khi báo hoàn thành; ghi trạng thái và đường dẫn kết quả vào `PROJECT_HANDOFF.md` khi bàn giao tập.

Quy chuẩn phụ đề đầy đủ và nguồn Netflix: `subtitles.md`. `needs_review` là trạng thái cần nghe/xem đối chiếu, nhất là khi timestamp là ước lượng; không coi việc xuất được video là phụ đề đã được nhận. TTS mới lưu mốc từng câu để căn qua khoảng nghỉ 0,8 giây. Mặc định SRT và ASS giữ cùng chữ/ngắt dòng/thời gian, với độ chính xác chung 0,01 giây.

Backend FFmpeg lấy worker, encoder, preset/CQ, đường dẫn ffmpeg/ffprobe và thời lượng dissolve từ nhóm `revideo` trong cấu hình hiện tại. Encode cuối lấy encoder/preset/CQ từ nhóm `renderer`. `REVIDEO_WORKERS` thuộc đường Revideo, không điều khiển backend FFmpeg trực tiếp. NVENC lỗi sẽ dừng; không tự hạ xuống CPU hoặc thay chất lượng đã chốt.

## Camera mượt và đa dạng

- Pan/zoom vẫn bật ở chế độ `balanced`; `animation.camera: "auto"` chọn theo mục đích và bố cục, không chạy vòng pan–hold–tilt–zoom theo số shot. Cảnh rộng có thể zoom-out nhẹ; có hướng quan sát rõ thì pan/tilt. Bản đồ, chữ, mặt cắt và so sánh ưu tiên đứng yên. Đây là quyết định từ metadata/từ khóa, không phải phân tích ảnh; phải kiểm crop thực tế.
- Các chỉ dẫn camera cụ thể được giữ. Đặt `animation.camera_policy: "preserve"` để giữ chỉ dẫn gốc hoặc `"balanced"` để giao cho renderer chọn.
- Giữ zoom phụ bằng 0 cho pan/tilt/hold. Hold cần đứng yên để đọc chi tiết và chữ.
- Renderer dùng tọa độ `perspective` phân số, nội suy cubic và chroma đầy đủ trước khi xuất YUV420. Không thay bằng crop `zoompan` dịch theo pixel nguyên vì dễ tái xuất hiện rung/nhảy bước ở chuyển động chậm.
- Renderer chỉ chuyển động camera và chuyển cảnh; hành động quan trọng phải đã hiện trong ảnh qua `animation.keyframe`. Parallax cần chuẩn bị layer riêng và chưa bật mặc định.

## Text trong ảnh

Mỗi shot mới mặc định có chữ ngắn, hữu ích trên biển hiệu, đồ vật hoặc bản đồ. Ghi đúng nội dung trong `in_scene_text` và vị trí trong `text_placement` trước khi xuất prompt. Nhãn giải thích dùng ngôn ngữ của kênh; chữ trên đồ vật lịch sử phải phù hợp địa điểm và thời kỳ. Kiểm tra chính tả, thông tin và độ dễ đọc trên điện thoại, kể cả trong crop camera.

Shot cần để trống có thể đặt `image_text_policy: none`. Quy tắc `none` đã ghi rõ trong tập cũ vẫn được tôn trọng; ảnh cũ không tự có chữ sau khi đổi mặc định. Muốn thêm chữ vào ảnh cũ cần cập nhật kế hoạch, tạo lại các ảnh liên quan bằng imagegen, kiểm tra và đăng ký lại. `prompt_text_exception` vẫn hỗ trợ nội dung chữ chính xác từ dự án trước. Không bịa trích dẫn/tài liệu lưu trữ hoặc đổi toàn bộ visual bible thành quy tắc cấm chữ. Phụ đề thoại tiếp tục được thêm ở bước assemble.

## Đầu ra và đo thời gian

- Visuals: `video/ffmpeg-visuals.mp4`.
- Cache từng shot: `video/ffmpeg-shot-cache/`.
- Báo cáo visuals: `video/ffmpeg-visuals.mp4.render-report.json`, gồm số frame, thời gian, số shot tái sử dụng và camera thực tế.
- Video giao: `final.mp4`, SRT: `final.srt`; thời gian từng công đoạn: `final.mp4.timing.json` khi dùng tên đầu ra mặc định.

Nếu đã có `revideo/src/timeline.json`, có thể dựng preview riêng để kiểm tra chuyển động:

```powershell
python scripts/ffmpeg_stills.py "D:\Video\<channel>\<slug>\revideo\src\timeline.json" --output "D:\scratch\episode-preview-30s.mp4" --seconds 30 --workers 2
```

Chọn đường dẫn scratch có quyền ghi, tách khỏi `final.mp4`. Preview này chỉ có hình, không đại diện cho thời gian TTS, căn phụ đề hay encode video cuối. Timeline phải đã tồn tại; assemble bằng backend FFmpeg không yêu cầu tạo một dự án Revideo mới.

Đường Revideo vẫn có thể chọn bằng `--stills-renderer=revideo`. `--reuse-revideo` cũng chọn Revideo nếu không có backend chỉ định; không dùng cờ này để yêu cầu tái sử dụng cache FFmpeg. Hướng dẫn đầy đủ: `local-pipeline.md`, camera/shot: `animation-direction.md`.


## Camera theo mục đích và QA tái dùng — 16/10/2026

Pan/zoom không bị tắt. `stills_incoming_zoom: 0.0` chỉ tắt zoom phụ lúc chuyển vào shot. Camera cụ thể và `camera_policy: preserve` vẫn giữ chỉ dẫn đã viết. Chế độ `balanced` hiện chọn theo mục đích, không tự đảo hướng hoặc thêm zoom chỉ để đổi nhịp. Hold dùng tỷ lệ 1.0 để không thêm crop camera; ảnh khác tỷ lệ video vẫn cần cover/crop theo khung xuất.

Shot mới có thể đặt trong `animation`: `camera_intent` = `read`, `compare`, `orient`, `follow`, `reveal`, `inspect` hoặc `observe`; `camera_direction` = `left`, `right`, `up`, `down`; `camera_motion_safe` là boolean cho biết người lập shot đã cân nhắc khoảng trống/crop. Follow cần hướng rõ. Cảnh có nhãn/sơ đồ chỉ tự chuyển động khi `camera_motion_safe: true`; việc đó không thay QA ảnh. Cảnh quay lại nguyên ảnh ưu tiên hold ở chế độ auto; muốn giữ chuyển động cụ thể cần chỉ dẫn camera tường minh. Không dùng camera để tạo góc nhìn mới từ ảnh tái dùng.

Trước dựng, `image-reuse-qa.json` dùng thời lượng shot sau phân bổ đuôi narration. Báo số shot lặp, số giây/tỷ lệ lặp, ảnh trở lại sát nhau và ảnh trùng byte dù khác tên. Trần 35% số shot và tối đa hai lần dùng lại mỗi ảnh vẫn chặn render; tỷ lệ thời lượng trên 35% và lặp sát nhau là cảnh báo cần xem, không phải ngưỡng thời lượng mới. Số giây là tổng thời lượng shot trước hòa trộn dissolve, không phải phân tích pixel video cuối.
