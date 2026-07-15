# CSLT Ôn thi

Webapp luyện trắc nghiệm nhiều môn. Đáp án và lời giải không xuất hiện trước khi nộp bài; sau khi nộp, người học có thể xem lại bài trong lịch sử 7 ngày.

## Chạy ứng dụng

```powershell
py -m pip install -r requirements.txt
npm.cmd ci
npm.cmd run build
$env:CSLT_ADMIN_TOKEN = "một-chuỗi-ngẫu-nhiên-dài"
py -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Mở `http://127.0.0.1:8000`. Trang `/admin` yêu cầu giá trị `CSLT_ADMIN_TOKEN`; mã không được lưu trong trình duyệt.

## Dữ liệu và phát hành

Chuẩn hóa pool hiện có rồi chạy app:

```powershell
py -m scripts.release_pool
```

Import thêm ngân hàng HTTTQL từ file HTML có `SOURCE_QUESTIONS`:

```powershell
py -m scripts.import_htttql_html F:\Downloads\HTTTQL_30_BO_DE_40_CAU_NANG_CAP.html --db data\review.db
```

Nên backup `data\review.db` trước khi import. Lần import file `HTTTQL_30_BO_DE_40_CAU_NANG_CAP.html` ngày 2026-07-15 đọc 1.200 câu và thêm 296 câu canonical HTTTQL chưa có.

Tạo hoặc refresh 10 đề mẫu HTTTQL:

```powershell
py -c "from pathlib import Path; from scripts.storage import create_database; from scripts.exams import publish_htttql_sample_exams; db=Path('data/review.db'); create_database(db); exams=publish_htttql_sample_exams(db); print(len(exams))"
```

Lệnh này idempotent: chạy lại sẽ trả về bộ đề đã có thay vì tạo thêm. Mỗi đề HTTTQL có 40 câu, nội bộ dùng 4 Dễ / 8 Vừa / 16 Khó / 12 Rất khó; tỷ lệ này dùng để kiểm tra dữ liệu và không hiển thị trên UI học viên. Nên backup `data\review.db` trước khi import hoặc refresh đề mẫu.

Thao tác quản trị **Publish 10 đề chuẩn** dành cho CSLT chỉ chạy một lần và từ chối tạo thêm đề để không làm lặp câu. Mỗi đề giữ seed, snapshot và thứ tự câu trong SQLite.

## Hành vi học viên

- Phần **Chọn đề có sẵn** có bộ chọn môn riêng và chỉ hiển thị đề đã publish của môn đang chọn.
- Phần **Xem lại đề đã làm** hiển thị các bài đã nộp trong 7 ngày gần nhất.
- Bài làm từ đề publish có tag `Đề có sẵn` và nhãn `Đã làm X lần` tính theo số lượt nộp của cùng đề đó.
- Bài làm từ đề tạo ngẫu nhiên/custom có tag `Đề ngẫu nhiên`.

## Backup và restore

Tạo bản sao nhất quán khi app đang chạy:

```powershell
py -m scripts.backup_database backup data/review.db backups/review-2026-07-13.db
```

Để khôi phục, dừng app trước rồi chạy vào một file đích hoặc ghi đè `data/review.db` sau khi đã có thêm một backup an toàn:

```powershell
py -m scripts.backup_database restore backups/review-2026-07-13.db data/review.db
```

## Kiểm tra

```powershell
py -m unittest discover -s tests -v
npm.cmd run build
npm.cmd audit --omit=dev
```

## Ứng dụng desktop

Windows được đóng gói thành ứng dụng native dùng **Microsoft Edge WebView2**. Trình cài đặt cài runtime Evergreen của Microsoft khi máy chưa có runtime này, nên dùng được trên máy Windows khác có Internet.

```powershell
winget install --id JRSoftware.InnoSetup --exact --accept-source-agreements --accept-package-agreements
.\scripts\build_desktop_windows.ps1
```

Tệp cài đặt được tạo tại `output\CSLT-OnThi-Setup-1.0.0.exe`.

macOS không chạy `.exe`; cùng mã nguồn được đóng gói thành `.app`/`.dmg` qua WebKit native. Chạy lệnh sau **trên máy macOS** (hoặc runner macOS) để tạo `output/CSLT-OnThi-1.0.0.dmg`:

```bash
chmod +x scripts/build_desktop_macos.sh
./scripts/build_desktop_macos.sh
```
