"""Build an evidence-scoped craft analysis of three user-selected GoDocs videos.

Reads existing browser transcript exports; no remote media download or live DNA edit.
"""
from pathlib import Path
import hashlib
import html
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/godocs-three-video-analysis-2026-10-17"
EXPORTS = Path("C:/Users/Admin/AppData/Local/Temp/browser-use/exports")

VIDEOS = [
    {
        "id": "gFZlrdfpfRA", "name": "Palm Jumeirah", "duration_seconds": 1149,
        "title": "Why Isn't Dubai's Palm Jumeirah Sinking? How Engineers Turned Sand into Steel",
        "viewed_frames": [229, 574, 1034],
        "frame_notes": ["03:49: phối cảnh nhìn dọc lớp đá đê chắn sóng.", "09:34: sơ đồ đầu rung bên cạnh hình nhà để biểu đạt quy mô; nhãn chiều dài tiếng Anh.", "17:14: cận mép nước/sóng ở phần chuyển sang rủi ro dài hạn."],
        "opening": "00:05–00:35: nghịch lý cát rời chịu tải, giới hạn không bê tông ở nền đảo, nguy cơ mất ổn định và câu hỏi vì sao đảo còn đứng.",
        "mechanism": "08:50–11:03: vật so sánh hạt trong xô → rung làm hạt tái sắp xếp → đầu vibroflot → bù cát và lặp quy trình → nền đủ cho công việc tiếp.",
        "ending": "16:39–19:05: tổng kết thành quả → xói lở/bổ sung cát → áp lực dài hạn → hình tượng con người tiếp tục duy trì không gian ven biển.",
        "arc": [
            [5, 35, "Nghịch lý và lời hứa", "Tạo câu hỏi về khả năng chịu tải của một nền cát nhân tạo."],
            [35, 111, "Chọn vật liệu", "Loại một đáp án trực giác, đưa người xem từ cát sa mạc sang cát được lấy ngoài biển."],
            [111, 179, "Nền chưa ổn định", "Đặt trạng thái chưa thể xây; teaser sang điều kiện bảo vệ trước khi nén."],
            [179, 338, "Bảo vệ khỏi sóng", "Đá, độ dốc, khe rỗng, lớp lọc được đưa vào theo công việc; đây là cách video kể, chưa phải hồ sơ trình tự thi công đã kiểm."],
            [338, 503, "Định vị hình cây cọ", "Từ mặt nước không thấy hình tổng thể tới hướng dẫn tàu đổ vật liệu."],
            [503, 663, "Nén và ổn định", "Trả lời lời hứa trung tâm qua tái sắp xếp hạt và thiết bị."],
            [663, 837, "Trao đổi nước", "Giải pháp che sóng được kể là phát sinh ràng buộc lưu thông; chuỗi cửa mở và bảo vệ cửa."],
            [837, 999, "Rung chấn/hóa lỏng", "Mở thêm rủi ro; có phần quay lại cơ chế nén cần rà trùng và kiểm nguồn."],
            [999, 1145, "Hệ quả dài hạn", "Chuyển từ làm xong sang duy trì và giới hạn."],
        ],
    },
    {
        "id": "gyuGHA8N_NU", "name": "Suez", "duration_seconds": 660,
        "title": "How a 3,000-Year-Old Obsession Built the Suez Canal",
        "viewed_frames": [14, 330, 528, 594, 644],
        "frame_notes": ["00:14: nhân vật lịch sử và bản cuộn trên nền sa mạc; nét hoạt hình 2D.", "05:30: người khảo sát được nhìn qua khung ngắm có chia độ.", "08:48: hai người bên thiết bị và bản vẽ, ở ngưỡng chuyển sang cơ giới.", "09:54: tàu hơi nước, người dự lễ, màu ấm; cảnh khánh thành.", "10:44: tàu và cờ Ai Cập trong đoạn quyền kiểm soát/vận hành."],
        "opening": "00:00–00:49: montage nhiều lần thử được nén thành một thất bại lặp, rồi gợi lời giải bằng máy móc thế kỷ 19.",
        "mechanism": "07:45–09:37: nguồn lao động thay đổi → công trường bị đẩy tới ngõ cụt trong cách kể → máy móc thành bước ngoặt năng lực. Tính chính xác từng nguyên nhân lịch sử cần nguồn riêng.",
        "ending": "09:37–10:56: hoàn thành và khánh thành → tài chính/quyền kiểm soát → câu hỏi về tàu lớn và tuyến thay thế trong tương lai.",
        "arc": [
            [0, 49, "Montage thất bại", "Mở quy mô thời gian và gợi một năng lực sẽ thay đổi kết quả."],
            [53, 131, "Necho", "Mục tiêu, sức người, tổn thất và lý do dừng theo lời video."],
            [131, 183, "Darius", "Một thành công được kể rồi bị giới hạn vận hành; hook đã nén quá nhiều khác biệt lịch sử."],
            [183, 246, "Thời La Mã", "Khả năng điều tiết và duy trì thay cách dùng kênh."],
            [246, 312, "Ottoman", "Động cơ thương mại/quân sự và trở ngại hậu cần."],
            [312, 362, "Napoleon", "Phép đo trở thành rào cản quyết định trong cấu trúc video."],
            [362, 465, "Lesseps và đào kênh", "Sự cho phép, nhân lực, nước uống và công trường trở thành giới hạn."],
            [465, 563, "Khủng hoảng và cơ giới", "Đẩy lối làm cũ tới giới hạn, đổi năng lực sản xuất."],
            [563, 660, "Thành quả và cái giá", "Mở rộng từ xây công trình sang ai kiểm soát/lợi ích và tương lai."],
        ],
    },
    {
        "id": "zAISigbynHM", "name": "Burj Khalifa", "duration_seconds": 852,
        "title": "No Rock to Hold Onto - Why the Burj Khalifa Hasn't Collapsed Yet",
        "viewed_frames": [0, 170, 426, 766],
        "frame_notes": ["00:00: toàn tháp trên một khối cắt địa tầng.", "02:50: đồ họa cột/móng, đường lực và mũi tên đỏ, màu phát sáng để tập trung điểm chú ý.", "07:06: toàn cảnh khối tháp trên sa mạc ở ngưỡng chuyển từ kết cấu sang lớp vỏ.", "12:46: cơ cấu thép bên trong ở đoạn đẩy phần đỉnh lên; phong cách dựng 3D."],
        "opening": "00:00–00:10: lược bỏ phần dẫn nhập, đặt kỳ vọng móng đá cạnh công trình cực cao và hỏi vì sao nó đứng được.",
        "mechanism": "01:12–01:49 đã trả lời nền móng khái quát; 01:52–04:15 quay lại cách làm, độ bền và phân tải. 05:09–07:02 là chuỗi bơm bê tông–nhiệt–giữ khả năng thi công.",
        "ending": "13:24–14:08: công trình thành không gian có người sử dụng và cần vận hành, rồi hỏi giải pháp nào ấn tượng và người xem có muốn lên đỉnh.",
        "arc": [
            [0, 72, "Móng và kỳ vọng", "Đặt mô hình quen thuộc rồi cho thấy điều kiện địa chất khác."],
            [72, 109, "Đáp án móng sớm", "Cọc và đài bè đưa người xem tới một mô hình lực mới."],
            [112, 255, "Thi công và độ bền", "Làm lỗ, cọc, chống ăn mòn và nối thành hệ móng."],
            [255, 309, "Hình học tháp", "Từ móng sang cách kết cấu phía trên hỗ trợ nhau."],
            [309, 422, "Đưa vật liệu lên cao", "Giữ cùng mục tiêu bơm bê tông khi độ cao và nhiệt tạo trở ngại."],
            [422, 565, "Lớp vỏ và nhiệt", "Từ tháp đứng được sang không gian có thể sử dụng."],
            [565, 612, "Chênh áp", "Ràng buộc bên trong công trình kín theo lời video."],
            [612, 704, "Vận chuyển người", "Phân vùng thang máy và trải nghiệm hành khách."],
            [704, 804, "Đỉnh thép", "Giới hạn thi công và lắp dựng từ bên trong."],
            [804, 852, "Vận hành và tương tác", "Cho thấy thành quả hoạt động rồi chuyển câu hỏi cho người xem."],
        ],
    },
]

