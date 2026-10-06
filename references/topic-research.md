# Nghiên cứu trước khi triển khai

Mỗi bộ cần một gói nghiên cứu riêng cho câu hỏi của bộ đó, trước khi viết beat map và trước khi Codex vẽ ảnh.

## Key

`scripts/research_youtube.py` đọc `YOUTUBE_API_KEY` từ `.env` ở gốc repo. Nếu biến cùng tên đã có trong môi trường tiến trình, giá trị đó được dùng. Không ghi key vào lệnh, báo cáo, `beats.json`, hay chat.

## Hai tầng

1. **Khám phá kênh**, khi cần chọn hướng. Script dùng các query sẵn trong `youtube_research` của kênh và ghi báo cáo vào `references/research/`. Không chạy lại toàn bộ query này cho mỗi bộ.

```text
python scripts/research_youtube.py --channel moc-vy
```

2. **Nghiên cứu đúng bộ**, sau khi đã `bind`. Một kênh, vài query sát câu hỏi, tag riêng, báo cáo nằm trong thư mục bộ:

```text
python scripts/research_youtube.py --channel moc-vy --query "giá gạo Việt Nam từ ruộng đến bán lẻ" --tag gia-gao --order relevance --output-dir "D:\Vox-Video\Mộc Vy\gia-gao\research"
```

`--query` lặp được. `--order` nhận `relevance`, `date`, hoặc `viewCount`. Muốn đối chiếu cả ba thì chạy ba lần, mỗi lần một tag khác. `--tag` tránh ghi đè báo cáo cũ.

## Đọc báo cáo như thế nào

Báo cáo có tiêu đề, kênh, lượt xem, lượt xem/ngày ước tính, thời lượng, link thumbnail và đoạn mô tả. Dùng nó để xem người khác đang trả lời câu hỏi nào, mở đầu ra sao, và chỗ nào còn trống.

Lượt xem không phải tỷ lệ giữ chân, mức hài lòng, hay bằng chứng cho một con số. Không chép lời dẫn, tiêu đề, thumbnail, hay nhận diện hình ảnh.

Sau đó mới kiểm từng dữ kiện quan trọng bằng nguồn gốc hoặc nguồn có thẩm quyền, rồi viết beat map. `codex_prompts.py` dừng nếu `research/youtube-market-scan-*.md` chưa có trong thư mục bộ.

Khi câu hỏi đã khóa, nghiên cứu thumbnail, tiêu đề, mô tả và tag bằng `scripts/research_packaging.py`. Đó là bước riêng, ghi ở `references/packaging-research.md`.
