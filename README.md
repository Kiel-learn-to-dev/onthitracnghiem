# CSLT Ôn thi

Webapp luyện trắc nghiệm Cơ sở lập trình. Mỗi đề gồm 40 câu theo blueprint 12 Dễ / 8 Vừa / 8 Khó / 12 Rất khó. Đáp án và lời giải không xuất hiện trước khi nộp.

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

Thao tác quản trị **Publish 10 đề chuẩn** chỉ chạy một lần và từ chối tạo thêm đề để không làm lặp câu. Mỗi đề giữ seed, snapshot và thứ tự câu trong SQLite.

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