REPORT = """# Phân tích sâu ba video GoDocs — 17/10/2026

**Kết luận biên tập:** kỹ thuật đáng học nhất là đặt một trở ngại cụ thể trước lời giải thích, làm cơ chế hiện thành hành động/trạng thái có thể hình dung, và dùng kết quả của đoạn trước để dẫn sang đoạn sau. Ba video không dùng chung một kiểu mở/kết hay cùng một thời điểm trả đáp án. Cần học chọn lọc vì bản phụ đề cũng có tuyệt đối hóa, kể động cơ không dẫn nguồn và nhắc lại lời hứa.

## Phạm vi bằng chứng

- Ba URL do người dùng chọn đều được xác nhận là GoDocs / @GoDocumentaries trên giao diện YouTube ngày 17/10/2026. Độ dài player: Palm 19:09, Suez 11:00, Burj 14:12.
- Đã đọc toàn bộ ba bản export phụ đề theo timestamp. Header ghi `Language: en`, `Captions: auto-generated` nhưng nội dung thực tế là tiếng Việt; giao diện có nhãn lồng tiếng. Vì vậy phân loại là phụ đề tự động bằng tiếng Việt của video có nhiều ngôn ngữ, có thể là bản dịch. Không khẳng định đây là lời Anh nguyên văn hay xác định được từng lỗi phát sinh ở giọng gốc, dub, dịch hoặc ASR.
- Các mốc dưới đây theo phụ đề, có sai số so với lời đọc. Đã xem các frame được ghi trong evidence-manifest.json; chỉ đánh giá thông tin nhìn thấy tại những mốc ấy. Không xem liên tục toàn video hoặc nghe toàn bộ voice/BGM/SFX. Không có tỷ lệ giữ chân, CTR, biểu đồ rơi hoặc dữ liệu nội bộ.
- Phân tích cách tác giả trình bày không xác nhận sự thật của tất cả tình tiết. Một số luận điểm được kiểm chéo qua nguồn thiết kế, kỹ thuật và cơ quan vận hành; phần chưa kiểm được ghi rõ.
- Không đọc hay phục hồi sáu mẫu editorial V2 đã xóa. Không thay DNA sống hoặc media hiện hành trong lượt phân tích này.

## 1. Palm Jumeirah — nghịch lý vật liệu và chuỗi điều kiện

[Mở video](https://www.youtube.com/watch?v=gFZlrdfpfRA)

### Mở đầu 00:05–00:35

Câu hỏi ở 00:27: **“Vậy tại sao Palm Jumeirah không bị chìm?”** Không bắt đầu bằng dân số Dubai, ngày khánh thành hoặc danh sách kỷ lục. Phần mở chọn một trực giác vật lý dễ hình dung: nền rời, tải lớn, nước và giới hạn vật liệu. Từ đó người xem có một khoảng trống hiểu biết cụ thể cần lấp.

Về craft, bốn việc được làm liên tiếp: đặt điều khó tin → chỉ ra vật phải chịu hậu quả → thêm giới hạn của cách giải → hứa bóc cơ chế. Hình ảnh tinh thần đã có trước thuật ngữ. Điều đáng chuyển vào DNA là sự cụ thể của câu hỏi. Các tiên đoán sụp đổ tức khắc hoặc phép so độ cứng không được tự xem là đúng chỉ vì hook mạnh.

### Phần giữa làm gì?

Sơ đồ mốc xem ở bảng phía cuối báo cáo. Về cấu trúc, các khối lần lượt mở một điều kiện để công trình có thể tồn tại: vật liệu, che sóng, định vị, ổn định nền, trao đổi nước, phản ứng khi có rung chấn và duy trì bờ. Nhờ giữ cùng một đối tượng, việc đổi sang thiết bị khác ít giống một danh sách công nghệ hơn.

Tuy nhiên, phải phân biệt cách sắp xếp câu chuyện với lịch sử thi công có hồ sơ. Khi video nói đội kỹ sư vừa giải xong một việc rồi mới nhận ra việc khác, đó có thể là thứ tự giải thích do người viết chọn. Chưa có bằng chứng ở đây rằng các chuyên gia thật sự bất ngờ, phát hiện muộn hay làm việc theo đúng thứ tự kể ấy.

### Cơ chế và ví dụ đời thường

Đoạn 08:50–11:03 dùng một vật so sánh có các hạt và khoảng rỗng, rồi chuyển sang thiết bị, trạng thái vật liệu sau tác động và thao tác tiếp theo. Đó là cầu nối từ cái người xem đã biết đến một quá trình dưới mặt đất. Tên thiết bị đến sau nhu cầu, nên tên không phải gánh toàn bộ lời giải thích.

Một ví dụ tốt chỉ giữ thuộc tính thật sự tương ứng. So sánh rung làm hạt tái sắp xếp có ích; không được kéo suy luận tới việc loại hết nước/không khí hoặc biến vật liệu thành một chất khác. Một đoạn minh họa nên kết thúc ở quan hệ cần hiểu rồi trở lại công trình.

### Trả lời chậm hay lặp?

Lời hứa nén cát đã mở từ giây thứ 5; bước giải thích rõ về nó tới khoảng 08:50–09:19. Khoảng chờ vẫn có những đáp án nhỏ về vật liệu, sóng và định vị. Đây là khác biệt giữa trì hoãn có đóng góp và cố giấu một câu trả lời đơn giản. Đoạn trước đáp án phải tự có giá trị, không chỉ nói nguy hiểm hơn.

Bản tham chiếu cũng có chỗ cần cắt: câu hỏi vẽ hình cọ được nêu hai lượt gần 05:38/05:49; động đất được báo hai lượt gần 13:57/14:04; phần hóa lỏng trở lại nguy cơ cát rời đã mở ở đầu. Không nên lấy video phổ biến làm lý do giữ mọi lần lặp của nó.

### Kết 16:39–19:05

Kết chuyển từ thành quả sang công việc kéo dài: bờ vẫn cần duy trì, công trình còn chịu điều kiện thay đổi. Nó tạo một lớp nghĩa mới cho thành quả thay vì chỉ gọi lại tên thiết bị. Cách kết này phù hợp với tập mà phụ thuộc vận hành là phần của đáp án.

Nhưng phần cuối khá dài, có lời tổng quát về tương lai và năng lực con người. Muốn dùng hướng ấy trong documentary của mình phải có nguồn cho biện pháp/rủi ro cụ thể. Không cần gắn biến đổi khí hậu hoặc một bài học về nhân loại vào mọi tập.

## 2. Suez — nhiều lần thử, một câu hỏi xuyên lịch sử

[Mở video](https://www.youtube.com/watch?v=gyuGHA8N_NU)

### Mở đầu 00:00–00:49

Video mở bằng hành động **“Hãy đào ở đây”**, rồi nén nhiều thế lực và nhiều lần thử thành một nhịp tăng quy mô. Tiếp đó nó gợi năng lực cơ giới sẽ là khác biệt. Người xem được trao hai câu hỏi: vì sao những lần trước chưa giải quyết được việc này, và điều gì cuối cùng làm thay đổi khả năng thực hiện?

Đây là montage lời nói có hướng. Một tên người chỉ được đưa vào kèm một việc họ muốn làm và một trở ngại. Điểm đáng học là tuyển chọn chi tiết theo câu hỏi. Mối nguy là ép lịch sử thành một hàng thất bại đồng nhất để làm chiến thắng cuối lớn hơn.

### Vì sao nhiều thời kỳ vẫn có thể nối mạch?

Các khối lặp một nhiệm vụ xuyên thời gian, thay điều kiện và năng lực. Thay vì kể tất cả việc của từng triều đại, bài chọn những gì làm câu hỏi con kênh đổi trạng thái. Như vậy khán giả có chỗ đặt thông tin mới.

Nhưng tuyến qua sông Nile và kênh hiện đại nối trực tiếp hai biển không phải một tuyến bất biến. Khi rút nhiều thế kỷ về một nỗi ám ảnh duy nhất, bản đồ/phạm vi cần hiện rõ chỗ kế hoạch đã đổi. Câu nối nhân quả cũng phải dựa trên tư liệu, không tự gán rằng một nhà vua quyết định chỉ vì kiêu ngạo hay sợ hãi.

### Bước ngoặt 07:45–09:37

Trong cấu trúc video, giới hạn sức người và nguồn lao động đẩy lối làm cũ tới một ngưỡng; năng lực cơ giới được đưa vào như điều thay được kết quả. Nhờ thế máy móc không xuất hiện như một mục kỹ thuật rời. Phần mở đã gieo vai trò của nó, phần giữa làm câu hỏi ấy nặng hơn, rồi mới giải.

Đây là payoff muộn: bước ngoặt đã được gợi ở khoảng 00:39 nhưng chỉ trở lại rõ gần 08:43. Nó hợp với một câu hỏi về lịch sử điều kiện thực hiện. Nếu dùng cho Cà Mau/SVB, không thể trì hoãn một cơ chế đơn giản tám phút bằng các tên nghiên cứu; mỗi lần thử phải có kết quả hoặc điều kiện thực sự khác.

### Kết 09:37–10:56

Sau thành quả vật lý, bài đổi câu hỏi sang ai có quyền kiểm soát và lợi ích, rồi đưa người xem tới một vấn đề tương lai. Đây là cách đưa chi phí sau thành công vào chuyện.

Câu tương tác cuối rộng hơn phần thân đã kiểm chứng. Nó có thể mời thảo luận nhưng không thay thế một đáp án. Nếu mình kết bằng một câu hỏi, câu hỏi trung tâm của tập phải được trả trước; câu mới phải phát sinh từ hệ quả vừa chứng minh.

### Điểm không nên mang theo

Phụ đề diễn đạt nhiều tâm lý, cảnh đơn độc, sự chế giễu và động cơ của nhân vật như điều người kể biết chắc. Audit này chưa có nhật ký, thư hoặc lời chứng để xác nhận các cảnh ấy. Chúng không được chuyển sang documentary của mình thành sự thật.

Lịch sử cổ đại cũng được nén rất mạnh. [Suez Canal Authority](https://www.suezcanal.gov.eg/English/About/SuezCanal/Pages/CanalHistory.aspx) ghi nhận cả giai đoạn Ptolemy II và những lần khôi phục/gián đoạn khác. Nguồn thể chế này đủ cho thấy cần đối chiếu thêm trước khi nhận một đường kể thất bại liên tục; nó không tự giải quyết mọi tranh luận sử học hoặc chứng thực mọi mốc trong video.

## 3. Burj Khalifa — đáp án sớm, mở rộng từ móng tới công trình vận hành

[Mở video](https://www.youtube.com/watch?v=zAISigbynHM)

### Mở đầu 00:00–00:10

Video đặt ngay nghịch lý **“không có tảng đá nào để bám vào”** bên dưới một công trình cực cao. Câu ngắn, quan hệ tải trọng–nền đất dễ tưởng tượng, và một chuẩn thông thường được đưa ra để chuẩn bị đảo cách hiểu.

Khác Palm/Suez, đáp án khái quát đã xuất hiện từ 01:12–01:49. Người xem không phải chờ cuối mới được biết cơ sở giữ tháp. Phần sau kéo họ đi bằng câu hỏi triển khai: thi công ra sao, bền ra sao, làm thế nào dựng và sử dụng phần phía trên.

### Cách mở rộng và giới hạn lời hứa

Trục vật lý đi từ dưới lên trên: nền, kết cấu, đưa vật liệu, lớp vỏ, môi trường trong nhà, vận chuyển người, đỉnh và vận hành. Chuyển quy mô tạo thêm công việc giải thích; một đối tượng quen thuộc vẫn giữ được sự liên tục.

Song title nhấn rất hẹp vào móng/không sụp, trong khi phần lớn thời lượng mở sang các hệ khác. Đây là điểm cần kiểm title–body. Nếu mình chọn một câu hỏi hẹp thì hoặc giữ mọi nhánh phục vụ nó, hoặc trình bày lời hứa rộng hơn ngay đầu. Không phải hễ thêm một công nghệ thú vị là nó phục vụ câu hỏi đã hứa.

### Chuỗi giải thích mạnh 05:09–07:02

Một nhiệm vụ cụ thể được giữ xuyên đoạn: đưa vật liệu tới nơi cần dùng. Các ràng buộc được bổ sung vào cùng nhiệm vụ, rồi lời giải thích tác động vào đúng đặc tính gây khó. Như vậy khán giả hiểu vì sao kỹ thuật đó cần thiết, không chỉ nhớ rằng nó đặc biệt.

Đây là mẫu rất gần điều SVB và Cà Mau đang thiếu: cùng một việc cần hoàn thành, một điều kiện đổi và một kết quả. Bản tham chiếu vẫn cần kiểm kỹ các từ tuyệt đối về giải pháp duy nhất, phá vỡ quy tắc hay không có khó chịu; audit cấu trúc không xác nhận các khẳng định ấy.

### Kết 13:24–14:08

Không chỉ trả lại câu móng, video cho thấy tháp đã thành nơi cần vận hành. Sau đó nó mời khán giả chọn một giải pháp và tưởng tượng trải nghiệm lên cao. Câu tương tác dựa vào những gì bài vừa cho họ hiểu nên gần nội dung hơn một lời hỏi ý kiến chung.

Điểm hạn chế là phần kết ca ngợi rộng và thu hẹp sự khác biệt giữa làm đúng kỹ thuật với phá bỏ quy tắc. DNA của mình nên giữ hệ quả sử dụng/vận hành; mức độ tán dương không thay cho cơ chế đã chứng minh.

## 4. Lời giải thích và hình ảnh phối hợp thế nào?

Các frame đã xem có ba việc khác nhau, không nên gọi gộp là một phong cách:

- Palm: phối cảnh vật liệu/công trình xen đồ họa kỹ thuật; frame đầu rung đặt cạnh hình nhà để cho người xem đọc được quy mô.
- Suez: người, thiết bị và bối cảnh hoạt hình 2D; frame khảo sát đặt người xem vào điểm nhìn dụng cụ, đúng nhiệm vụ đang nói.
- Burj: khối cắt địa tầng, kết cấu/mũi tên và cơ cấu 3D; đổi từ nhìn toàn thể sang bộ phận ở những câu hỏi cơ chế.

Chỉ từ những frame này có thể rút ra chức năng hình: định vị → chỉ vật cần hiểu → cắt/xuyên để lộ quan hệ → nhìn kết quả. Chưa đủ để đo số cut/phút, tốc độ pan/zoom, nhịp nhạc hoặc kết luận từng cảnh có chuyển động vật lý thật. Không lấy frame có mũi tên làm bằng chứng thuật toán hay độ chính xác kỹ thuật.

Với pipeline stills của mình, một góc cận/cắt cần mang thêm thông tin hoặc cho thấy trạng thái khác. Pan/zoom hướng mắt; nó không thay thế việc có ảnh đúng trạng thái trước/sau. Chưa thể suy ra tỷ lệ tái dùng ảnh hay cách sản xuất của GoDocs từ các mẫu này.

## 5. Ba kiểu nối đoạn cần phân biệt

1. **Hệ quả nhân quả:** một giải pháp thực sự thay điều kiện và tạo/để lộ một đánh đổi. Muốn kể như vậy phải có nguồn chứng minh cả hai vế và quan hệ.
2. **Điều kiện tiên quyết:** để làm việc B, trước hết cần A. Đây có thể là thứ tự giải thích hợp lý, nhưng không tự là lịch sử phát hiện/thi công đúng theo lời kể.
3. **Nhiệm vụ tiếp theo:** A xong, còn B để cả hệ hoạt động. B không nhất thiết do A gây ra. Dùng chuyển đoạn trực tiếp được, không cần thêm một cơn khủng hoảng giả.

Các video dùng cả ba nhưng có lúc phủ cùng một lớp tính từ khủng hoảng lên tất cả. DNA của mình cần giữ sự khác biệt. Cùng một ngữ pháp nguyên nhân không đồng nghĩa ép mọi đoạn thành một nguy hiểm mới.

## 6. Kiểm chéo để không học nhầm khoa học

Đây là kiểm tra chọn lọc, không phải full fact-check ba video:

- **Palm:** [trang bảo tàng tại The View](https://www.theviewpalm.ae/en/museum/vibro-compaction) mô tả nén rung, lún và bù cát; [Keller](https://www.kellerme.com/expertise/techniques/vibro-compaction) mô tả kỹ thuật cải tạo đất hạt. Chúng không ủng hộ việc hiểu lời 10:33–10:38/15:46–15:56 như loại sạch nước và làm nước không thể trở lại. Nén tăng độ chặt không biến cát bão hòa thành chất rắn kín nước. Các chi tiết 40 tấn, nền giảm chấn cho mọi công trình hay bảo vệ hoàn toàn vẫn cần nguồn dự án riêng.
- **Burj:** [nghiên cứu thử tải móng 2023](https://avestia.com/CSEE2023_Proceedings/files/paper/ICGRE/ICGRE_106.pdf), phần ground profile/Table 1, có các lớp đá yếu và địa tầng khác nhau. Hook cần phân biệt không có nền đá cứng kiểu trực giác với hoàn toàn không có đá; cách giải thích toàn bộ cọc chỉ bám cát làm mất cơ chế địa kỹ thuật quan trọng. [SOM](https://www.som.com/projects/burj-khalifa/) mô tả buttressed core, hình Y và tác dụng đổi hình theo cao độ; đó là cơ sở kỹ thuật để thay ngôn ngữ thần kỳ bằng quan hệ lực.
- **Suez:** lịch sử kênh cổ, tuyến hiện đại, chế độ lao động, cơ giới, sở hữu cổ phần và kiểm soát lãnh thổ cần tách nhau. Thông tin [cơ quan kênh đào](https://www.suezcanal.gov.eg/English/About/SuezCanal/Pages/CanalHistory.aspx) đủ để chỉ ra các mốc bổ sung/khác biệt, không đủ để kết tội mọi câu riêng của video. Tâm lý người thật và lời thoại ngắn trong hook không được coi là trích dẫn lịch sử đã kiểm.

Vì bản phụ đề có dịch/ASR, những vấn đề trên là vấn đề của phát biểu đang đọc được; chưa kết luận lỗi nằm ở bản gốc hay bản chuyển ngữ. Trước khi dùng một dữ kiện làm hook của mình phải quay về nguồn gốc.

## 7. Đối chiếu trực tiếp với sáu tập của mình

- **Cà Mau:** có nghịch lý và câu hứa theo hạt bùn nhưng B13–B17 đi theo các bài nghiên cứu. Bài học từ Palm là giữ đối tượng và làm lộ điều kiện qua hành động; bỏ việc lần lượt tóm tắt năm bài báo. Không copy kết luận nền cát kín nước hoặc biến các nguyên nhân khả dĩ thành nguyên nhân đã đo ở Hương Mai.
- **SVB:** thay vòng kể lại báo cáo bằng cùng việc tiếp cận tiền, qua ordinary coverage → Friday plan → Sunday exception → Monday access. Bài học từ Burj là câu hỏi nhỏ có lời giải rồi mở việc tiếp; không cần giấu đáp án chính tới cuối.
- **Terra:** kỳ ngừng cấp tháng 12 là phép thử của cùng tuyến nước, phù hợp hơn việc nhắc tên các nhánh hai lần. Mỗi con số phải giúp đọc được điều kiện hoặc kết quả.
- **Khe Sanh:** mỗi phương thức tiếp tế có giới hạn thật, rất hợp cách giải thích bằng nhiệm vụ. Cần giữ một kết khi đường được khôi phục; không thêm bốn lượt diễn giải lại air/ground.
- **Nyos:** điều tra có thể tiến bằng chứng cứ làm đổi mô hình nguyên nhân. Đừng thay phát hiện mới bằng nhiều lời nhắc điều chưa biết; không thêm một kích hoạt giả chỉ để có bước ngoặt như video tham chiếu.
- **Nhật:** Sapporo đã có câu hỏi đời thường và tuyến vật chất. Gộp phần lặp cơ sở; đổi cỡ hình theo điều cần hiểu. Không nhập câu hô kịch tính hoặc diễn đạt dịch Anh vào giọng Nhật hiện hành.

## 8. Đoạn thử nguyên bản để thấy khác biệt

Đây là minh họa biên tập, chưa thay lời đã duyệt, chưa phải kịch bản mới:

**Cà Mau:** Đê giảm sóng ở Hương Mai đã làm yếu năng lượng sóng. Nhưng trong giai đoạn được khảo sát, nghiên cứu không ghi nhận bùn mịn tích tụ như mong đợi. Vấn đề nằm ở khoảng cách giữa hai kết quả ấy: nước bớt sóng chưa cho biết bùn đã ở lại đáy. Muốn hiểu điều đó, phải nhìn tiếp vào dòng nước đưa bùn tới và điều kiện khiến nó lắng xuống hoặc bị cuốn đi.

Đoạn thử giữ nghịch lý rồi biến nó thành việc phải quan sát tiếp; không tự kết luận một nguyên nhân riêng tại điểm khảo sát. Các giả thuyết về dòng/nguồn bùn vẫn cần gắn nguồn khi phát triển toàn đoạn.

**SVB:** On Friday, the first resolution plan treated insured and uninsured deposits differently. By Sunday, officials had extended protection to all SVB deposits, with access from Monday. The ordinary insurance limit had not changed; the authority used for this particular failure had.

Đoạn thử giữ một việc tiếp cận tiền qua thay đổi quyền hạn; các điều kiện thủ tục và ngày cần nằm đúng chỗ trong toàn bản. Không tạo khách hàng giả thành nhân chứng.

## 9. Đề xuất DNA rút ra

Đọc DNA_LESSONS_PROPOSED.md. Trọng tâm là: trở ngại cụ thể → cơ chế cần biết → trạng thái mới → phụ thuộc/hệ quả có nguồn. Đây là cách kiểm đoạn, không phải công thức câu nói, số chương, nhịp cliffhanger hay yêu cầu mỗi giải pháp tạo khủng hoảng.

Đánh giá sau này bằng chất lượng đoạn đã sửa và, khi có, dữ liệu phát hành. Lượt xem công khai của ba video không chứng minh kỹ thuật nào làm tăng retention hay cho phép dự đoán hiệu quả của sáu kênh.
"""

