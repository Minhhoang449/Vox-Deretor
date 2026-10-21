# Phụ đề narration — quy chuẩn tham khảo Netflix

Cập nhật 2026-10-19. Nguồn chạy thực tế: `config/pipeline.json`, `scripts/caption_policy.py` và `scripts/caption_timeline.py`.

## Phạm vi tham khảo

Dự án chép narration cùng ngôn ngữ, nên giới hạn đọc tham khảo phần SDH của các hướng dẫn Netflix. Chúng ta chỉ áp dụng các nguyên tắc dễ đọc phù hợp: chữ trắng, font sans-serif đủ glyph, tối đa hai dòng, ngắt theo nghĩa, giới hạn tốc độ đọc và thời lượng cue. Đây không phải một bộ xuất Netflix được chứng nhận: dự án vẫn giao SRT/ASS cho YouTube, giữ nguyên lời đã duyệt và không tự thêm ký hiệu người nói, mô tả âm thanh, ruby hoặc biên tập lại lời như một bản SDH hoàn chỉnh.

| Ngôn ngữ | Ký tự tối đa mỗi dòng | Mục tiêu đọc của dự án | Trần tham khảo cùng ngôn ngữ |
|---|---:|---:|---:|
| Anh | 42 | 17 CPS | 20 CPS |
| Việt | 42 | 17 CPS | 20 CPS |
| Tây Ban Nha | 42 | 15 CPS | 17 CPS |
| Nhật | 16 ký tự toàn chiều rộng tương đương | 6 CPS | 7 CPS |
| Hàn | 16 ký tự Hangul tương đương | 12 CPS | 14 CPS |

CPS là số ký tự trên một giây hiển thị. Với chữ Latin, tính cả khoảng trắng và dấu câu, chuẩn hóa dấu Unicode trước khi đếm. Với Nhật, ký tự toàn chiều rộng tính 1, nửa chiều rộng tính 0,5. Với Hàn, chữ Latin/ASCII, khoảng trắng và dấu câu tính 0,5; Hangul tính 1. Mục tiêu thấp hơn trần là lựa chọn của dự án để còn thời gian xem hình. Riêng tiếng Việt, mức 17 CPS trong phần phụ đề dịch khác với trần 20 CPS trong phần SDH; không coi hai con số là cùng một chuẩn.

## Hình thức và chia cụm

Preset ở 1080p: font 50 px, chữ trắng, viền đen đặc 2 px, shadow nhẹ 1,2 px, lề dưới 78 px và lề ngang 84 px. Arial dùng cho Anh/Việt/Tây Ban Nha, Yu Gothic cho Nhật và Malgun Gothic cho Hàn. Cỡ chữ/lề thay đổi theo độ phân giải. Netflix không ấn định một cỡ px cho bản xuất video của dự án: hướng dẫn quy định cỡ tương đối theo độ phân giải và khả năng chứa 42 ký tự mỗi dòng; TTML dùng 100% tương đối. Preset 50 px là lựa chọn của dự án, giảm khoảng 17% so với preset cũ 60 px, với kích thước chữ còn dễ đọc trong preview điện thoại 320×180. Hướng dẫn áp dụng nguyên tắc tham khảo, không phải chứng nhận Netflix.

- Giữ phụ đề tĩnh theo cụm; mỗi cue hiển thị đủ chữ, ổn định.
- Chia ở cuối câu trước, rồi chọn dấu câu/ranh giới ý nghĩa khi cụm quá dài. Không chia máy móc mỗi tám từ.
- Giữ tên riêng, số liệu và đơn vị trong cùng một cụm/dòng khi vừa khung. Khai báo các tên/thuật ngữ cần bảo vệ bằng `caption_protected_terms` ở cấp tập hoặc beat. Bộ dò tên tự động chỉ là heuristic; câu khó nên dùng `caption_units` đã review.
- Ưu tiên một dòng nếu vừa; hai dòng phải ngắt hợp lý. Kiểm tra cả số ký tự và độ rộng bằng font, không chỉ đếm chữ.
- Giới hạn hai dòng là bắt buộc. Cụm không thể chia an toàn sẽ báo lỗi để chỉnh ranh giới phụ đề; không cắt chữ hoặc thay lời narration.
- Cue hướng tới khoảng 5/6 giây đến tối đa 7 giây theo hướng dẫn chung. Cue quá dài được thử chia lại; cue ngắn/quá nhanh không thể giải quyết an toàn sẽ được báo để review.
- Khi nhãn trong ảnh che vùng phụ đề, có thể dùng `caption_render.position: "top"` cho tập. Cần xem các khung hình có chữ bản đồ/biển hiệu; máy chưa tự phát hiện vị trí chữ trong cảnh.

## Một timeline cho hai định dạng

