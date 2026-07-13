# Kế hoạch triển khai webapp ôn thi trắc nghiệm — Cơ sở lập trình

## Mục tiêu

Xây dựng webapp ôn thi cho môn **Cơ sở lập trình**, tạo đề 40 câu theo blueprint cố định:

| Nhóm độ khó | Số câu/đề | Tỷ lệ |
| --- | ---: | ---: |
| Dễ | 12 | 30% |
| Vừa + Khó | 16 | 40% |
| Rất khó | 12 | 30% |

Mặc định, 16 câu ở nhóm giữa được chia thành 8 câu Vừa và 8 câu Khó. Chỉ được bù giữa hai mức này khi dữ liệu sau lọc không đủ; lần bù phải được ghi lại trong đề để kiểm tra.

## Kết quả kiểm kê database (13/07/2026)

### Nguồn và liên kết dữ liệu

| Nguồn | Lượt câu | Đã liên kết canonical | Ghi chú |
| --- | ---: | ---: | --- |
| `200_cau_hoi_CSLT.xlsx` | 200 | 200 | Đủ 4 phương án, đáp án và giải thích |
| `đề 1.pdf` | 241 | 0 | Đã tách câu; chưa tách phương án |
| `đề 2.pdf` | 50 | 0 | Đã tách câu; chưa tách phương án |
| `Câu hỏi ôn tập-e.pdf` | 225 | 0 | OCR; còn cần duyệt trích xuất |
| **Tổng** | **716** | **200** | **516 câu cần chuẩn hóa thành canonical** |

- 716 câu có nội dung câu hỏi khác nhau khi so khớp chính xác trên văn bản đã chuẩn hóa. So khớp gần (near-duplicate) chưa thực hiện.
- Chưa có câu nào `approved`; 200 canonical hiện đều `drafted`. Vì vậy pool được phép phát hành hiện là **0 câu**.
- 665/716 câu có trạng thái đáp án `extracted` hoặc `solved`; 51 câu còn `needs_review`.
- 491/716 câu có trạng thái trích xuất `extracted`; toàn bộ 225 câu từ PDF OCR còn `needs_review`.
- Chỉ 200/716 câu có đúng 4 phương án lựa chọn có thể dùng ngay. 516 câu PDF hiện lưu danh sách phương án rỗng; cần tách lại A–D và duyệt đối chiếu bản gốc.

### Phân bố độ khó hiện tại

| Độ khó | Số câu thô đã gắn tag |
| --- | ---: |
| Dễ | 151 |
| Vừa | 236 |
| Khó | 201 |
| Rất khó | 128 |
| **Tổng** | **716** |

Các tag từ PDF đang là `rule_based`, chưa thay thế cho đánh giá chuyên môn. Tag từ Excel được giữ theo nguồn. Cần duyệt lại các tag trước khi dùng làm đề chính thức.

## Số lượng đề đề xuất

### Đề chuẩn không lặp câu

Sau khi mọi câu được chuẩn hóa, xác minh và `approved`, ngân hàng hiện tại đủ để phát hành **10 đề chuẩn 40 câu không lặp câu giữa các đề**:

- 10 × 12 câu Dễ = 120 câu (còn 31 câu Dễ).
- 10 × 16 câu Vừa + Khó = 160 câu (còn 277 câu nhóm giữa).
- 10 × 12 câu Rất khó = 120 câu (còn 8 câu Rất khó).

Nhóm **Rất khó (128 câu)** là nút thắt: `floor(128 / 12) = 10`. Không nên hứa hơn 10 đề chuẩn không lặp câu trước khi bổ sung tối thiểu 4 câu Rất khó đã duyệt cho đề thứ 11, hoặc thay đổi blueprint.

### Chế độ random

Ngoài 10 đề chuẩn có mã đề cố định, webapp có thể tạo nhiều phiên random từ cùng ngân hàng. Câu có thể lặp giữa các lần làm khác nhau, nhưng không được lặp trong một đề. Cần hiển thị mã đề, seed và snapshot ID để tái lập chính xác phiên làm bài khi cần phúc khảo.

## Quy tắc dữ liệu trước khi phát hành

Một câu chỉ được vào pool thi khi đồng thời có:

1. Nội dung câu hỏi và đúng 4 lựa chọn A–D không rỗng.
2. Một đáp án A–D đã xác minh; nếu có xung đột giữa nguồn và lời giải thì chuyển `needs_review`.
3. Lời giải ngắn, có thể hiểu độc lập; với C/C++ phải ghi rõ giả định compiler/chuẩn/ngữ cảnh khi cần.
4. Một chủ đề và một độ khó đã được duyệt thủ công.
5. Liên kết `canonical_question` và ít nhất một nguồn gốc (tài liệu, trang, số thứ tự).
6. `solution_status = approved`; câu OCR cần duyệt hình gốc trước khi đạt trạng thái này.

## Kiến trúc đề xuất

```text
Tài liệu nguồn -> import/OCR -> source_questions (provenance)
                              -> canonical_questions (đã duyệt)
                              -> API tạo đề/chấm điểm
                              -> webapp học viên + trang quản trị
```

- Duy trì SQLite là nguồn sự thật; giữ `source_questions` để truy vết, chỉ `canonical_questions` đã duyệt được phát hành.
- Bổ sung các bảng `exam_blueprints`, `exam_instances`, `exam_instance_questions`, `attempts`, `attempt_answers` và `review_queue`.
- Stack MVP nhẹ: **FastAPI + Jinja templates + TypeScript ES modules + Tailwind CSS biên dịch tĩnh**. Không dùng React, chart library, UI runtime hay ảnh trang trí; các control chỉ dùng HTML native và SVG icon nhất quán.
- API phía máy chủ tạo đề và chấm điểm. Không đưa đáp án/lời giải vào payload trước khi nộp bài; frontend tĩnh chứa sẵn đáp án không phù hợp cho chế độ thi.
- Giao diện gồm hai vai trò: học viên (làm đề, xem kết quả/lịch sử) và quản trị (duyệt dữ liệu, xem hàng đợi lỗi, tạo/publish đề).

## Blueprint nội dung và trải nghiệm

- Áp dụng tỷ lệ 12 Dễ / 8 Vừa / 8 Khó / 12 Rất khó; xác thực trước khi tạo đề.
- Sau khi chủ đề PDF được chuẩn hóa, mỗi đề phải phủ tối thiểu 5 chủ đề và không quá 35% câu từ một chủ đề, trừ khi quản trị chọn chế độ ôn theo chủ đề.
- Luôn lấy mẫu không hoàn lại theo `canonical_question.id`; lưu snapshot câu hỏi và thứ tự hiển thị vào `exam_instance`.
- Cho phép trộn thứ tự câu và phương án nhưng không thay đổi nghĩa của câu (đặc biệt với “tất cả đáp án trên”).
- Màn hình làm bài: đồng hồ tùy chọn, bảng điều hướng 40 câu, đánh dấu câu cần xem lại, tự lưu đáp án, nộp bài có xác nhận.
- Màn hình kết quả: điểm, tỷ lệ theo độ khó/chủ đề, đáp án đúng, lời giải và danh sách cần ôn lại. Không công bố lời giải trước khi nộp.

## Thiết kế UI — laptop-first, nhẹ và mượt

Thiết kế chi tiết nằm tại `tasks/ui-design.md`. Quyết định cốt lõi:

- Chỉ tối ưu cho viewport laptop từ **1024px**; ưu tiên 1280–1440px. Ở 1024–1199px, thanh điều hướng câu thu gọn thành panel mở bằng nút; không triển khai trải nghiệm mobile-first trong MVP.
- Giao diện “quiet academic”: nền slate rất nhạt, chữ slate đậm, xanh dương làm màu hành động duy nhất; không gradient, không minh họa, không card/shadow dày, không emoji làm icon.
- Dùng system font để không phát sinh tải font/CLS; font mono hệ thống chỉ cho code C/C++ và timer. Dùng SVG icon cùng một bộ khi thật sự cần.
- Mỗi lần mở đề tải một payload chứa đủ 40 câu **không có đáp án/lời giải**, sau đó đổi câu tại client không gọi mạng. Chọn đáp án phản hồi ngay; autosave nền được debounce 400ms và có trạng thái “Đã lưu/Đang lưu/Lưu lỗi”.
- Chỉ dùng chuyển màu/opacity 120–160ms; tôn trọng `prefers-reduced-motion`. Không có animation trang, biểu đồ hoặc hiệu ứng không phục vụ thao tác.
- Mọi thao tác làm bài có thể dùng bàn phím: `1–4` chọn đáp án, mũi tên trái/phải chuyển câu, `R` đánh dấu xem lại (không kích hoạt khi đang focus vào input). Có focus ring, skip link, thứ tự Tab hợp lý và không dùng màu làm tín hiệu duy nhất.

