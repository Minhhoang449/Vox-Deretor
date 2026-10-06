# Pipeline local — Codex, Muse.ai, VoiceStudio

Bản checkout này không gọi API để tạo ảnh, video, hay giọng đọc.

| Việc | Ai làm | Script |
|---|---|---|
| Chọn kênh | Bạn chỉ định, agent gắn vào project | `scripts/channels.py` |
| Nghiên cứu chủ đề | Quét YouTube công khai trước khi viết kịch bản | `scripts/research_youtube.py` |
| Chọn thời lượng | Codex tính số shot, mỗi shot có dur riêng ≤ 10s | `scripts/plan_runtime.py` |
| Kịch bản (`beats.json`) | Agent viết đủ số shot trong plan, bạn duyệt | — |
| Ảnh collage | Codex tự vẽ | `scripts/codex_prompts.py` |
| Ảnh → video | Bạn, trên Muse.ai, dán prompt chuyển động của dự án | `scripts/muse_pack.py` |
| Giọng đọc | VoiceStudio trên máy | `scripts/voicestudio_tts.py` |
| Ghép phim | ffmpeg | `scripts/assemble.py` |
| Phụ đề SRT | đo giọng đọc | `scripts/export_srt.py` (assemble cũng ghi) |
| Thumbnail, tiêu đề, mô tả, tag | Quét cách đóng gói đang xuất hiện, rồi mới viết gói | `scripts/research_packaging.py` |
| Thumbnail + metadata | Codex vẽ ảnh, script xuất gói đăng | `scripts/export_youtube.py` |

Mỗi bộ nằm tại `D:\Vox-Video\<tên kênh>\<slug>\`. Không ghi vào thư mục `out/` của repo. Ảnh, clip Muse, giọng đọc và `final.mp4` đều nằm trong thư mục bộ đó.

Nhạc nền không được tạo tự động. Nếu muốn nhạc, đặt file `audio/bgm.mp3` trong thư mục bộ trước khi ghép. Không có file thì phim chỉ có lời.

Trong `beats.json` phải có `"pipeline": "local"`. Script `codex_prompts.py` tự ghi trường này. Khi đó `keyframes.py`, `clips.py`, `audio.py` và các script Atlas khác sẽ dừng, không gọi API.

## 0. Chuẩn bị

- Python 3, Pillow (`pip install pillow`)
- `ffmpeg` và `ffprobe`
- VoiceStudio đang mở. API local mặc định: `http://localhost:3900`
- Biến môi trường chỉ khi bạn đổi cổng hoặc bật remote:
  - `VOICESTUDIO_BASE_URL` (mặc định `http://localhost:3900/v1`)
  - `VOICESTUDIO_API_KEY` (trên localhost điền `local` cũng được)
- `YOUTUBE_API_KEY` trong `.env` ở gốc repo. Script nghiên cứu tự đọc file này. Không ghi key vào lệnh, báo cáo, hay `beats.json`.

Map giọng từng kênh nằm trong `config/channels.json`, trường `voice` (profile VoiceStudio), cùng `voice_profile_name` và `voice_reference`. Xem nhanh:

```text
python scripts/channels.py voices
```

Cách gọi máy (model `omnivoice`, tốc độ 0.8, wav, 32 bước) nằm ở `config/pipeline.json` → `voice_studio`, giống Vox-AI. `narration_direction` chỉ để agent viết lời. Request TTS không gửi câu đó, vì profile đã lưu kiểu giọng.

## 1. Chọn kênh, rồi mới viết kịch bản

Danh sách kênh nằm ở `config/channels.json`. Mỗi kênh là một bản sắc: ngôn ngữ, lời hứa nội dung, lane được phép, danh sách cần tránh, giọng VoiceStudio, và cách kể.

```text
python scripts/channels.py list
python scripts/channels.py show moc-vy
python scripts/channels.py bind moc-vy gia-gao
```

`bind` tạo `D:\Vox-Video\Mộc Vy\gia-gao` và ghi `channel_id`, ngôn ngữ, giọng, và cả khối `channel` vào `beats.json` ở đó. Các lệnh sau dùng đúng thư mục bộ này. Agent chỉ viết lời thuyết minh, tiêu đề, và ví dụ bên trong `promise`, `lanes`, và `avoid` của kênh đó. Không trộn hai kênh trong một phim.

Trước khi viết beat map, quét YouTube cho đúng câu hỏi của bộ đó. Cách làm và giới hạn nằm ở `references/topic-research.md`.

```text
python scripts/research_youtube.py --channel moc-vy --query "giá gạo Việt Nam từ ruộng đến bán lẻ" --tag gia-gao --output-dir "D:\Vox-Video\Mộc Vy\gia-gao\research"
```

Đọc báo cáo trong `research/`, chốt câu hỏi và khoảng trống, rồi mới đối chiếu sự kiện với nguồn gốc. `codex_prompts.py` dừng nếu thư mục bộ chưa có file `research/youtube-market-scan-*.md`.

Mỗi video dài 7–20 phút. Muse nhận thời lượng của từng shot và chỉ chịu tối đa 10 giây, giống API cũ truyền `shot.dur` chứ không khóa mọi cảnh ở 10 giây. Codex chạy:

```text
python scripts/plan_runtime.py "D:\Vox-Video\Mộc Vy\gia-gao" --minutes 12
```