`captions-timeline.json` chứa các cue đã chia cụm, ngắt dòng và căn thời gian. `final.srt` và `final-captions.ass` đều xuất từ timeline này; thời gian chung được làm tròn đến 0,01 giây để hai định dạng khớp nhau. Assembly truyền đúng mốc bắt đầu beat đã tính cho cả hai exporter.

TTS mới lưu `audio/narr_<beat>.sentences.json`, ghi mốc từng câu trước khoảng nghỉ. WhisperX dùng các mốc này khi file khớp đúng WAV và narration. WAV cũ không có mốc hợp lệ vẫn dùng căn toàn beat; không tự tạo lại giọng chỉ để thêm metadata.

Cue mới không bắt đầu trước lời tương ứng. Mặc định giữ câu trước thêm 0,2 giây sau lời, có thể tận dụng một phần khoảng nghỉ để đủ thời gian đọc, giới hạn giữ tối đa 0,65 giây. Khoảng trống trước cue kế tiếp được giữ khi có thể; không kéo câu tiếp theo vào khoảng nghỉ 0,8 giây.

Timeline cache phụ thuộc narration, WAV, mốc từng câu, beat starts, ngôn ngữ, cấu hình căn thời gian, font và quy chuẩn đọc. Đổi các đầu vào này sẽ tính lại timeline. `--redo` tính lại timeline nhưng vẫn tái sử dụng cache từ WhisperX còn hợp lệ.

## Kiểm tra trước render và bàn giao

Assembly tạo/kiểm tra timeline trước render hình nặng. `captions-qa.json` có ba trạng thái:

- `pass`: các kiểm tra tự động đạt; vẫn xem/nghe mẫu thật trước khi nhận tập.
- `needs_review`: có cue quá nhanh/ngắn, font chưa đo được hoặc timestamp ước lượng. Ghi rõ vấn đề và nghe đối chiếu; trạng thái này không chứng minh căn WhisperX thành công.
- `fail`: thiếu WAV/lời đo được, mất hoặc thay chữ đã duyệt, chồng cue, quá dòng/độ rộng, quá 7 giây hoặc bỏ sót vùng thoại. Mặc định dừng trước render hình; không bỏ qua lỗi để giao tập.

Căn thời gian luôn được kiểm tra trên từng vùng có lời, loại các khoảng im lặng ra khỏi mẫu số. Mặc định cần độ phủ ít nhất 95% sau dung sai mép 0,15 giây và không được bỏ sót liên tục quá 0,4 giây lời nói. Bộ đo dùng envelope qua FFmpeg, không chứng minh từng từ đã đúng; phải nghe mẫu đầu/giữa/cuối và các cue bị cảnh báo.

`captions-alignment.json` ghi nguồn thời gian từng beat; `captions-display.json` ghi font, số cue và fingerprint timeline. Timestamp không đáng tin cậy chỉ được thay bằng ước lượng có nhãn `needs_review`, không gọi là WhisperX-aligned.

```powershell
python scripts/export_srt.py "<episode>"
python scripts/export_ass.py "<episode>"
python scripts/export_srt.py "<episode>" --redo
python scripts/preview_captions.py
```

Preview mặc định nằm ở `tmp/caption-readability-preview/`; dùng nền/chữ tổng hợp để kiểm tra renderer và hình thức, không phải kiểm tra thời gian trên giọng thật. Khi sửa phụ đề một tập, giữ ảnh và cache visual hiện có, xem báo cáo rồi dựng lại phần phụ đề bằng pipeline hiện hành.

## Nguồn chính thức đã kiểm tra

- [Netflix — General Requirements](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617-Timed-Text-Style-Guide-General-Requirements): thời lượng, hai dòng, ngắt theo ngữ nghĩa và vị trí.
- [Netflix — English USA](https://partnerhelp.netflixstudios.com/hc/en-us/articles/217350977-English-USA-Timed-Text-Style-Guide): giới hạn chữ và tốc độ đọc.
- [Netflix — Vietnamese](https://partnerhelp.netflixstudios.com/hc/en-us/articles/220447048-Vietnamese-Timed-Text-Style-Guide): font trắng, 42 ký tự/dòng và phân biệt phụ đề dịch/SDH.
- [Netflix — Spanish](https://partnerhelp.netflixstudios.com/hc/en-us/articles/217349997-Spanish-Latin-America-Spain-Timed-Text-Style-Guide): giới hạn chữ và tốc độ đọc.
- [Netflix — Japanese](https://partnerhelp.netflixstudios.com/hc/en-us/articles/215767517-Japanese-Timed-Text-Style-Guide): phần II SDH, giới hạn 16 ký tự toàn chiều rộng và 7 CPS.
- [Netflix — Korean](https://partnerhelp.netflixstudios.com/hc/en-us/articles/216001127-Korean-Timed-Text-Style-Guide): phần II SDH, giới hạn chữ có trọng số và 14 CPS.