LESSONS = """# Bài học DNA từ ba video GoDocs — đề xuất, 17/10/2026

Liên hệ: REPORT.md và audit sáu tập ở ../six-produced-scripts-review-2026-10-17/. Chưa sửa active DNA, narration hay media.

## Quy tắc viết đề xuất

Đặt một điều người xem cần hiểu bằng một sự kiện/trạng thái cụ thể. Cho lời giải thích xuất hiện tại chỗ nó giúp hiểu hành động, khả năng hoặc giới hạn. Sau lời giải thích phải chỉ ra cái gì giờ đã khác: vật liệu ổn định hơn, đường có thể đi, nước tới nơi dùng, tiền có thể tiếp cận hoặc mô hình nguyên nhân đổi theo bằng chứng.

Chọn đúng kiểu nối đoạn: hệ quả có quan hệ nhân quả; điều kiện tiên quyết; hoặc nhiệm vụ tiếp theo của cùng hệ. Chỉ kiểu thứ nhất được kể như giải pháp trước tạo ra vấn đề sau, và quan hệ đó phải có nguồn. Không gán rằng kỹ sư bất ngờ, nhân vật sợ hãi hay giải pháp duy nhất tồn tại nếu hồ sơ không chứng minh.

Trả một đáp án nhỏ có ích trước khi chuyển câu hỏi. Đáp án lớn có thể đến sớm hoặc muộn tùy nhiệm vụ; mọi đoạn chờ phải tự tạo tiến triển. Khi đáp án lớn đã trả, các nhánh sau phải được giới thiệu trong lời hứa hoặc cho thấy một hệ quả thực sự liên quan. Không dùng sự thú vị của chi tiết để thay sự liên quan với câu hỏi tập.

Vật so sánh chỉ chuyển một quan hệ cần hiểu sang hình quen thuộc. Nói đúng giới hạn khi nó làm thay kết luận; không dùng phép so để biến cát thành thép, đá yếu thành không có đá, hoặc độ bền thiết kế thành bảo vệ vĩnh viễn. Số liệu có chức năng quy mô/ngưỡng/chênh lệch; chỉ giữ số khi giúp hiểu cơ chế/hệ quả.

Kết bằng loại payoff phù hợp: kết quả, đánh đổi vận hành, giới hạn bằng chứng hoặc thay đổi trải nghiệm. Câu tương tác là tùy chọn và đến sau payoff; nó không được thay câu trả lời còn thiếu. Không bắt buộc kể tương lai/khí hậu, ca ngợi thiên tài hay quay lại hình mở bằng cùng một câu chữ.

## Hình và camera

Chọn cỡ hình theo câu hỏi: toàn cảnh/bản đồ để định vị; cắt lớp để thấy quan hệ không nhìn được; cận để đọc một thao tác; trở lại toàn cảnh để thấy hệ quả. Không coi pan/zoom là sự kiện vật lý. Một still khác phải có lý do thông tin; một cảnh tái dùng phải giữ trạng thái đúng theo chính sách hiện hành. Các frame tham chiếu không cho phép kết luận GoDocs dùng một pipeline hoặc tỷ lệ tái dùng nào.

## Kiểm tra ngắn trước duyệt

- Người xem đã hiểu/biết thêm điều gì sau đoạn này? Nếu chỉ đổi tính từ, gộp hoặc cắt.
- Câu nối là nhân quả, điều kiện tiên quyết hay nhiệm vụ tiếp theo? Nguồn có cho phép cách nói đó không?
- Câu hỏi title/opening được trả ở đâu? Những nhánh sau đó còn nằm trong lời hứa nào?
- Có lặp teaser, cơ chế, đáp án hoặc kết vừa xuất hiện không?
- Có câu dự đoán tuyệt đối, tâm lý/đối thoại người thật hoặc phép so bị kéo quá giới hạn không?

Những câu hỏi này gộp vào story/retention hiện có; không tạo thêm điểm số hoặc quota cliffhanger. Native-language review, approved narration, fact ledger và các production gate hiện hành vẫn là nguồn điều khiển.
"""


