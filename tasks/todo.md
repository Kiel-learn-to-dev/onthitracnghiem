# Danh sách công việc — webapp ôn thi Cơ sở lập trình

## Task 1: Bổ sung dependency và kiểm tra pipeline nhập liệu

**Description:** Đóng gói môi trường Python tái lập được, gồm `pypdf`, và xác nhận các importer chạy được từ đầu đến cuối.

**Acceptance criteria:**
- [ ] Có file dependency/lock phù hợp cho các script nhập liệu và test.
- [ ] `python -m unittest discover -s tests -v` chạy không lỗi import.
- [ ] Không thay đổi dữ liệu nguồn trong quá trình test.

**Verification:** chạy toàn bộ test và rebuild database vào đường dẫn tạm.

**Dependencies:** None

**Estimated scope:** Small

## Task 2: Tách và lưu phương án A–D cho 516 câu PDF

**Description:** Mở rộng parser PDF/OCR để lưu bốn phương án có thứ tự, vị trí nguồn và độ tin cậy thay vì danh sách lựa chọn rỗng.

**Acceptance criteria:**
- [ ] Mỗi câu PDF có đúng 4 lựa chọn A–D hoặc được đưa vào `review_queue` kèm lý do.
- [ ] Không ghi đè câu Excel đã có phương án chuẩn.
- [ ] Lưu được trang/số câu để đối chiếu tài liệu gốc.

**Verification:** báo cáo số câu có 4 lựa chọn theo từng nguồn; kiểm tra trực quan mẫu đầu/cuối và các câu có code.

**Dependencies:** Task 1

**Estimated scope:** Medium

## Task 3: Chuẩn hóa canonical, phát hiện trùng gần và bảo toàn provenance

**Description:** Tạo canonical cho 516 câu còn thiếu, liên kết tất cả source record và xếp các cặp nghi trùng vào hàng đợi duyệt.

**Acceptance criteria:**
- [ ] 716/716 source record có `canonical_id`.
- [ ] Câu trùng không làm mất nguồn/trang/số thứ tự.
- [ ] Có báo cáo exact/near duplicate để quản trị quyết định gộp.

**Verification:** truy vấn linkage bằng 0 câu chưa liên kết; kiểm tra 10 cặp nghi trùng.

**Dependencies:** Task 2

**Estimated scope:** Medium

## Checkpoint: Cấu trúc ngân hàng

- [ ] Mọi candidate có nội dung, 4 lựa chọn và provenance.
- [ ] Không có importer/test nào phụ thuộc môi trường cục bộ chưa khai báo.

## Task 4: Duyệt đáp án, lời giải và các câu OCR

**Description:** Xử lý 51 câu có đáp án `needs_review`, xác minh 225 câu OCR bằng ảnh gốc và gắn cờ câu phụ thuộc compiler/undefined behavior.

**Acceptance criteria:**
- [ ] Không còn candidate phát hành có `answer_status = needs_review` hoặc `extraction_status = needs_review`.
- [ ] Mọi đáp án là A–D và có lời giải không rỗng.
- [ ] Câu cần giả định môi trường có ghi chú hoặc bị loại khỏi đề chuẩn.

**Verification:** báo cáo trạng thái đáp án/trích xuất; review ngẫu nhiên tối thiểu 10% mỗi nguồn.

**Dependencies:** Task 2, Task 3

**Estimated scope:** Medium

## Task 5: Kiểm duyệt chủ đề, độ khó và mở pool phát hành

**Description:** Hoàn thiện taxonomy, duyệt tag độ khó và chuyển các câu đủ điều kiện sang `approved`.

**Acceptance criteria:**
- [ ] Mỗi câu approved có một chủ đề và một độ khó đã duyệt.
- [ ] Pool approved có tối thiểu 120 Dễ, 80 Vừa, 80 Khó, 120 Rất khó.
- [ ] Có báo cáo coverage theo chủ đề/độ khó và hàng đợi thiếu dữ liệu.

**Verification:** truy vấn distribution; review độc lập một mẫu mỗi chủ đề/độ khó.

**Dependencies:** Task 4

**Estimated scope:** Medium

## Checkpoint: 10 đề chuẩn khả thi

- [ ] Bộ chọn tạo được 10 tập không giao nhau, mỗi tập 40 câu đúng 12/8/8/12.
- [ ] Không câu nào chưa approved xuất hiện trong tập thử.

