# Thiết kế giao diện MVP — CSLT Ôn thi

## Mục tiêu trải nghiệm

Người học mở đề, trả lời 40 câu bằng chuột hoặc bàn phím, luôn biết mình đang ở câu nào và dữ liệu đã được lưu chưa. Giao diện phải yên tĩnh, rõ ràng, không tạo gánh nặng thị giác khi đọc code C/C++.

Phạm vi là **laptop web**: hỗ trợ tốt từ 1024px, tối ưu tại 1280–1440px. Không xây bố cục mobile-first; màn hẹp hơn 1024px hiển thị thông báo dùng màn hình lớn hơn thay vì cố nén trải nghiệm thi.

## Nguyên tắc thiết kế

- Một màn hình, một hành động chính: bắt đầu đề, chọn đáp án hoặc nộp bài.
- Nội dung câu hỏi là trung tâm; navigation và số liệu chỉ hỗ trợ định hướng.
- Trạng thái có văn bản + hình dạng, không chỉ màu: `Đã trả lời`, `Chưa trả lời`, `Đánh dấu`.
- Không dùng gradient, glassmorphism, ảnh stock, biểu đồ nặng, hình minh họa hoặc icon emoji.
- Không dùng modal để điều hướng; modal chỉ dùng cho thao tác không thể đảo ngược như nộp bài.
- Không có dark mode trong MVP để giảm diện kiểm thử. Light theme đạt WCAG AA; dark mode là hạng mục sau khi luồng học viên ổn định.

## Design tokens

| Token | Giá trị | Dùng cho |
| --- | --- | --- |
| `--bg` | `#F8FAFC` | nền trang |
| `--surface` | `#FFFFFF` | vùng đọc câu hỏi, panel |
| `--text` | `#0F172A` | chữ chính |
| `--muted` | `#475569` | chữ phụ |
| `--border` | `#CBD5E1` | đường chia, control mặc định |
| `--primary` | `#2563EB` | CTA, lựa chọn đang chọn, focus |
| `--primary-weak` | `#DBEAFE` | nền trạng thái đang chọn |
| `--success` | `#15803D` | lưu thành công, đáp án đúng |
| `--danger` | `#B91C1C` | lỗi, đáp án sai, hành động nguy hiểm |
| `--warning` | `#A16207` | câu đánh dấu xem lại |
| `--radius` | `6px` | button, input, panel |
| spacing | `4, 8, 12, 16, 24, 32px` | toàn bộ gap/padding |

- Font chính: `system-ui, "Segoe UI", Arial, sans-serif`.
- Code/timer: `ui-monospace, "Cascadia Code", Consolas, monospace`.
- Body 16px / 1.6; câu hỏi 18px / 1.6; code 14px / 1.55. Không dùng text dưới 13px.
- Khung nội dung tối đa 1440px; padding ngang 24px (1024px) và 32px (1280px+).

## Cấu trúc màn hình

### 1. Trang chủ / chọn đề

```text
+--------------------------------------------------------------------------------+
| CSLT Ôn thi                         Lịch sử làm bài                 [Hồ sơ]  |
+--------------------------------------------------------------------------------+
|                                                                                |
|  Ôn thi Cơ sở lập trình                                                        |
|  40 câu · 12 Dễ · 8 Vừa · 8 Khó · 12 Rất khó                                 |
|                                                                                |
|  [ Bắt đầu đề ngẫu nhiên ]         [ Xem 10 đề chuẩn ]                        |
|                                                                                |
|  Lần làm gần đây                   Tiến độ ôn tập                              |
|  Đề #03  29/40  72.5%              4 đề đã hoàn thành                         |
+--------------------------------------------------------------------------------+
```

- Không có hero lớn; CTA “Bắt đầu đề ngẫu nhiên” là primary duy nhất.
- Các số liệu là text/HTML đơn giản, không nạp thư viện chart.

### 2. Màn làm bài

```text
+--------------------------------------------------------------------------------+
| ← Thoát đề     Đề #03 · Câu 12/40     [Đã lưu]                    34:12       |
+----------------------------------------------+---------------------------------+
|                                              | Câu hỏi                         |
|  CHỦ ĐỀ: Con trỏ · KHÓ                       | [01] [02] [03] [04] [05]       |
|                                              | [06] [07] [08] [09] [10]       |
|  Nội dung câu hỏi / code block               | [11] [12] [13] [14] [15]       |
|                                              | ...                             |
|  ( ) A. Phương án A                           |                                 |
|  ( ) B. Phương án B                           | Trạng thái                      |
|  ( ) C. Phương án C                           | ■ Đã trả lời                    |
|  ( ) D. Phương án D                           | □ Chưa trả lời                  |
|                                              | ◇ Đánh dấu xem lại              |
|  [← Câu trước]  [Đánh dấu xem lại] [Câu sau →]|                                 |
+----------------------------------------------+---------------------------------+
|  12/40 đã trả lời                                      [ Nộp bài ]             |
+--------------------------------------------------------------------------------+
```