### Ngân sách hiệu năng UI

| Hạng mục | Mục tiêu MVP |
| --- | --- |
| JavaScript tải ban đầu | ≤ 80 KB gzip, không tính runtime trình duyệt |
| CSS đã build | ≤ 25 KB gzip |
| Payload một đề 40 câu | ≤ 150 KB nén, không có đáp án/lời giải |
| Phản hồi chọn đáp án/chuyển câu | cập nhật UI trong <100 ms, không chờ API |
| Tự lưu | debounce 400 ms, retry có kiểm soát khi lỗi mạng |
| Hiệu ứng UI | chỉ `opacity`/`transform`, 120–160 ms hoặc tắt khi reduced motion |

## Lộ trình theo lát dọc

### Giai đoạn 1 — Hoàn thiện ngân hàng phát hành

1. Chuẩn hóa 516 câu PDF: tách A–D, khôi phục trang/số câu, tạo canonical và hàng đợi OCR.
2. Đối chiếu 51 đáp án còn `needs_review`; phát hiện xung đột đáp án/lời giải.
3. Gắn chủ đề đầy đủ, kiểm duyệt độ khó và phát hiện trùng gần.
4. Chỉ chuyển `approved` khi đạt đủ 6 điều kiện phát hành; xuất báo cáo coverage theo chủ đề/độ khó.

### Checkpoint dữ liệu

- Có ít nhất 120 Dễ, 80 Vừa, 80 Khó và 120 Rất khó đã `approved`, mỗi câu có 4 phương án.
- Có thể tạo 10 đề không lặp câu và mọi đề đều đúng blueprint 12/8/8/12.
- Báo cáo riêng các câu OCR, đáp án mâu thuẫn và câu phụ thuộc compiler/undefined behavior.

### Giai đoạn 2 — Đề và API

5. Thêm schema đề/phiên làm bài cùng migration có thể chạy lặp lại.
6. Xây bộ tạo đề có seed, kiểm tra tỷ lệ/chủ đề/không lặp và thông báo thiếu pool rõ ràng.
7. Cài API tạo đề, lưu đáp án, nộp bài và trả kết quả sau nộp.

### Checkpoint luồng lõi

- Test tạo 100 đề random: mỗi đề 40 câu, 12/8/8/12, không trùng ID nội bộ.
- Cùng seed và snapshot luôn tái tạo cùng đề.
- Không có API trước nộp trả đáp án hoặc lời giải.

### Giai đoạn 3 — Webapp và quản trị

8. Xây app shell laptop-first và luồng làm bài: chọn đề, tải trước 40 câu, tự lưu, bàn phím và nộp bài.
9. Xây trang kết quả và màn quản trị tối giản: review queue, audit, tạo/publish 10 đề chuẩn.
10. Kiểm thử end-to-end, ngân sách hiệu năng/accessibility, sao lưu SQLite và hướng dẫn vận hành.

## Rủi ro và cách xử lý

| Rủi ro | Tác động | Cách xử lý |
| --- | --- | --- |
| 516 câu PDF chưa có phương án A–D | Không thể phát hành đề đúng nghĩa trắc nghiệm | Ưu tiên parser/duyệt phương án trước UI |
| 225 câu OCR chưa duyệt | Sai câu, mất ký tự code hoặc đáp án | Đối chiếu ảnh gốc; chỉ approved sau duyệt |
| Tag độ khó tự động sai | Phân bố đề thiếu công bằng | Duyệt chuyên môn, lưu lý do/nguồn tag |
| Code C/C++ phụ thuộc môi trường | Chấm sai hoặc lời giải gây tranh cãi | Nêu giả định; gắn cờ/loại câu UB khỏi đề chuẩn |
| Thiếu dependency `pypdf` ở môi trường hiện tại | Bộ test import PDF không chạy đầy đủ | Khai báo dependency tái lập được và chạy test trong môi trường sạch |
| UI nặng hoặc render giật khi làm bài | Mất tập trung, dễ chọn nhầm đáp án | Không dùng UI runtime; preload 40 câu; đo bundle và giữ thay đổi UI cục bộ |

## Câu hỏi cần chốt trước khi code webapp

1. Webapp chỉ dùng nội bộ một lớp hay cần tài khoản cho nhiều học viên/lớp?
2. Có yêu cầu giới hạn thời gian, chống gian lận hoặc xuất PDF đề đáp án không?
3. Ai là người duyệt độ khó/chủ đề cho các câu PDF trước khi publish?
