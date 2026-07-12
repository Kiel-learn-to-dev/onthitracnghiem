# Kế hoạch triển khai: Ngân hàng ôn tập Cơ sở lập trình

## Mục tiêu

Xây dựng một nguồn dữ liệu chuẩn duy nhất để lưu, giải chi tiết và phân loại toàn bộ 716 lượt câu hỏi hiện có. Từ nguồn này sẽ sinh ra (1) PDF ôn tập có lời giải và (2) HTML app chạy cục bộ để tạo đề 40 câu, làm bài, chấm điểm và xem lời giải.

## Phạm vi dữ liệu ban đầu

| Nguồn | Lượt câu hỏi | Cách đọc |
| --- | ---: | --- |
| `200_cau_hoi_CSLT.xlsx` | 200 | Bảng câu hỏi, đáp án và giải thích sẵn có |
| `Câu hỏi ôn tập-e.pdf` | 225 | PDF ảnh, cần OCR và kiểm tra thủ công |
| `đề 1.pdf` | 241 | PDF có lớp văn bản; vẫn có câu nhãn trùng cần chuẩn hóa |
| `đề 2.pdf` | 50 | Đề thi 50 câu |
| **Tổng** | **716** | Chưa loại trùng giữa các nguồn |

## Quyết định kiến trúc

- **SQLite (`data/review.db`)** là nguồn dữ liệu gốc: không cần máy chủ, có giao dịch an toàn và phù hợp với việc cập nhật từng câu.
- Bảng `source_questions` bảo toàn từng lượt câu theo tài liệu gốc. Bảng `canonical_questions` chứa nội dung chuẩn hóa và lời giải dùng chung cho các câu trùng; `source_questions.canonical_id` liên kết tới nó.
- Mọi lần giải được ghi ngay trong một giao dịch SQLite: nội dung câu, đáp án, lời giải, mức độ, giả định môi trường chạy code, trạng thái kiểm duyệt và thời điểm cập nhật.
- HTML là static app, nạp `web/data/questions.json` được sinh từ các câu có trạng thái `approved`; không truy cập SQLite trực tiếp từ trình duyệt.
- PDF được sinh từ truy vấn SQLite đã duyệt, có mục lục/chủ đề, đáp án và lời giải chi tiết.

## Mô hình dữ liệu tối thiểu

```text
sources(id, filename, kind, imported_at, checksum)
source_questions(id, source_id, source_label, page, ordinal, raw_question,
                 raw_choices_json, canonical_id, extraction_status)
canonical_questions(id, content_hash, question, choices_json, answer,
                    explanation, topic, difficulty, assumptions,
                    solution_status, reviewed_at, updated_at)
solution_audit(id, canonical_id, action, before_json, after_json, created_at)
```

`difficulty` chỉ nhận `Dễ | Vừa | Khó | Rất khó`; `solution_status` chỉ nhận `pending | drafted | reviewed | approved`.

## Luồng xử lý và kiểm soát chất lượng

1. Nhập dữ liệu từng nguồn, lưu nguyên văn và tọa độ nguồn (trang/thứ tự) trước khi chuẩn hóa.
2. OCR 225 câu trong PDF ảnh; đối chiếu ảnh gốc ở các trang có độ tin cậy thấp.
3. Chuẩn hóa câu hỏi, phương án, mã nguồn C/C++ và ký hiệu; phát hiện trùng exact/near-duplicate nhưng không xóa bản ghi nguồn.
4. Giải theo từng câu chuẩn. Ngay sau khi hoàn tất một câu, lưu transaction vào SQLite; không chờ cả lô.
5. Với câu tracing C/C++, ghi rõ tiêu chuẩn và môi trường cần thiết (C/C++, kích thước kiểu dữ liệu, compiler), đồng thời đánh dấu câu có undefined/implementation-defined behavior để lời giải không khẳng định sai.
6. Gắn tag chủ đề và một mức độ. Có kiểm tra phân bố để bảo đảm đủ câu cho đề 40 câu.
7. Rà soát độc lập đáp án, phương án nhiễu và lời giải; chỉ câu `approved` mới được xuất PDF/JSON.

## Quy tắc tạo đề 40 câu

- 12 câu Dễ (30%).
- 16 câu thuộc nhóm Vừa + Khó (40%); mặc định 8 Vừa và 8 Khó, nhưng có thể phân phối lại trong cùng nhóm nếu một mức không đủ câu.
- 12 câu Rất khó (30%).
- Không lặp `canonical_id` trong một đề; có thể lọc theo chủ đề.
- Nếu một nhóm chưa có đủ câu `approved`, app báo rõ số câu còn thiếu thay vì tạo đề sai tỷ lệ.

## Lộ trình triển khai

### Giai đoạn 1 — Dữ liệu và OCR

Tạo schema, nhập 716 lượt câu, OCR PDF ảnh, giữ liên kết về nguồn và tạo báo cáo thiếu/trùng.

### Giai đoạn 2 — Lời giải và phân loại

Giải theo lô nhỏ có checkpoint; mỗi câu lưu ngay vào DB với mức độ, chủ đề, đáp án và lời giải. Hoàn tất bằng rà soát các câu phụ thuộc compiler/undefined behavior.

### Phạm vi dừng theo yêu cầu hiện tại

Sau khi database đủ 716 lượt câu và mọi lượt có tag độ khó, dừng công việc. Việc sinh PDF, JSON và HTML app được để lại cho kế hoạch riêng sau này.

## Rủi ro và phương án xử lý

| Rủi ro | Tác động | Cách xử lý |
| --- | --- | --- |
| OCR sai PDF ảnh | Sai câu/đáp án | Lưu ảnh-trang tham chiếu, đánh dấu độ tin cậy, kiểm tra trực quan trước khi duyệt |
| Câu trùng hoặc đánh số trùng | Lời giải bị lặp/sai nguồn | Bảo toàn bản ghi nguồn, dùng canonical question và content hash |
| Code phụ thuộc Dev-C++/32-bit/UB | Đáp án không phổ quát | Ghi rõ giả định và kiểm chứng bằng compiler phù hợp; gắn cờ hành vi không xác định |
| Thiếu câu Dễ/Vừa cho tỷ lệ đề | Không thể random đúng | Hoàn tất tagging toàn bộ trước khi mở app; app từ chối tạo đề sai tỷ lệ |

## Tiêu chí hoàn thành

- 716 lượt câu có mặt trong database và truy vết được về tài liệu/trang gốc.
- Mọi câu chuẩn có đáp án, lời giải, chủ đề, đúng một tag độ khó và trạng thái `approved`.
- PDF xuất được từ database, hiển thị đúng tiếng Việt/mã nguồn và có lời giải đầy đủ.
- HTML app tạo đúng 40 câu với tỷ lệ 12/16/12, chấm điểm chính xác, hiện lời giải và không lặp câu trong đề.
- Có kiểm tra tự động cho schema, import, phân bố đề, export JSON và thao tác app chính.

## Điểm cần duyệt trước khi triển khai

Kế hoạch coi 716 là các lượt câu theo nguồn; các câu giống nhau sẽ cùng dùng một lời giải chuẩn nhưng vẫn được giữ trong các tài liệu xuất bản phù hợp.