- Từ 1200px: vùng câu hỏi 1fr + sidebar 288px sticky. Từ 1024–1199px: sidebar thành panel mở/đóng từ header, không thay đổi vùng đọc câu.
- Câu hỏi và phương án nằm trong HTML semantic: `fieldset`, `legend`, radio native được style nhẹ. Có vùng code cuộn ngang độc lập, giữ dòng không wrap.
- Nút số câu là `button` 40px; trạng thái có viền, số và nhãn truy cập được, không chỉ đổi màu.
- Footer hành động sticky, chừa không gian cho nội dung; `Nộp bài` là CTA duy nhất. Modal xác nhận nêu số câu chưa trả lời và hai lựa chọn “Quay lại làm tiếp” / “Nộp bài”.

### 3. Kết quả

```text
+--------------------------------------------------------------------------------+
| Kết quả đề #03                                             [ Làm đề khác ]     |
+--------------------------------------------------------------------------------+
|  29/40 đúng      72.5%             Thời gian: 31:42                           |
|  Dễ  10/12       Vừa  6/8          Khó  5/8          Rất khó  8/12           |
|--------------------------------------------------------------------------------|
|  Câu 12 · Khó · Con trỏ                                                       |
|  Đáp án của bạn: B (Sai)       Đáp án đúng: C                                 |
|  Lời giải …                                                                  |
|  [ Câu trước ]                                                [ Câu sau ]      |
+--------------------------------------------------------------------------------+
```

- Tổng quan dùng 4 thanh progress CSS/HTML có số liệu kèm text, không dùng chart library.
- Review lần lượt từng câu để giữ DOM và sự tập trung nhẹ; URL có `?question=12` để back/forward được.

### 4. Quản trị dữ liệu

- Sidebar desktop cố định 232px; vùng chính là table/filter có pagination server-side.
- Màn danh sách không render toàn bộ 716 hàng: mỗi trang 25–50 hàng; lọc/truy vấn ở server, debounce 250ms.
- Form duyệt dùng split view: bản gốc/provenance bên trái, canonical + lựa chọn + tag bên phải; hành động `Approve`/`Needs review` luôn có lý do và audit.

## Tương tác và trạng thái

| Hành động | Phản hồi |
| --- | --- |
| Chọn A–D | cập nhật radio + nút số câu ngay, autosave sau 400ms |
| Autosave thành công | text “Đã lưu 10:24:08”, `aria-live="polite"`; không toast |
| Autosave lỗi | text “Chưa lưu — Thử lại”, nút retry; không xóa lựa chọn trên UI |
| Chuyển câu | thay nội dung tức thì từ payload đã tải; focus chuyển đến tiêu đề câu |
| Nộp bài | button disable trong lúc gửi; modal xác nhận nếu còn câu trống |
| Tải >300ms | skeleton vùng nội dung; không chặn header/navigation |

Phím tắt: `1–4` chọn phương án, `←/→` đổi câu, `R` bật/tắt đánh dấu. Hiển thị shortcut ở tooltip và trang trợ giúp; tất cả thao tác đều có button tương ứng.

## Accessibility và hiệu năng

- Mục tiêu WCAG 2.1 AA: tương phản text tối thiểu 4.5:1, focus ring 2px, Tab theo thứ tự đọc, skip link đến nội dung câu hỏi.
- Không trap focus trong sidebar/panel; modal nộp bài trap focus và `Esc` đóng modal.
- Payload đề tải một lần; không refetch khi chuyển câu. Cache route tĩnh, CSS/JS hash và nén Brotli/gzip.
- Không nạp Google Fonts, video, ảnh trang trí, analytics bên thứ ba hay icon package toàn cục. SVG icon inline chỉ cho hành động có ích.
- Tôn trọng `prefers-reduced-motion`; không animate layout, chỉ opacity/color 120–160ms.

## Tiêu chí nghiệm thu UI

- Tại 1024px, 1280px và 1440px không có cuộn ngang toàn trang; màn làm bài luôn giữ câu hỏi dễ đọc.
- Di chuyển 40 câu và chọn đáp án hoạt động offline sau khi payload đề đã tải; UI phản hồi dưới 100ms.
- Không có đáp án/lời giải trong dữ liệu trước khi nộp bài.
- Toàn bộ luồng làm bài hoàn thành bằng keyboard; trạng thái lưu, lỗi và xác nhận được screen reader thông báo.
- Bundle/CSS đạt ngân sách trong `tasks/plan.md`; Lighthouse/axe không còn lỗi mức critical/serious.