def stamp(seconds):
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    evidence = []
    for v in VIDEOS:
        matches = list(EXPORTS.glob(f"youtube-{v['id']}-*.txt"))
        if not matches:
            raise RuntimeError(f"Missing browser transcript export: {v['id']}")
        source = max(matches, key=lambda p: p.stat().st_mtime)
        text = source.read_text(encoding="utf-8-sig")
        # Keep a research record, not a full-transcript deliverable in the report.
        cues = re.findall(r"^\[(\d+:\d+)\]", text, flags=re.M)
        evidence.append({**v, "url": f"https://www.youtube.com/watch?v={v['id']}",
                         "transcript_export_path": str(source),
                         "transcript_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                         "transcript_cues": len(cues), "first_cue": cues[0], "last_cue": cues[-1],
                         "evidence_class": "Full timestamped auto-caption export in Vietnamese despite en header; language provenance uncertain. Sampled frames only. No full listening or full playback review."})
    (OUT / "evidence-manifest.json").write_text(json.dumps({"date": "2026-10-17", "channel": "GoDocs / @GoDocumentaries", "videos": evidence}, ensure_ascii=False, indent=2), encoding="utf-8")
    timelines = ["", "## Phụ lục: mốc diễn tiến và frame đã xem", ""]
    for v in evidence:
        timelines += [f"### {v['name']} — {stamp(v['duration_seconds'])}", "", "| Khoảng phụ đề | Công việc của đoạn | Đóng góp vào câu hỏi |", "|---|---|---|"]
        for a, b, label, why in v["arc"]:
            timelines.append(f"| [{stamp(a)}–{stamp(b)}](https://www.youtube.com/watch?v={v['id']}&t={a}s) | {label} | {why} |")
        timelines += ["", "Frame kiểm tra thực tế:", ""] + [f"- {note}" for note in v["frame_notes"]] + [""]
    (OUT / "REPORT.md").write_text(REPORT + "\n".join(timelines), encoding="utf-8")
    (OUT / "DNA_LESSONS_PROPOSED.md").write_text(LESSONS, encoding="utf-8")
    sections = []
    for v in evidence:
        rows = "".join(f'<tr><td><a href="https://www.youtube.com/watch?v={v["id"]}&amp;t={a}s">{stamp(a)}–{stamp(b)}</a></td><td>{html.escape(label)}</td><td>{html.escape(why)}</td></tr>' for a,b,label,why in v["arc"])
        sections.append(f'''<section data-id="{v['id']}"><h2>{html.escape(v['name'])} <small>{stamp(v['duration_seconds'])}</small></h2><p>{html.escape(v['title'])}</p><h3>Mở</h3><p>{html.escape(v['opening'])}</p><h3>Cơ chế và bước ngoặt</h3><p>{html.escape(v['mechanism'])}</p><h3>Kết</h3><p>{html.escape(v['ending'])}</p><details><summary>Mốc diễn tiến · bấm để mở đúng đoạn YouTube</summary><table><thead><tr><th>Mốc phụ đề</th><th>Công việc</th><th>Phân tích</th></tr></thead><tbody>{rows}</tbody></table><h3>Frame đã xem</h3><ul>{''.join('<li>'+html.escape(n)+'</li>' for n in v['frame_notes'])}</ul></details></section>''')
    options = "".join(f'<option value="{v["id"]}">{html.escape(v["name"])}</option>' for v in evidence)
    html_doc = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ba cách kể của GoDocs · 17/10/2026</title><style>body{margin:0;background:#f6f6f2;color:#263039;font:16px/1.65 system-ui,sans-serif}main{max-width:1060px;margin:auto;padding:28px}header{padding-bottom:24px;border-bottom:2px solid #314c60}h1{font-size:28px;line-height:1.25}h2{font-size:23px}h3{font-size:17px}small{font-size:14px;color:#566673}section{padding:24px 0;border-bottom:1px solid #c6cdd2}select{font:inherit;padding:8px}a{color:#1d526d}summary{cursor:pointer;font-weight:600}table{border-collapse:collapse;font-size:14px}td,th{padding:10px;text-align:left;border-bottom:1px solid #c6cdd2;vertical-align:top}.note{background:#e6ecef;padding:16px}.meta{font-size:14px;color:#53616a}</style><main><header><p class="meta">Nghiên cứu ngày 17/10/2026 · Ba video do người dùng chọn</p><h1>Trở ngại khiến lời giải thích có việc để làm</h1><p>Palm giữ lời hứa vật lý để trả muộn. Suez dùng một câu hỏi qua nhiều lần thử. Burj trả móng sớm rồi mở rộng công trình. Không có một nhịp trả đáp án bắt buộc.</p><p class="note">Đọc đủ ba export phụ đề tiếng Việt tự động, header en không chứng minh đó là lời Anh nguyên văn. Đã kiểm các frame được liệt kê; chưa nghe/xem trọn. Không có dữ liệu retention hoặc CTR.</p><p><a href="REPORT.md">Phân tích sâu, kiểm chéo và đối chiếu sáu tập</a> · <a href="DNA_LESSONS_PROPOSED.md">Bài học DNA đề xuất</a> · <a href="evidence-manifest.json">Phạm vi bằng chứng</a></p><label for="pick">Xem: </label><select id="pick"><option value="all">Cả ba video</option>OPTIONS</select></header>SECTIONS<footer><h2>Điều kiện áp dụng vào DNA</h2><p>Giữ nguyên nhân–cơ chế–hệ quả có nguồn. Phân biệt quan hệ nhân quả, điều kiện tiên quyết và nhiệm vụ tiếp theo. Không thêm sự bất ngờ, khủng hoảng, động cơ hoặc tiên đoán sụp đổ chỉ để nối đoạn.</p><p>Hình phục vụ định vị, cắt lớp, thao tác hoặc kết quả. Các frame mẫu không chứng minh tốc độ cut, pan/zoom hoặc cách GoDocs sản xuất. Không thay DNA sống hay lời đã duyệt trong lượt này.</p></footer></main><script>document.getElementById('pick').addEventListener('change',e=>document.querySelectorAll('section').forEach(s=>s.hidden=e.target.value!=='all'&&s.dataset.id!==e.target.value));</script></html>'''
    (OUT / "review.html").write_text(html_doc.replace("OPTIONS",options).replace("SECTIONS","".join(sections)), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"report":str(OUT/'REPORT.md'), "videos":[{"id":v['id'],"captions":v['transcript_cues'],"last_cue":v['last_cue'],"frame_times":v['viewed_frames']} for v in evidence]},ensure_ascii=False))


if __name__ == "__main__":
    main()
