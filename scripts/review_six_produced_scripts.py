"""Build a dated editorial review from the six current episode texts, read-only.

This is a report builder with explicit editorial judgments, not an auto-scoring tool.
It never edits episode narration, live DNA, media, approval state or retired samples.
"""
import difflib
import hashlib
import html
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/six-produced-scripts-review-2026-10-17"
sys.path.insert(0, str(ROOT / "scripts"))
import channels

STORY = ["Mở đầu", "Phạm vi/lời hứa", "Diễn tiến nhân quả", "Cơ chế/số liệu", "Lời nói tự nhiên", "DNA kênh", "Chứng cứ/giới hạn", "Kết thúc"]
RETENTION = ["Tò mò mở đầu", "Tiến triển không lặp", "Nối/trả câu hỏi", "Khả năng minh họa", "Đáp án/hệ quả"]

REVIEWS = {
    "last-safe-minute": {
        "master": "narration-v1-draft.md", "start": "On 21 August", "stop": None,
        "title": "Hồ Nyos: điều tra cơ chế đã lấn diễn biến thảm họa",
        "summary": "Mở đầu rõ, cơ chế khí hòa tan và ống khử khí có liên hệ tốt. Sau cú mở, phần lớn tập chuyển sang giải thích khoa học và giới hạn suy luận; phản ứng, cứu hộ và hậu quả đời sống rất mỏng so với lời hứa của Last Safe Minute.",
        "quotes": [
            ["B01", "The lake remained where it was. The gas did not."],
            ["B04", "Those bubbles would rise too, pulling nearby water with them."],
            ["B09", "The lake can tell us how the danger formed. The surviving evidence cannot tell us precisely what set it in motion."],
        ],
        "stall": "B06 (105,63 giây) lặp ranh giới nguồn khí/cơ chế/kích hoạt vốn đã đặt ở B03–B04; B09 quay lại cùng giới hạn. Bí ẩn kích hoạt là trọng tâm hợp lệ, nhưng việc nhắc lại hồ sơ chưa đủ không tạo thêm phát hiện.",
        "story": [2, 2, 1, 2, 1, 1, 2, 1],
        "story_reasons": ["Có ngày, nơi và chuyển động vật lý cụ thể.", "Lời hứa cơ chế/kích hoạt rõ, không bịa mốc phút.", "Chuỗi điều tra dễ theo dõi nhưng thiếu diễn biến con người và ứng phó.", "Dissolution → pressure → bubbles → controlled pipe là chuỗi giải thích dùng được.", "Các câu về hồ sơ và điều không thể khẳng định chiếm nhiều vị trí; B06 nói về 'the title'.", "Giọng điềm tĩnh đúng; trục sự kiện–ứng phó–hậu quả chưa đủ trong lời thực tế.", "Phân biệt mô hình, giả thuyết và quan sát rõ; không suy đoán kích hoạt thành sự thật.", "Đáp án đúng phạm vi nhưng tổng kết điều tra và giới hạn lặp quá dài."],
        "retention": [2, 1, 1, 2, 1],
        "retention_reasons": ["Mặt hồ còn nguyên, khí rời hồ là hình ảnh tốt.", "B03/B04/B06/B09 trở lại cùng sự phân biệt nhiều lần.", "Đến Monoun ở B07 mới mở thêm phụ thuộc; lịch sử đặt muộn mà chưa làm đổi quyết định trước đó.", "Mặt cắt, áp suất, sườn dốc và ống có thể giải thích rõ.", "Chưa thấy rõ cộng đồng được cứu trợ/di dời hoặc đời sống sau sự kiện từ hồ sơ đã kiểm chứng."],
        "fixes": ["Giữ mở đầu và đoạn ống khử khí. Gộp lời giải thích tích khí–giải phóng thành một đường nhân quả, giữ kích hoạt chưa rõ tại đúng chỗ tranh luận.", "Nghiên cứu thêm phản ứng, cứu hộ, nơi người sống sót được đưa tới và hậu quả đã ghi nhận. Chỉ thêm điều có nguồn; nếu nguồn không đủ thì xác định tập này là điều tra nguyên nhân, không chấm như đã tái dựng đầy đủ thảm họa.", "Gộp kết B09 thành hậu quả của việc đo/khử khí và một câu giới hạn về kích hoạt; bỏ 'the title' và lời bình về việc kể chuyện."],
        "dna": "Cho phép nhánh điều tra nguyên nhân trong Last Safe Minute, nhưng vẫn nối các phát hiện với người bị ảnh hưởng và hành động ứng phó. Không ép cảnh báo/cứu hộ khi hồ sơ thiếu; phải nêu thiếu trong review, không tự cho 2/2 channel fit.",
        "example": "B06: 'The gas accumulated over time. What first lifted the deep water on 21 August was not recorded.' Hai câu minh họa cách thu ngắn một qualification, không thay toàn bộ đoạn tranh luận hay kết luận nghiên cứu.",
    },
    "terra-rewired": {
        "master": "narration-draft-v1.md", "start": "Look out from", "stop": None,
        "title": "Đông Giang–Hong Kong: đúng đường nước, giữa tập còn giống danh mục hạ tầng",
        "summary": "Đây là tập bám grammar kênh tốt: lưu vực → chuyển nước → trữ/xử lý → vòi và mạng xả toilet. Tuy vậy, số liệu vào quá sớm, nhánh đường nước lặp và phần cuối liệt kê lại cả tuyến.",
        "quotes": [
            ["B01", "Yet the largest source of Hong Kong's fresh water is a river that doesn't flow through Hong Kong at all."],
            ["B10", "The department says water supply from Guangdong is suspended each December."],
            ["B14", "But the glass at the tap depends on a system whose source begins far beyond the view from the waterfront."],
        ],
        "stall": "B08–B09 (111,25 giây) hai lần giải thích nước đi thẳng tới trạm xử lý hoặc qua hồ và các nhánh được nối nhau. B06 quay lại tuyến cũ sau khi B05 đã đưa người xem vào tuyến hiện nay. B14 (86,87 giây) là beat dài nhất nhưng chủ yếu recap.",
        "story": [2, 2, 1, 1, 1, 2, 2, 1],
        "story_reasons": ["Nghịch lý ven biển/nguồn ngoài lưu vực rõ.", "Cùng một hệ thống và endpoint vòi nước.", "Tiến theo tuyến thật nhưng tuyến cũ và nhánh lặp làm ngắt nhịp.", "Không phát hiện cơ chế sai trong kiểm tra giới hạn; nhiều số khác đơn vị/năm làm tăng tải hiểu.", "70–80%, 816 triệu m³ rồi ba số ở B03 đến trước khi tuyến có hành động.", "Địa điểm và một dòng vật chất giữ trục; bảo trì là phụ thuộc có thật.", "Tách raw/treated, flushing/freshwater và historical/current cẩn thận.", "Đáp án trọn nhưng lặp nguồn, tuyến và blend quá dài."],
        "retention": [2, 1, 1, 1, 1],
        "retention_reasons": ["Câu hỏi nguồn nước tự nhiên từ cảng và vòi.", "B08–B09 lặp cùng khả năng routing/storage.", "Tháng 12 ngừng cấp là chuyển trạng thái mạnh nhưng đến sau nhiều danh mục.", "Sơ đồ có thể rõ; phần số/nút tên riêng cần chọn lọc trong lời, không giao hết cho hình.", "Về được vòi nước nhưng đoạn cuối gần như đi lại toàn tuyến."],
        "fixes": ["Dùng kỳ ngừng cấp tháng 12 như phép thử vận hành của cùng tuyến, rồi làm rõ hồ và bảo trì giải quyết điều gì; giữ đúng đó là kỳ bảo trì có kế hoạch, không tạo cảnh thiếu nước giả.", "Gộp B08–B09; tuyến lịch sử chỉ giữ nếu giải thích một thay đổi chất lượng/đường đi hiện nay. Chọn một số quy mô có vai trò, đưa số còn lại vào bảng/ghi chú.", "Kết bằng hai dịch vụ nước ở cùng tòa nhà: nước đã xử lý và mạng xả riêng. Chỉ gọi về nguồn xa một lần, không nhắc lại đầy đủ các trạm."],
        "dna": "Mỗi chặng của tuyến phải giải quyết một trở ngại hoặc đổi trạng thái vận hành; tránh đưa danh sách mọi nút vào lời. Daily life có thể là cùng một dịch vụ tại nhà, không cần bịa một gia đình.",
        "example": "'Each December, the mainland supply pauses. Hong Kong still needs water. Stored raw water feeds the works while crews inspect and repair the route.' Đây là đoạn thử từ dữ kiện sẵn có, cần biên tập lại trong toàn mạch trước khi dùng.",
    },
    "battlefield-bearings": {
        "master": "master-narration.md", "start": "On February", "stop": None,
        "title": "Khe Sanh: cơ chế tiếp tế tốt, đáp án và kết bị nói lại",
        "summary": "LAPES, thời tiết, chặng trực thăng và sửa cầu làm hậu cần thành hành động có thể nhìn thấy. Điểm yếu lớn là chia nhỏ rồi diễn giải lại; bốn beat cuối cùng cùng trả lời airlift giữ căn cứ còn Pegasus mở đường.",
        "quotes": [
            ["B01", "On February 23, 1968, the large C-130 transport stopped landing at Khe Sanh."],
            ["B19", "At one small position, nine days without helicopter flights created a water shortage."],
            ["B34", "One date marks the meeting, the other a restored corridor."],
        ],
        "stall": "B31–B34 (100,05 giây, gần 12% speech) tổng kết lại cùng hai chức năng. B34 lại mở 'Return to the runway on February 23' sau B31 đã làm đúng việc đó. B29–B30 cũng vừa nêu ba ngày rồi đọc lại theo dạng hỏi–đáp.",
        "story": [2, 2, 1, 2, 1, 2, 2, 1],
        "story_reasons": ["Mở ở thay đổi phương thức giao hàng có ngày.", "Địa hình, căn cứ, đường và câu hỏi Pegasus rõ.", "Có tiếp cận/chiến đấu/phản ứng; nhiều beat diễn giải điều beat trước đã cho thấy.", "Pallet/LAPES và đường/cầu/bypass biến thông số thành cơ chế.", "Dùng lặp 'That distinction matters', 'not just', 'different tasks' để nói lại hành động.", "Hậu cần và địa hình làm thay lựa chọn; không ép thắng lợi thay thế.", "Nguồn quân sử có locators; hạn chế góc nhìn Mỹ và phạm vi tổn thất đã ghi trong dossier.", "Đáp án rõ từ trước kết; bốn kết nối tiếp làm giảm lực câu cuối."],
        "retention": [2, 1, 1, 2, 1],
        "retention_reasons": ["C-130 ngừng đáp nhưng hàng tiếp tục đến là hook có thực.", "B13–B17 và B29–B34 có nhiều lớp nhắc lại.", "Giữ câu hỏi nhưng một số đoạn chuyển như nhãn bài học thay vì hệ quả.", "Rất nhiều hành động/hình học dùng được: kéo pallet, tiếp tế đồi, sửa cầu.", "Chặng kết tái kể thay vì dừng tại hệ quả đường đã thông."],
        "fixes": ["Giữ một kết duy nhất từ B31–B34; gộp B29–B30 thành chuỗi diễn tiến có nhãn ngày, giữ khác nhau giữa link-up và mở đường nhưng không đọc lại ba lần.", "Đưa thiếu nước ở một chốt vào mạch hạn chế trực thăng; giữ tính địa phương trong một cụm 'at one outpost', không cần thêm cả beat để cảnh báo không phải mọi chốt.", "Cho thấy hậu quả chiến đấu đã ghi nhận ở các điểm then chốt. Nếu thêm tổn thất/đối phương, phải xác định phạm vi và kiểm tra nguồn; không bỏ chi phí con người chỉ vì khó có tổng số toàn trận."],
        "dna": "Tác chiến có thể kể qua hậu cần, nhưng giải thích kỹ thuật phải đổi khả năng giao hàng/di chuyển; sau khi chuỗi hành động đã trả lời, không thêm nhiều beat diễn giải cùng một kết luận.",
        "example": "'The link-up came on April 8. Route 9 was declared open three days later: reaching the base and restoring its road were separate jobs.' Đoạn thử gộp mốc, không thay lời đã duyệt.",
    },
    "status-and-systems": {
        "master": "master-narration.md", "start": "On Thursday", "stop": None,
        "title": "SVB: luận điểm tốt, trải nghiệm người gửi tiền chưa thành trục",
        "summary": "Sự khác nhau giữa bảo hiểm thông thường và ngoại lệ khẩn cấp là đáp án mạnh. Tập hiện nặng đọc báo cáo/số tổng; khách hàng xuất hiện như nhóm thống kê hơn là cùng một nhiệm vụ giữ tiền hoạt động xuyên suốt.",
        "quotes": [
            ["B01", "On Thursday, March 9, 2023, Silicon Valley Bank customers submitted requests to wire $54 billion out of the bank."],
            ["B05", "And selling a security to meet a sudden withdrawal can turn a paper loss into a realized one."],
            ["B12", "The $250,000 limit had not secretly meant “everything.”"],
        ],
        "stall": "B05 (71,61 giây) giải thích lãi suất tăng → chứng khoán giảm giá → bán để trả tiền → lỗ thực hiện, rồi lặp lại cùng cơ chế ngay đoạn tiếp. Bộ số requested/completed/queued/canceled xuất hiện ở B01, B08, B12. Beat dài nhất B09 (86,7 giây) chủ yếu trở lại findings đã nêu B02.",
        "story": [1, 2, 1, 2, 1, 1, 2, 1],
        "story_reasons": ["Sự kiện rõ nhưng bốn trạng thái tiền chiếm hook trước khi có việc cần làm của người gửi.", "Ngày, Mỹ/California và hai quyền hạn rõ.", "Có trước/sau đóng cửa nhưng phần tổng hợp báo cáo ngắt nhiệm vụ của khách hàng.", "Phân biệt requested/sent, duration/maturity và per ownership category đúng trong hồ sơ kiểm tra.", "Mật độ số, cơ quan và qualification cao; B05 lặp liền nhau.", "Có quy tắc và đối chiếu nhóm, nhưng nhiệm vụ dịch vụ/khác biệt tiếp cận của cùng tình huống chưa hiện rõ.", "Không gán tư tưởng người gửi; tách tương quan/nguyên nhân và chính sách/luật hiện hành.", "Hai quyền hạn được giải quyết nhưng quay lại bốn số thêm một lần."],
        "retention": [1, 1, 1, 1, 1],
        "retention_reasons": ["Tiền rút lớn có lực, câu hỏi 'ai/quy tắc đổi gì' đến sau sổ cái.", "Lặp cơ chế B05 và bộ số ba lần.", "B10 Friday plan → Sunday exception → Monday access là chuỗi mạnh nhất nhưng xuất hiện muộn.", "Có thể dùng cùng màn hình/quyền rút tiền; nhiều số hiện không cần cùng lúc.", "Đáp án chính đáng nhưng human consequence còn trừu tượng."],
        "fixes": ["Giữ cùng nhiệm vụ: tiền gửi dùng để thanh toán hoạt động. Theo quyền tiếp cận trước đóng cửa → phương án thứ Sáu → ngoại lệ Chủ nhật → truy cập thứ Hai, theo hồ sơ có thật. Không tạo khách hàng/lời khai thật giả.", "B05 giữ một lần giải thích chênh thời gian giữa tài sản và tiền gửi; B08 mới mở chi tiết hàng chờ khi nó thay cách hiểu tốc độ rút.", "Nói rõ kết quả so sánh nhóm và ngoại lệ mà nguồn cho phép; không thay 'more likely' thành ai đã rút đầu tiên. Xem lại title 'Who ran first' vì bài hiện chứng minh xu hướng theo nhóm, chưa kể một thứ tự đầy đủ."],
        "dna": "Đơn vị kể là cùng một việc người dùng cần làm và quyền tiếp cận thay đổi khi quy tắc đổi. Có thể dùng so sánh nhóm có dữ liệu hoặc ví dụ được gọi rõ là minh họa, nhưng không để lịch sử ngân hàng thay toàn bộ trải nghiệm.",
        "example": "'Friday's plan gave insured depositors a route to their money. By Sunday, officials had extended protection to all SVB deposits, with access from Monday. The ordinary limit had not changed; the authority used for this failure had.' Đoạn thử phải giữ các chi tiết thủ tục cần thiết ở toàn bản.",
    },
    "chikyu-shikumi": {
        "master": "research/narration-sapporo-snow-v1.md", "start": "冬の札幌", "stop": "## ",
        "title": "Sapporo: gọn và đúng kênh nhất về cấu trúc; còn lặp và nặng số",
        "summary": "Câu hỏi đời thường, có tuyến vật chất và giới hạn vận hành cụ thể. Trong sáu bản, đây là cấu trúc gọn và ít mang giọng quản trị nghiên cứu hơn; đánh giá tiếng Nhật vẫn cần người bản ngữ và nghe giọng.",
        "quotes": [
            ["b01", "道の脇に残った雪は、次にどこへ運ぶのでしょう。"],
            ["b08", "その水は、真冬でもおおむね15度前後を保っています。"],
            ["b15", "札幌では、雪は道路から消えたあとも、街のしくみの中を移動し続けます。"],
        ],
        "stall": "b09–b10 (68,09 giây) mở lại cùng chức năng mùa mưa trữ nước/mùa đông tan tuyết của Fushikogawa. Beat dài nhất b04 (39,23 giây) dồn 81 bãi, 2.679 vạn m³ kế hoạch và 1.458 vạn m³ thực nhận năm khác, rồi giải thích vì sao không nên so trực tiếp.",
        "story": [2, 2, 1, 2, 1, 2, 2, 2],
        "story_reasons": ["Câu hỏi dễ hiểu từ tuyết còn ở mép đường.", "Địa điểm, dịch vụ và câu hỏi rõ; không gộp cả Nhật.", "Tuyến tuyết có tiến nhưng b09–b10 lặp cơ sở theo mùa.", "Nhiệt, đường vận tải và giới hạn khoảng 1/10 có chức năng.", "Nhận xét sơ bộ trên văn bản; chưa có bản ngữ kiểm âm/cách đọc, câu b01 '押し寄せます' cần rà đúng chủ thể.", "Tiếng Nhật giải thích process gắn đời sống, không mượn banter.", "Nêu niên độ, plan/actual, treated/untreated và phạm vi cơ sở.", "Kết tự nhiên trở về công việc của thành phố, không đọc lại toàn tuyến."],
        "retention": [2, 1, 1, 1, 2],
        "retention_reasons": ["Một câu hỏi đời thường rõ ngay 15 giây đầu.", "Vai trò Fushikogawa được giới thiệu lại ở hai beat liên tiếp.", "Nhiệt nước thải đến b07, sau khoảng 2:43 speech; có thể nối trực tiếp từ quãng xe dài để lộ đáp án mới sớm hơn.", "Phân nhánh tuyết và các loại cống cần ít thuật ngữ hơn trong cùng đoạn.", "Đáp án và giới hạn về lượng xử lý đủ rõ."],
        "fixes": ["Gộp b09–b10: giới thiệu cơ sở một lần, sau đó dùng số vận hành để cho thấy quy mô nếu thật sự cần.", "b04 chọn chỉ số phù hợp câu hỏi. Nếu muốn so sánh kế hoạch và thực tế, nghiên cứu cùng niên độ; nếu không thì bỏ một dãy số thay vì dùng thời lượng để giải thích phép so không dùng được.", "Nối quãng xe/thiếu xe với cơ sở dùng nhiệt nước thải; giữ treated/untreated đúng tại nhánh tương ứng. Không kéo bản 6:40 thành 10/20 phút bằng các loại cơ sở thêm vào danh sách."],
        "dna": "Giữ ngữ pháp Nhật theo hành trình một dịch vụ thật; thuật ngữ đến sau chức năng. Một cơ sở được giải thích một lần; sau đó chỉ trở lại khi trạng thái, lượng hoặc giới hạn đổi.",
        "example": "'伏古川の貯留管は、雨の時期には水をため、冬には処理水の熱で雪を融かします。' Câu thử gộp chức năng; cách đọc tên và toàn câu vẫn cần người Nhật rà.",
    },
    "vi-sao-noi-nay": {
        "master": "research/narration-ca-mau-v2.md", "start": "Ở Huong Mai", "stop": "## Biên tập",
        "title": "Cà Mau: nghịch lý tốt, hành trình hạt bùn bị thay bằng chuỗi tóm tắt nghiên cứu",
        "summary": "Câu 'sóng giảm, bùn chưa bồi' rất đúng kênh và cơ chế có chất liệu hình tốt. Nhưng sau lời hứa theo hạt bùn, bản thảo dành nhiều thời gian đi qua nghiên cứu 2022/2025/2026 và cách đánh giá chúng; đời sống địa phương đến muộn và còn chung chung.",
        "quotes": [
            ["B03", "Muốn trả lời, ta phải theo cả con sóng lẫn hạt bùn, thay vì chỉ nhìn vào bức tường ngoài biển."],
            ["B17", "nhưng hiện ta mới kiểm tra được phần tóm tắt và các trích đoạn của nhà xuất bản."],
            ["B22", "Trở lại Huong Mai: sóng giảm không có nghĩa bờ đã được cứu."],
        ],
        "stall": "B13–B17 (~147 giây) chuyển từ vật lý sang cách đọc ảnh, các loại nghiên cứu và quyền hạn của người nghiên cứu. B17 nói thẳng việc agent chỉ đọc abstract. B20 thêm 'Ta không nên biến...' là lời hướng dẫn người viết. B21–B23 trả lại cùng đáp án ba nhịp. Beat dài nhất B16 40,38 giây.",
        "story": [2, 1, 1, 1, 1, 1, 2, 1],
        "story_reasons": ["Nghịch lý giảm sóng/không tích bùn có địa điểm và nguồn.", "Phạm vi theo thời gian có, nhưng hệ quả với cuộc sống địa phương không hiện rõ sớm.", "Hạt bùn chưa đi xuyên một điều kiện thay đổi; bài chuyển thành literature review.", "Cơ chế lắng/cuốn lại hữu ích; nhiều kết quả vùng/thiết kế chỉ được nêu mà không thành đối chiếu.", "Huong Mai/Tieu Dua chưa bản địa hóa; nhiều câu 'ta chưa dùng/không nên' hướng về người viết.", "Có địa điểm và câu hỏi; đời sống và hành trình nhân quả chưa đủ trong phần thực tế.", "Không bịa hộ dân/thu nhập; ranh giới nguồn nêu rõ. Vấn đề là cách trình bày chứ không nên bỏ giới hạn quan trọng.", "Đáp án có nhưng kết B21–B23 lặp và biến thành lời dặn cách đo."],
        "retention": [2, 1, 1, 1, 1],
        "retention_reasons": ["B03 trả đúng tò mò từ công trình nhìn có vẻ làm đúng việc.", "Cùng kết luận sóng giảm chưa đủ lặp qua nhiều mốc nghiên cứu.", "Nối theo năm bài báo, chưa theo sự đổi trạng thái của bùn.", "Mặt cắt có thể rõ nhưng bốn loại đê và các phương pháp không có so sánh cụ thể tương xứng.", "Hệ quả sinh kế là khả năng chung; đoạn kết vẫn chủ yếu nói về quan trắc."],
        "fixes": ["Giữ nghịch lý, dùng đúng Hương Mai/Tiểu Dừa sau khi xác minh vị trí. Theo dòng có trầm tích → sóng qua đê → điều kiện lắng/cuốn lại → dấu hiệu trên bãi; không gán đường hạt bùn giả là phép đo thật.", "Cắt/gộp literature review thành kết quả phục vụ cơ chế; giữ năm/phạm vi bằng cụm tự nhiên. Full-text chưa đọc thuộc ledger; narration chỉ giữ giới hạn điều khẳng định. Dùng nghiên cứu 2026 để đặt câu hỏi đối chiếu, chưa kết luận địa điểm cụ thể khi chưa đủ dữ liệu.", "Bổ sung một hệ quả địa phương có hồ sơ nếu muốn khẳng định đời sống; nếu không đủ nguồn, nói đúng điều bãi/rừng thay đổi và dừng. Gộp B21–B23 thành một kết."],
        "dna": "Lời hứa theo một dòng nước/hạt bùn/chuyến hàng phải hiện thành chuỗi trạng thái trong lời. Tên nghiên cứu và năm không thay cho hành động. Tên địa phương cần tiếng Việt đúng; hậu quả con người có thể ngắn nhưng phải cụ thể và có nguồn.",
        "example": "'Ở Hương Mai, công trình đã làm yếu sóng. Nhưng nghiên cứu tại đây không ghi nhận bùn mịn tích tụ như mong đợi. Sóng đã giảm; điều còn phải giải thích là vì sao bùn chưa ở lại.' Đoạn thử chỉ dùng kết quả có nguồn, không đoán nguyên nhân riêng của địa điểm.",
    },
}