## Task 6: Thiết kế migration và bộ tạo đề có thể tái lập

**Description:** Thêm schema đề/phiên làm bài và service chọn câu theo seed, blueprint, chủ đề, trạng thái phát hành.

**Acceptance criteria:**
- [ ] Lưu snapshot ID câu hỏi, thứ tự và seed cho từng đề.
- [ ] Không lặp canonical ID trong một đề.
- [ ] Thiếu pool trả lỗi có số câu thiếu theo từng bucket, không tự phá tỷ lệ.

**Verification:** unit test tạo 100 đề; test thiếu dữ liệu cho từng bucket.

**Dependencies:** Task 5

**Estimated scope:** Medium

## Task 7: Xây API tạo đề, lưu bài làm và chấm điểm

**Description:** Cài API server-side cho lifecycle tạo đề → trả câu hỏi → lưu đáp án → nộp → xem kết quả.

**Acceptance criteria:**
- [ ] Payload trước nộp không chứa đáp án/lời giải.
- [ ] Nộp bài chấm chính xác và idempotent.
- [ ] Attempt lưu được điểm, thời gian và đáp án đã chọn.

**Verification:** integration test cho toàn bộ lifecycle và kiểm tra payload trước/sau nộp.

**Dependencies:** Task 6

**Estimated scope:** Medium

## Task 8: Xây app shell laptop-first và màn làm bài

**Description:** Tạo giao diện FastAPI template + TypeScript ES modules theo `tasks/ui-design.md`; không dùng React/UI runtime. Tối ưu laptop 1024px+, tải trước 40 câu và điều hướng cục bộ.

**Acceptance criteria:**
- [ ] Layout hai cột hoạt động tại 1280–1440px; panel điều hướng thu gọn đúng tại 1024–1199px.
- [ ] Chọn đáp án/câu chuyển trong <100ms không cần gọi mạng; autosave debounce 400ms có trạng thái thành công/lỗi/retry.
- [ ] Có keyboard navigation, focus management, skip link, modal nộp bài và trạng thái tải/lỗi/trống rõ ràng.
- [ ] Màn hình hẹp hơn 1024px báo yêu cầu dùng laptop, không cố tạo mobile layout.

**Verification:** browser end-to-end test cho một attempt 40 câu tại 1024px, 1280px, 1440px; Tab/keyboard walkthrough và axe-core.

**Dependencies:** Task 7

**Estimated scope:** Medium

## Task 9: Xây kết quả, quản trị tối giản và phát hành 10 đề chuẩn

**Description:** Tạo màn duyệt dữ liệu có audit, hàng đợi review và thao tác tạo/publish đề cố định.

**Acceptance criteria:**
- [ ] Mọi thay đổi câu/đáp án/độ khó có audit trail.
- [ ] Quản trị publish được 10 đề không lặp nhau.
- [ ] Học viên không thể truy cập thao tác quản trị.
- [ ] Kết quả dùng HTML/CSS progress bars, không thêm chart library; review câu dùng deep link theo số câu.
- [ ] Table quản trị phân trang server-side 25–50 hàng, không tải toàn bộ ngân hàng vào DOM.

**Verification:** role-based integration test; kiểm tra 10 đề đã publish với blueprint; performance test danh sách quản trị và review kết quả.

**Dependencies:** Task 5, Task 7

**Estimated scope:** Medium

## Task 10: Kiểm thử, sao lưu và bàn giao

**Description:** Hoàn tất quality gate, hướng dẫn vận hành và cơ chế backup/restore database.

**Acceptance criteria:**
- [ ] Unit, integration và end-to-end tests đều chạy trong môi trường sạch.
- [ ] Có hướng dẫn import, duyệt, tạo đề, backup và restore.
- [ ] Có smoke test sau deploy và quy trình rollback.
- [ ] JavaScript/CSS/payload đề đạt ngân sách hiệu năng trong `tasks/plan.md`.
- [ ] Axe không còn lỗi critical/serious; kiểm tra keyboard tại 1024px, 1280px và 1440px.

**Verification:** chạy full test/build, restore database bản sao và thực hiện một attempt hoàn chỉnh.

**Dependencies:** Task 8, Task 9

**Estimated scope:** Medium
