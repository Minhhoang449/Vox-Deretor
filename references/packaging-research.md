# Nghiên cứu thumbnail, tiêu đề, mô tả và tag

Làm bước này sau khi câu hỏi của bộ đã khóa, trước khi viết `youtube_metadata` và trước khi xuất gói đăng.

Tiêu đề, thumbnail và câu nói đầu phải hứa cùng một điều. Video phải làm đúng lời hứa đó.

## Lệnh

```text
python scripts/research_packaging.py "D:\Vox-Video\Mộc Vy\gia-gao" --query "cách giá gạo đến tay người mua" --query "giá gạo từ ruộng đến bán lẻ"
```

Script đọc `YOUTUBE_API_KEY` từ `.env`. Không ghi key vào lệnh, báo cáo, hay `beats.json`.

Mặc định chạy ba thứ tự: `relevance`, `date`, `viewCount`. Mỗi query lấy tối đa 8 video, rồi gộp thành 15 video khác nhau trong báo cáo. Muốn hẹp lại:

```text
python scripts/research_packaging.py "<episode>" --query "..." --orders relevance --max-results 5
```

Báo cáo ghi vào `research/packaging-<ngày>-<slug>.md`. Cụm tìm kiếm được lưu vào `youtube_metadata.search_phrases`.

## Đọc bốn phần

- **Tiêu đề.** Xem từ nào đứng đầu và tiêu đề dài khoảng bao nhiêu. Viết tiêu đề của mình: một phương án là cụm tìm kiếm rõ nghĩa, một phương án gợi tò mò nhưng vẫn nêu đúng chủ đề. Tối đa 100 ký tự. Không chép nguyên tiêu đề người khác.
- **Thumbnail.** Mở từng link. Ghi vật thể chính, độ tương phản, câu hỏi hình ảnh đang hỏi, và chỗ còn trống. API không nhìn thấy ảnh. Ảnh của mình: một chủ thể, nền gọn, vẫn đọc được khi thu nhỏ trên điện thoại. Chữ trên ảnh là tùy chọn và phải đúng chính tả.
- **Mô tả.** Hai dòng đầu nói video giải thích điều gì và trong phạm vi nào. Đưa cụm tìm kiếm vào câu tự nhiên. Phần sau tóm tắt cách giải thích và nguồn chính. Hashtag tối đa ba cái, mỗi cái bắt đầu bằng `#`. Mô tả cộng hashtag không quá 5000 ký tự.
- **Tag trong YouTube Studio.** API không trả tag của kênh khác. Pool trong báo cáo là cụm tìm kiếm cộng từ lặp lại trong tiêu đề công khai. Chỉ giữ biến thể chính tả, dấu, phiên âm hoặc viết tắt đúng bộ này. Tổng tag không quá 500 ký tự. Đừng biến tag thành danh sách từ khóa rộng.

## Trước khi xuất

Thêm một nhận xét vào `beats.json`:

```json
{ "observation": "Tiêu đề thường nêu vật thể ngay đầu. Thumbnail cho một tuyến hàng. Chỗ trống là phần giá bị chia ở khâu bán lẻ." }
```

Rồi điền `promise`, tối đa ba `candidates`, `description`, `hashtags`, `studio_tags`. `export_youtube.py` dừng nếu chưa có báo cáo hoặc chưa có `observation`.

Ba gói ứng viên phải khác nhau về góc hoặc hình, không chỉ khác màu nền. Sau khi Codex vẽ ảnh, xem ở cỡ điện thoại, chọn `selected_candidate_id`, chạy lại exporter để có `youtube-upload.txt`.