PROPOSAL = """# Đề xuất chỉnh DNA sau sáu tập mới — 17/10/2026

Trạng thái: đề xuất biên tập, chưa thay DNA/profile đang chạy và chưa sửa lời dẫn đã duyệt. Bằng chứng và điểm từng tiêu chí ở REPORT.md/assessment.json. Đây là một tập mẫu trên mỗi kênh, không đủ xác lập hiệu quả khán giả hoặc một quy luật cho mọi tập.

## Giữ nền hiện hành

Giữ sáu phạm vi kênh, documentary dựa trên nguồn, viết lời liên tục trước shot, ngôn ngữ bản địa, phân biệt reconstruction/illustration/fact và duyệt lời trước sản xuất. Không giải quyết sự khô bằng nhân vật bịa, lời khai bịa, tình huống giả hay nhịp gây sốc cố định. Không biến callback, một dòng vật chất hoặc bảo trì thành phần phải có trong mọi tập.

## Đoạn đề xuất thay vì thêm nhiều checklist lặp

### 1. Nguyên tắc diễn tiến và giọng kể

Mỗi đoạn phải làm đổi hiểu biết về cùng sự kiện, địa điểm hoặc việc người dùng đang cần làm: một hành động xảy ra, điều kiện thay đổi, so sánh có kết quả, lựa chọn hẹp đi hoặc hệ quả hiện ra. Câu giải thích chỉ cần khi nó giúp hiểu sự đổi đó. Kiểm tra đoạn liền trước và sau; xóa phần chỉ nói lại đáp án bằng từ khác. Không biến mỗi bước thành một beat rồi thêm một beat 'điều này có nghĩa là'.

Giữ điều kiện thực sự làm thay đổi kết luận: năm, nơi, phạm vi, giả thuyết, đại lượng kế hoạch/thực tế và dữ liệu tổng/hộ gia đình. Nói các điều kiện đó tại luận điểm cần nó. Nhật ký truy cập, việc chỉ đọc abstract, giới hạn tool và lời nhắc 'ta không nên bịa' thuộc dossier/review. Nếu một hạn chế nguồn khiến luận điểm thiết yếu chưa đủ, thu hẹp luận điểm hoặc nghiên cứu thêm; không dùng một đoạn disclaimer để hợp thức hóa kết luận quá rộng. Chỉ kể phương pháp điều tra khi chính phép đo/phát hiện ấy làm đổi lời giải của câu chuyện.

Mở bằng điều quan sát được và câu hỏi cụ thể. Đưa số vào khi nó giải thích quy mô, tỷ lệ, ngưỡng, tốc độ hoặc chênh lệch có hệ quả. Ưu tiên quan hệ rồi đến số cần giữ; bỏ dãy số không phục vụ câu hỏi thay vì đọc dãy số rồi giảng vì sao không so được. Không có số lượng số cứng cho mỗi phút.

Kết một lần khi đáp án và hệ quả đã đủ. Trở lại hình ảnh đầu nếu ý nghĩa đã đổi; không bắt buộc đọc 'Return to...' hoặc đi lại toàn tuyến. Một qualification không cần xuất hiện lại chỉ để báo rằng người viết vẫn thận trọng.

### 2. Sáu execution_check nên thay nội dung riêng của mẫu cũ

- last-safe-minute: 'Follow the documented change, exposure/impact, available information, response and aftermath. An investigation-led episode may follow evidence changing the causal model, but must connect findings to affected communities and actual mitigation. Do not invent a warning or rescue to fill missing records; state the remaining gap in review.'
- terra-rewired: 'Follow the selected material/service route through an operating constraint, supported response and everyday consequence. Each branch must change the route or explain a dependency; do not repeat the network inventory. A historical segment is useful only where it explains the present mechanism.'
- battlefield-bearings: 'Orient parties, terrain, objective and available information; show supported contact, response, logistics and local consequences. Technical details must change what forces or crews can do. Keep outcome and casualty scope explicit, and close once the operational question is answered.'
- status-and-systems: 'Keep one human task or comparable service constant as a sourced rule, access condition or incentive changes. Show the bounded result for the compared cases, with material jurisdiction, date and eligibility. Distinguish observed group behavior from individual motives; do not substitute company chronology for the user experience.'
- chikyu-shikumi: '自然な日本語で、同じ場所の雪・水・人やサービスの流れを、条件の変化と暮らしの結果までたどる。設備は機能から説明し、同じ仕組みを繰り返さない。計画・実績・対象範囲は必要な箇所で示し、地名と読み方は日本語資料で確認する。音声と母語話者の確認は別に記録する。'
- vi-sao-noi-nay: 'Theo một địa điểm và dòng vật chất/hành động cụ thể qua điều kiện thay đổi tới kết quả và hệ quả địa phương có nguồn. Lời hứa hành trình phải hiện trong đoạn thực tế; không thay bằng chuỗi tóm tắt nghiên cứu. Dùng tên nơi bằng tiếng Việt đúng, giữ niên độ/phạm vi cần thiết ngay ở dữ kiện.'

evidence_limit trong profile chỉ nên nói giới hạn của loại bằng chứng, không giữ nhận xét về độ dài hay nội dung của một mẫu audit như đó là tình trạng của mọi tập sau. Những câu 'không lặp overtopping', 'spend/base rewards/bonus' và 'mẫu chưa bao quát toàn trận' cần chuyển về hồ sơ audit tương ứng. Không đưa chúng thành yêu cầu cho hồ Nyos, SVB hay một chiến dịch khác.

### 3. Hai review vẫn tách, nhưng bám một phiên bản thật

Chấm /16 và /10 trên toàn lời hiện hành; ghi đường dẫn và SHA-256 của phần lời, không chỉ tên 'v1/v2'. Dẫn đúng opening, turn, ending và đoạn đứng lâu. Điểm 2 cho tiến triển/channel fit phải được chứng minh bằng thay đổi thấy trong văn bản; một câu hứa 'theo hạt bùn' không chứng minh rằng cả bài đã thực hiện. Điểm qua ngưỡng không lấn át một thiếu hụt quan trọng. Tên review, mô tả 'đã xóa' và text phải khớp.

Khi chia beats, đối chiếu lại phần lời với bản duyệt. Trường hợp sáu tập này, cả sáu khớp sau chuẩn hóa khoảng trắng; vấn đề Cà Mau là review mô tả sai việc đã xóa số, không phải beats tự phục hồi một bản cũ. Cà Mau còn khác chuỗi topic giữa root và episode_context; cần xác nhận cùng phạm vi rồi đồng bộ nhãn, không đổi chủ đề hoặc slug để lách kiểm tra.

### 4. Runtime dùng đo giọng, không lấy ngân sách ảnh làm thời lượng lời

Lập kế hoạch bằng số đơn vị lời và giọng/ngôn ngữ hiện hành; dùng tốc độ đã đo ở những tập này như điểm xuất phát, chưa phải chuẩn ổn định. Giữ punctuation, pause và nội dung trong phép so. Tiếng Việt đếm đơn vị cách trắng không tương đương từ tiếng Anh; tiếng Nhật dùng ký tự phù hợp phép đo.

Trong mẫu hiện có: English khoảng 124–131 đơn vị/phút; VieNeu của tập Cà Mau khoảng 201 đơn vị cách trắng/phút; Nhật khoảng 328 ký tự không khoảng trắng/phút. Dự toán 20 phút tương ứng gần 2.490–2.630 đơn vị English, 4.010 đơn vị Việt hoặc 6.550 ký tự Nhật. Chỉ áp dụng cho planning cùng route/setting và phải đo TTS được duyệt; không viết đủ con số bằng lặp ý. Cập nhật sau nhiều đoạn/tập và có sample timing đại diện. Những ngoại lệ độ dài đã được người dùng chấp nhận vẫn có giá trị.

## Thứ tự triển khai đề xuất

1. Sửa execution_check đang mang nội dung mẫu cũ và nguyên tắc qualification/diễn tiến/kết ở nguồn canonical; đồng bộ các điểm trỏ mà không chồng thêm bản DNA cạnh tranh.
2. Dùng ba đoạn ngắn thử trên Cà Mau (nguồn nói thành hành trình), SVB (cùng nhiệm vụ dưới hai quyền hạn), Khe Sanh (một kết). So đoạn cũ/mới và review thực tế trước khi thay lời đã duyệt.
3. Dùng tốc độ TTS đo được để định ngân sách tập sau, rồi kiểm tra lại bằng voice. Không tự kéo dài sáu tập hiện hành.
4. Khi có dữ liệu phát hành, kiểm tra intro/dips/traffic context để đánh giá giả thuyết. Bản audit này chỉ xác lập vấn đề biên tập có thể chỉ ra trong text.
"""