Với 12 phút, ít nhất phải có 72 clip nếu shot nào cũng dài hết 10 giây. Mốc làm việc là khoảng 144 shot nếu mỗi cảnh khoảng 5 giây. Codex đặt `dur` từng shot từ 3 đến 10 giây sao cho tổng xấp xỉ 720 giây, rồi viết một prompt ảnh và một prompt chuyển động cho mỗi shot.

Sau khi đã gắn kênh, agent đọc `references/beat-layer.md`, chọn arc, viết các beat. Bạn duyệt beat map trước khi vẽ.

## 2. Chọn style

```text
python scripts/codex_prompts.py "D:\Vox-Video\Mộc Vy\gia-gao" --bakeoff american-retro,swiss-modern,punk-zine
```

Codex đọc `style-bakeoff/prompts/<theme>.txt`, vẽ ảnh, lưu đúng đường dẫn trong `style-bakeoff/manifest.json` (ví dụ `style-bakeoff/american-retro.png`). Bạn chọn một theme, ghi vào `"theme"` trong `beats.json`.

## 3. Codex vẽ toàn bộ ảnh

```text
python scripts/codex_prompts.py "D:\Vox-Video\Mộc Vy\gia-gao"
```

Mỗi shot có một prompt ở `codex/kf_<key>.txt` — đúng cấu trúc collage của dự án (`compose_collage_prompt`). Codex vẽ và lưu `keyframes/kf_<key>.png` (jpg hoặc webp cũng được).

```text
python scripts/codex_prompts.py "D:\Vox-Video\Mộc Vy\gia-gao" --register
```

Lệnh này ghi `keyframe_path` vào `beats.json`.

## 4. Muse.ai làm video

```text
python scripts/muse_pack.py "D:\Vox-Video\Mộc Vy\gia-gao"
```

Ra thư mục `muse/<key>/`:

- `image` — ảnh Codex vừa vẽ
- `prompt.txt` — prompt chuyển động của dự án (camera, element motion, ràng buộc giấy cắt). Dán nguyên văn vào Muse.ai
- `meta.json` — số giây và tỷ lệ khung

Việc của bạn trên Muse.ai, từng shot:

1. Image-to-video.
2. Upload `image`.
3. Dán `prompt.txt`.
4. Đặt thời lượng bằng `duration_sec`.
5. Tải clip về `clips/clip_<key>.mp4`.

Danh sách shot nằm ở `muse/INDEX.md`. Xong thì:

```text
python scripts/muse_pack.py "D:\Vox-Video\Mộc Vy\gia-gao" --register
```

## 5. VoiceStudio đọc lời

```text
python scripts/voicestudio_tts.py "D:\Vox-Video\Mộc Vy\gia-gao"
```

Mỗi beat thành `audio/narr_<id>.mp3` (hoặc wav nếu engine không có mp3) và `audio/narr_<id>.txt`. File âm thanh đã có thì được giữ; thêm `--redo` để đọc lại.

Nếu app chưa mở, script dừng và vẫn để file `.txt` để bạn dán tay vào VoiceStudio.

## 6. Ghép

```text
python scripts/assemble.py "D:\Vox-Video\Mộc Vy\gia-gao"
```

Ra `D:\Vox-Video\Mộc Vy\gia-gao\final.mp4` và `final.srt`.

SRT không phải một dòng phụ đề cho cả beat. Script cắt lời thành cụm ngắn, đo khoảng nói và khoảng lặng trong file giọng của beat đó, rồi đặt mốc thời gian đúng chỗ beat bắt đầu trên phim. Cách này giống `render.py` của Vox-AI.

## 7. Thumbnail, tiêu đề, mô tả và tag

Sau khi câu hỏi của bộ đã khóa, quét cách người khác đóng gói cùng chủ đề. Cách đọc và giới hạn nằm ở `references/packaging-research.md`.

```text
python scripts/research_packaging.py "D:\Vox-Video\Mộc Vy\gia-gao" --query "cách giá gạo đến tay người mua" --query "giá gạo từ ruộng đến bán lẻ"
```

Báo cáo nằm ở `research/packaging-*.md`: độ dài tiêu đề, hai dòng đầu mô tả, hashtag công khai, pool tag, và link thumbnail. Mở ảnh bằng tay. Ghi một `observation` vào `youtube_metadata.packaging_research`. Không chép tiêu đề hay ảnh.

Sau đó Codex điền `youtube_metadata` trong `beats.json`:

- `promise`: một câu, người xem sẽ hiểu gì và hình nào thể hiện ngay điều đó.
- `candidates`: 1 đến 3 gói. Mỗi gói có `id`, `title` (tối đa 100 ký tự), `thumbnail_concept`, `thumbnail_prompt`, `thumbnail_file` (ví dụ `assets/thumbnail-a.png`), và `thumbnail_text` nếu cần chữ trên ảnh.
- `description`, `hashtags` (mỗi cái bắt đầu bằng `#`), `studio_tags` (tổng không quá 500 ký tự).
- Tiêu đề, ảnh thumbnail và câu mở đầu phải cùng một lời hứa. Không hứa điều video không trả lời.

```text
python scripts/export_youtube.py "D:\Vox-Video\Mộc Vy\gia-gao"
```

Lần đầu xuất `thumbnail-prompts.md`. Codex vẽ từng ảnh và lưu đúng `thumbnail_file`. Xem ảnh ở cỡ điện thoại, ghi `selected_candidate_id`, chạy lại lệnh. Lần này xuất `youtube-upload.txt` (tiêu đề, mô tả, tags, đường dẫn thumbnail).
