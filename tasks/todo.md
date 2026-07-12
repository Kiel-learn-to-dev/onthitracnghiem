# Danh sách công việc: Ngân hàng ôn tập Cơ sở lập trình

## Giai đoạn 1 — Thiết lập dữ liệu

## Task 1: Tạo cấu trúc dự án và schema SQLite

**Acceptance criteria:**
- [ ] Có schema cho nguồn, câu nguồn, câu chuẩn và lịch sử cập nhật.
- [ ] Ràng buộc mức độ và trạng thái không cho phép giá trị ngoài quy ước.
- [ ] Database tạo lại được từ một lệnh duy nhất.

**Verification:** kiểm tra schema và chèn thử một bản ghi hợp lệ/không hợp lệ.

**Dependencies:** None

## Task 2: Nhập và kiểm tra file Excel

**Acceptance criteria:**
- [ ] Nhập đủ 200 câu, 4 đáp án, đáp án đúng và giải thích.
- [ ] Giữ đúng tiếng Việt, code block và chủ đề nguồn.

**Verification:** đối chiếu số dòng và 10 câu ngẫu nhiên với workbook.

**Dependencies:** Task 1

## Task 3: Trích xuất ba PDF và OCR PDF ảnh

**Acceptance criteria:**
- [ ] Có 225, 241 và 50 lượt câu tương ứng với ba PDF.
- [ ] Mỗi câu có định danh trang/thứ tự và cờ độ tin cậy trích xuất.
- [ ] Tất cả trang OCR có độ tin cậy thấp được đưa vào danh sách kiểm tra trực quan.

**Verification:** đối chiếu tổng 516 lượt PDF và xem lại mẫu đầu/cuối của mỗi tài liệu.

**Dependencies:** Task 1

## Checkpoint: Nguồn dữ liệu

- [ ] Database chứa đúng 716 lượt câu nguồn.
- [ ] Không có bản ghi thiếu câu hỏi hoặc thiếu tập phương án mà không được gắn cờ.

## Giai đoạn 2 — Chuẩn hóa và giải chi tiết

## Task 4: Chuẩn hóa, gộp câu trùng và gắn chủ đề

**Acceptance criteria:**
- [ ] Không mất câu nguồn; mọi bản ghi có liên kết câu chuẩn.
- [ ] Các câu trùng exact được gộp lời giải nhưng vẫn giữ nguồn.
- [ ] Câu nghi ngờ trùng được ghi cờ để quyết định thủ công.

**Verification:** báo cáo số nguồn, số câu chuẩn, số exact duplicate và số cần rà soát.

**Dependencies:** Task 2, Task 3

## Task 5: Giải và lưu theo lô có checkpoint

**Acceptance criteria:**
- [ ] Mỗi câu hoàn thành được lưu ngay kèm đáp án, lời giải, tag độ khó và trạng thái.
- [ ] Câu về code có ghi rõ giả định runtime/compiler khi cần.
- [ ] Lô kế tiếp chỉ bắt đầu sau khi kiểm tra dữ liệu lô trước.

**Verification:** sau từng lô, truy vấn số `approved`, kiểm tra mẫu lời giải và chạy kiểm tra trùng/thiếu.

**Dependencies:** Task 4

## Task 6: Rà soát độc lập đáp án và phân bố độ khó

**Acceptance criteria:**
- [ ] 100% câu chuẩn được kiểm tra đáp án/lời giải.
- [ ] Mỗi câu có đúng một tag Dễ, Vừa, Khó hoặc Rất khó.
- [ ] Mỗi nhóm có đủ câu để tạo đề 12/16/12.

**Verification:** báo cáo phân bố và test tạo 100 đề không lặp câu nội bộ.

**Dependencies:** Task 5

## Checkpoint: Ngân hàng đã duyệt

- [ ] Không còn câu `pending`, `drafted` hoặc `reviewed` trong tập xuất bản.
- [ ] Không có lời giải trống, đáp án ngoài A-D hoặc độ khó không hợp lệ.

## Giai đoạn 3 — PDF và web

## Task 7: Tạo PDF ôn tập từ database

**Acceptance criteria:**
- [ ] PDF có câu hỏi, đáp án và lời giải theo chủ đề/độ khó.
- [ ] Mã C/C++ và tiếng Việt hiển thị rõ, không bị cắt trang.

**Verification:** render, xem trang đầu/cuối và các trang chứa code dài.

**Dependencies:** Task 6

## Task 8: Xuất JSON cho app và kiểm tra hợp đồng dữ liệu

**Acceptance criteria:**
- [ ] JSON chỉ chứa câu `approved` và không lộ đáp án trước khi người học nộp bài.
- [ ] Dữ liệu có đủ chủ đề, mức độ, phương án, đáp án và lời giải sau khi chấm.

**Verification:** JSON schema validation và kiểm tra số lượng khớp database.

**Dependencies:** Task 6

## Task 9: Xây dựng HTML app luyện trắc nghiệm

**Acceptance criteria:**
- [ ] Tạo đúng 40 câu theo tỷ lệ 12 Dễ / 16 Vừa+Khó / 12 Rất khó.
- [ ] Có chọn đáp án, điều hướng, tiến độ, nộp bài, điểm và lời giải.
- [ ] Không có câu chuẩn lặp trong cùng đề; thông báo rõ nếu dữ liệu chưa đủ.

**Verification:** unit test bộ chọn đề và kiểm tra luồng làm đề trong trình duyệt.

**Dependencies:** Task 8

## Task 10: Kiểm tra và bàn giao

**Acceptance criteria:**
- [ ] Kiểm tra import, database, generator đề, PDF và app đều đạt.
- [ ] Có hướng dẫn ngắn để cập nhật dữ liệu, sinh lại PDF/JSON và mở app.

**Verification:** chạy toàn bộ test, mở app từ đầu tới cuối và đối chiếu PDF với database.

**Dependencies:** Task 7, Task 9