def norm(text):
    return " ".join(text.split())


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def mmss(sec):
    return f"{int(sec)//60:02d}:{sec%60:05.2f}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for c in channels.load_channels():
        r = dict(REVIEWS[c["id"]])
        episodes = [p for p in Path(c["destination"]).iterdir()
                    if p.is_dir() and not p.name.startswith("_") and (p / "beats.json").exists()]
        if len(episodes) != 1:
            raise RuntimeError(f"Select explicit current episode: {c['id']}: {episodes}")
        ep = episodes[0]
        d = json.loads((ep / "beats.json").read_text(encoding="utf-8-sig"))
        text = "\n\n".join(b["narration"] for b in d["beats"])
        master_path = ep / r["master"]
        master = master_path.read_text(encoding="utf-8-sig")
        master = master[master.index(r["start"]):]
        if r["stop"]:
            master = master.split(r["stop"])[0]
        assert norm(master) == norm(text), f"Narration mismatch: {ep}"
        beats = {b["id"]: b for b in d["beats"]}
        for bid, quote in r["quotes"]:
            assert quote in beats[bid]["narration"], (c["id"], bid, quote)
        try:
            channels.authoring_context(c["id"], ep.name)
            context_status = "ok"
        except SystemExit as exc:
            context_status = str(exc)
        seconds = sum(b.get("narration_dur", 0) for b in d["beats"])
        units = len(text.split()) if c["language"] != "ja" else len(re.sub(r"\s", "", text))
        qa = json.loads((ep / "captions-qa.json").read_text(encoding="utf-8-sig"))
        r.update({
            "channel_id": c["id"], "channel": c["display_name"], "language": c["language"],
            "slug": ep.name, "episode_dir": str(ep), "master_path": str(master_path),
            "topic": d["topic"], "recorded_topic": d.get("episode_context", {}).get("topic"),
            "beats_file_sha256": sha((ep / "beats.json").read_text(encoding="utf-8-sig")),
            "narration_sha256_normalized": sha(norm(text)), "master_matches_beats": True,
            "speech_seconds": round(seconds, 2), "speech_runtime": mmss(seconds),
            "unit_count": units, "unit": "ký tự không khoảng trắng" if c["language"] == "ja" else "đơn vị cách trắng",
            "units_per_minute": round(units / seconds * 60, 2),
            "story_total": sum(r["story"]), "retention_total": sum(r["retention"]),
            "context_status": context_status, "caption_qa_status": qa.get("status"),
            "live_execution_check": c.get("writing_contract", {}).get("execution_check"),
            "live_evidence_limit": c.get("writing_contract", {}).get("evidence_limit"),
        })
        results.append(r)

    metadata = {
        "review_date": "2026-10-17", "timezone": "Asia/Bangkok",
        "basis": "Text-only editorial re-review by one reviewing agent in two separate passes; not an external blind review or audience analytics.",
        "scope": "All narration in six current beats.json files; matched to stated approved/master text after whitespace normalization; handoffs, briefs and source ledgers inspected. No complete video/audio review or comprehensive fact check.",
        "versions": "Cà Mau episode narration-ca-mau-v2.md is a current episode revision, distinct from the six deleted editorial V2 samples. None of those retired samples was opened or reconstructed.",
        "reviews": results,
    }
    (OUT / "assessment.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Đánh giá lại sáu kịch bản đã sản xuất — 17/10/2026", "",
        "**Kết luận:** giữ định vị sáu kênh; cần chỉnh cách thực thi DNA để lời kể đi theo sự thay đổi và hệ quả, giảm giọng review nghiên cứu, giảm lặp và kết nhiều lần. Nền nguồn tương đối cẩn thận không tự bảo đảm câu chuyện hấp dẫn.", "",
        "## Phạm vi và phiên bản", "",
        "Đọc toàn bộ lời trong sáu beats.json hiện hành, đối chiếu bản master/lời dẫn đã chỉ định trong handoff, đọc brief/handoff, profile sống, ledger và review sẵn có. Cả sáu bản master khớp beats sau chuẩn hóa khoảng trắng. Điểm mới là đánh giá biên tập trên văn bản của một agent, hai lượt story/retention tách biệt; không phải hội đồng độc lập, đánh giá nghe/nhìn hay dự báo retention. Không mở mẫu editorial V2 đã xóa. File 'narration-ca-mau-v2.md' thuộc tập Cà Mau mới và là revision hiện hành, không phải bộ mẫu cũ.", "",
        "Thời lượng dưới đây cộng narration_dur từ beat đã có audio; mốc khi dẫn beat là thứ tự lời, không phải timecode MP4 vì video có đuôi hình. Ngoại lệ độ dài đã được chấp nhận được tôn trọng; ngắn không tự là lỗi, thiếu chất liệu so với lời hứa mới là lỗi.", "",
        "## So sánh nhanh", "",
        "| Kênh / tập | Lời đọc | Story /16 | Retention /10 | Channel fit /2 | Vấn đề chính |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for r in results:
        lines.append(f"| {r['channel']} / {r['slug']} | {r['speech_runtime']} | {r['story_total']} | {r['retention_total']} | {r['story'][5]} | {r['title'].split(':',1)[-1].strip()} |")
    lines += ["", "Các điểm không dùng để xếp hạng thị trường, ngôn ngữ hoặc chất lượng thành phẩm. Tiêu chí khắt khe hơn review cũ vì xét đóng góp từng đoạn và toàn mạch; điểm cũ 15/16, 9/10 không được coi là chuẩn vàng.", "", "## Vấn đề chung có bằng chứng", "",
        "1. **Quy tắc đã có nhưng chưa được thực thi.** scripting-dna.md đã yêu cầu nguồn quản trị ở ngoài speech, không lặp, payoff thật. Cà Mau B17/B20 và Khe Sanh B31–B34 cho thấy vấn đề áp dụng/review, chưa có bằng chứng rằng chỉ thêm checklist sẽ sửa được.",
        "2. **Chất thận trọng đang lấn giọng kể.** Giữ uncertainty làm đổi kết luận; chuyển access log và lời dặn người viết ra khỏi narration. Nyos phải giữ kích hoạt chưa biết, SVB phải giữ request khác outflow, Cà Mau phải giữ phạm vi nghiên cứu. Không xóa qualification cần thiết để tăng nhịp.",
        "3. **Thông tin chưa luôn thành thay đổi.** B08–B09 Terra đi lại sơ đồ; b09–b10 Nhật lặp chức năng; SVB B05 lặp cơ chế trong cùng beat. Cần làm rõ đoạn nào thêm trạng thái/hệ quả trước khi chia shot.",
        "4. **Kết thành nhiều kết.** Khe Sanh bốn beat cuối khoảng 100 giây; Cà Mau B21–B23 ba nhịp đáp lại. Năm trong sáu tập dùng lời gọi trở lại rõ ('Return', 'Now return', 'Trở lại'); riêng lối Nhật cho thấy có thể đóng vòng tự nhiên mà không nói công thức ấy.",
        "5. **Con người chưa thành hệ quả cụ thể.** Nêu 'people/daily life' trong profile không đủ. SVB cần cùng nhiệm vụ tiếp cận tiền; Nyos cần phản ứng/hậu quả có hồ sơ; Cà Mau cần kết quả bãi/rừng/đời sống địa phương. Không chữa bằng nhân vật thật giả hoặc suy nghĩ bịa.",
        "6. **Bản dài được dự tính bằng tốc độ chưa đo.** 1.873 đơn vị cách trắng Việt thành 9:20, 2.186 ký tự Nhật thành 6:40. Con số ảnh/900 giây không quyết định thời lượng lời. Dùng số đo hiện có để lập kế hoạch tập sau rồi xác nhận TTS; không kéo dài các ngoại lệ đã duyệt.",
        "7. **Contract dùng chung đang chứa việc của một mẫu cũ.** LSM execution_check nói 'overtopping', Status nói 'spend, base rewards and bonus'; chúng không áp dụng cho hồ Nyos/SVB. evidence_limit của một số kênh còn nói về thiếu hụt mẫu audit. Chuyển chi tiết mẫu về hồ sơ mẫu, thay bằng nguyên tắc theo kênh.", "",
        "## Sáu lượt story edit và retention tách biệt", "",
    ]
    for r in results:
        lines += [f"### {r['channel']} — {r['title']}", "", r["summary"], "",
                  f"Nguồn lời: [{r['master']}]({Path(r['master_path']).as_posix()}) · speech {r['speech_runtime']} · {r['unit_count']} {r['unit']} · fingerprint `{r['narration_sha256_normalized']}`.", ""]
        for label, (bid, quote) in zip(["Mở", "Giữa/cơ chế", "Kết"], r["quotes"]):
            lines += [f"**{label}, {bid}:** “{quote}”", ""]
        lines += ["**Đoạn đứng/lặp:** " + r["stall"], "", f"**Story edit: {r['story_total']}/16.**"]
        for name, score, reason in zip(STORY, r["story"], r["story_reasons"]):
            lines.append(f"- {name}: {score}/2 — {reason}")
        lines += ["", f"**Retention: {r['retention_total']}/10.**"]
        for name, score, reason in zip(RETENTION, r["retention"], r["retention_reasons"]):
            lines.append(f"- {name}: {score}/2 — {reason}")
        lines += ["", "**Ưu tiên sửa:**"]
        lines.extend(f"- {fix}" for fix in r["fixes"])
        lines += ["", "**Đề xuất DNA kênh:** " + r["dna"], "", "**Đoạn thử minh họa, chưa thay lời đã duyệt:** " + r["example"], ""]
    lines += [
        "## Hồ sơ/version và giới hạn phê duyệt", "",
        "- **Cà Mau:** review hiện hành nói v2 đã xóa hai tốc độ xói lở, nhưng approved text lẫn beats B05 vẫn có khoảng 35 m/năm và 10 m/năm. Đây là mô tả review sai so với text; không có bằng chứng beats khác master. Cần sửa review và nếu sửa lời thì duyệt revision mới.",
        "- **Cà Mau context:** topic root là 'Vì sao đê giảm sóng ở Cà Mau chưa chắc tạo bãi bồi?' còn recorded topic là câu hỏi hai đoạn bờ bồi/lở. channels.py context hiện từ chối vì chuỗi khác nhau. Hai câu có vẻ cùng phạm vi nhưng cần xác nhận nhãn; không lách bằng rebinding sang chủ đề khác. Audit đọc beats/master và profile sống, ghi lỗi rõ.",
        "- **Địa danh Việt:** lời hiện hành giữ Huong Mai/Tieu Dua. Công báo Cà Mau ghi Hương Mai/Tiểu Dừa; cần kiểm tra chính xác điểm khảo sát trên bản đồ trước khi bản địa hóa nhãn/đọc. Không suy địa giới hiện nay từ tên trong nghiên cứu cũ.",
        "- **Hồ sơ giai đoạn:** một số brief và đầu file lời còn nói chưa voice/render dù handoff đã ghi render xong. Handoff mới hơn dùng để xác định production state; nhãn cũ không chứng minh thiếu bản duyệt.",
        "- **Sáu captions-qa đều needs_review.** Chưa nghe trọn audio/video trong audit này; không kết luận giọng máy, nhạc hay crop tốt/xấu từ lời viết. Đó là việc riêng trước giao thành phẩm.",
        "- Một số kênh chưa đạt 2/2 channel fit trong lượt đánh giá mới. Điều này là đề nghị sửa cho revision/tập tới, không tự thu hồi chấp nhận thời lượng hay sửa media đã duyệt.", "",
        "## Kiểm tra nguồn có giới hạn ngày 17/10/2026", "",
        "Kiểm tra dưới đây xác nhận một số luận điểm then chốt, không phải full fact-check. Không phát hiện lý do để cáo buộc sáu tập bịa nguồn chỉ vì nguồn có mốc 2026.", "",
        "- FDIC: [thông cáo 14/05/2026](https://www.fdic.gov/news/press-releases/2026/fdic-releases-staff-study-deposit-flows-three-failed-banks-spring-2023) xác nhận nghiên cứu ba ngân hàng và khác biệt nhóm gửi tiền. PDF trực tiếp bị 403; tìm kiếm có indexed text, nhưng audit này chưa kiểm lại mọi hàng $54/$41/$12,1 tỷ trong bảng gốc. Không xem đó là bằng chứng thứ tự tất cả người rút.",
        "- Sapporo: [trang thành phố cập nhật 04/08/2026](https://www.city.sapporo.jp/gesui/kaitei2026.html) xác nhận khoảng 15°C và cơ sở nước thải xử lý khoảng 1/10 tổng lượng tuyết thải. Xác nhận lõi b08/b13, chưa kiểm mọi số capacity/actual.",
        "- Hong Kong: [WSD về Đông Giang](https://www.wsd.gov.hk/en/water-matters/harvesting-water/06/) có kỳ ngừng cấp tháng 12 và bảo trì 20 ngày. Đây là phụ thuộc vận hành có nguồn, không cần tạo khủng hoảng giả.",
        "- Cà Mau: [repository bài 2021](https://researchonline.jcu.edu.au/78647/) hỗ trợ nghịch lý giảm năng lượng sóng nhưng không có bằng chứng tích bùn mịn tại điểm khảo sát. [Publisher/index bài 2026](https://www.sciencedirect.com/science/article/pii/S027277142600418X) xác nhận volume 341, 15/10/2026 và khảo sát 32 tuyến/75 km; truy cập full text còn hạn chế. Không dùng abstract để xác lập quan hệ nhân quả chi tiết cho một xã/hộ.",
        "- Khe Sanh và Nyos: đọc lại ledger có locators và nguồn quân sử/USGS. Một số endpoint web trực tiếp không trả text; không coi việc có URL hoặc score cũ là đã kiểm toàn văn nguồn trong audit này.",
        "- Địa danh: [Công báo Cà Mau số 111/2023](https://congbao.camau.gov.vn/Admin/OfficialGazetteStorage/SoCongBao/cong_bao_so_111_12-12-2023-signed.pdf) ghi Hương Mai/Tiểu Dừa; đối chiếu nguồn địa phương thay vì tự thêm dấu theo phỏng đoán.", "",
        "## Đối chiếu tham chiếu và điều chưa thể kết luận", "",
        "Dùng dated evidence sẵn có, không gọi đây là một lượt xem lại toàn bộ đối thủ. Khe Sanh có sampled translated/auto captions của Legends of Vietnam, FVqSe1e4Xig, 16/10/2026 (0:00–0:58; 4:28–4:58; 12:20–14:17); chỉ đủ so cấu trúc. Terra có transcript trường học From Source to Tap; tải thông tin/khán giả khác nên không phải chuẩn chất lượng adult explainer. SVB chủ yếu metadata của WSJ/CNN/FDIC, không đủ chấm spoken ending đối thủ. Nhật chủ yếu metadata/news/official short, không đủ kết luận lời Nhật hơn bản ngữ.", "",
        "Đã đọc lại transcript gốc Việt tự động eoMKQ1KLLlY lưu ngày 16/10: mở 0:00–0:47 đi qua chiều cao/dân số trước câu địa lý; giữa 2:51–3:36 nối vật liệu–đập–nước; cuối 4:43–5:45 mở rộng sang xuất khẩu/GDP. Nó cho thấy có thể học cách nối vật chất và nói gần người nghe, nhưng chính tham chiếu cũng có nhánh ngoài câu hỏi, nhận dạng tự động sai và dữ kiện cần kiểm riêng. Không dùng độ phổ biến, câu đùa hay kết quốc gia hóa của nó làm chuẩn bắt buộc. Tập Cà Mau khác chủ đề và thời lượng; không tuyên bố hơn/kém retention từ so sánh này.", "",
        "## Đề xuất áp dụng", "",
        "Đọc DNA_PROPOSED.md để xem phần quy tắc viết và execution_check cụ thể có thể thay vào nguồn canonical. Ưu tiên Cà Mau/SVB cho trục kể, Khe Sanh cho cắt lặp và kết, rồi các đoạn giữa của Terra/Nyos/Nhật. Đánh giá lại đoạn đã sửa trước khi đổi lời đã duyệt. Chưa thay config, active DNA, audio hoặc video trong đợt review này.",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "DNA_PROPOSED.md").write_text(PROPOSAL, encoding="utf-8")
    render_html(metadata)
    print(json.dumps({"report": str(OUT / "REPORT.md"), "proposal": str(OUT / "DNA_PROPOSED.md"), "reviews": [{"channel": r["channel_id"], "master_matches_beats": r["master_matches_beats"], "story": r["story_total"], "retention": r["retention_total"]} for r in results]}, ensure_ascii=False))


def render_html(data):
    # Standalone local view; the Canvas SDK/managed project path is unavailable here.
    cards = []
    esc = html.escape
    for r in data["reviews"]:
        quotes = "".join(f"<blockquote><b>{esc(bid)}</b> {esc(q)}</blockquote>" for bid, q in r["quotes"])
        scores = "".join(f"<tr><td>{esc(n)}</td><td>{s}/2</td><td>{esc(reason)}</td></tr>" for n, s, reason in zip(STORY, r["story"], r["story_reasons"]))
        ret = "".join(f"<tr><td>{esc(n)}</td><td>{s}/2</td><td>{esc(reason)}</td></tr>" for n, s, reason in zip(RETENTION, r["retention"], r["retention_reasons"]))
        fixes = "".join(f"<li>{esc(f)}</li>" for f in r["fixes"])
        cards.append(f'''<article data-id="{esc(r['channel_id'])}"><h2>{esc(r['channel'])}</h2><h3>{esc(r['title'])}</h3><p>{esc(r['summary'])}</p><p class="meta">Lời {r['speech_runtime']} · Story {r['story_total']}/16 · Retention {r['retention_total']}/10 · DNA {r['story'][5]}/2</p>{quotes}<p><b>Đoạn đứng/lặp:</b> {esc(r['stall'])}</p><h3>Ưu tiên sửa</h3><ol>{fixes}</ol><p><b>Đề xuất DNA:</b> {esc(r['dna'])}</p><details><summary>Điểm từng tiêu chí và bằng chứng</summary><h3>Story /16</h3><table><thead><tr><th>Tiêu chí</th><th>Điểm</th><th>Lý do</th></tr></thead><tbody>{scores}</tbody></table><h3>Retention /10</h3><table><thead><tr><th>Tiêu chí</th><th>Điểm</th><th>Lý do</th></tr></thead><tbody>{ret}</tbody></table><p>{esc(r['example'])}</p><p class="meta">Fingerprint lời: {r['narration_sha256_normalized']}</p></details></article>''')
    options = "".join(f'<option value="{esc(r["channel_id"])}">{esc(r["channel"])}</option>' for r in data["reviews"])
    page = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Đánh giá sáu kịch bản · 17/10/2026</title><style>body{font:16px/1.65 system-ui,sans-serif;color:#242b34;background:#f7f7f4;margin:0}main{max-width:1060px;margin:auto;padding:28px}h1{font-size:28px;line-height:1.25}h2{font-size:23px;margin-bottom:4px}h3{font-size:18px}header{border-bottom:2px solid #243c50;padding-bottom:24px}.meta{font-size:14px;color:#586471;overflow-wrap:anywhere}article{padding:26px 0;border-bottom:1px solid #c9ced2}blockquote{border-left:3px solid #9aa7b3;padding:8px 16px;margin:12px 0;background:#fff}select{font:inherit;padding:8px;max-width:100%}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:9px;border-bottom:1px solid #d4d8da;text-align:left;vertical-align:top}summary{cursor:pointer;font-weight:600}li{margin:10px 0}a{color:#185679}.note{padding:16px;background:#e9eef1}</style><main><header><p class="meta">17/10/2026 · Review văn bản · Sáu tập đã tạo media</p><h1>Nguồn đã kỹ hơn câu chuyện</h1><p>Giữ định vị sáu kênh. Chỉnh cách thực thi: đoạn phải tạo thay đổi, giới hạn nguồn nói đúng chỗ, số liệu có việc để làm, và kết một lần.</p><p class="note">Đọc toàn bộ lời hiện hành; cả sáu master khớp beats sau chuẩn hóa khoảng trắng. Điểm là đánh giá biên tập của một agent, không phải analytics hay review nghe/nhìn. Không tự sửa narration, media hoặc DNA sống.</p><p><a href="REPORT.md">Báo cáo đầy đủ, nguồn và giới hạn</a> · <a href="DNA_PROPOSED.md">Đề xuất thay DNA cụ thể</a> · <a href="assessment.json">Dữ liệu phiên bản và điểm</a></p><label for="channel">Xem kênh: </label><select id="channel"><option value="all">Cả sáu kênh</option>OPTIONS</select></header>CARDS<footer><p>Cà Mau: review ghi đã bỏ số tốc độ nhưng text vẫn có; topic root và recorded topic khác chuỗi nên context từ chối. Sáu caption QA còn needs_review theo hồ sơ. Báo cáo đầy đủ phân biệt các lỗi này với nhận xét kịch bản.</p></footer></main><script>document.getElementById('channel').addEventListener('change',e=>document.querySelectorAll('article').forEach(x=>x.hidden=e.target.value!=='all'&&x.dataset.id!==e.target.value));</script></html>'''
    (OUT / "review.html").write_text(page.replace("OPTIONS", options).replace("CARDS", "".join(cards)), encoding="utf-8")


if __name__ == "__main__":
    main()
