"""Restore OCR-derived Vietnamese display text from matching clean source questions."""

from __future__ import annotations

import difflib
import json
import re
import sqlite3
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


PHRASE_REPLACEMENTS = (
    ("thoat khoi", "thoát khỏi"), ("lap tuc", "lập tức"),
    ("hoac switch", "hoặc switch"), ("ngay lap", "ngay lập"),
    ("nhay toi", "nhảy tới"), ("keteip", "kế tiếp"),
    ("ketiep", "kế tiếp"), ("bo qua", "bỏ qua"),
    ("cho phep", "cho phép"), ("lay dia chi", "lấy địa chỉ"),
    ("truong kieu", "trường kiểu"), ("nhom bit", "nhóm bit"),
    ("xay dung", "xây dựng"), ("cac mang", "các mảng"),
    ("cau truc lap", "cấu trúc lặp"), ("kieu cua ham", "kiểu của hàm"),
    ("ten ham", "tên hàm"), ("bang", "bằng"), ("than vong", "thân vòng"),
    ("lap sau", "lặp sau"), ("lap truoc", "lặp trước"),
    ("chao ban", "chào bạn"), ("chao cac", "chào các"), ("chao", "chào"),
    ("nhan cu the", "nhãn cụ thể"), ("bo qua", "bỏ qua"),
    ("phan con lai", "phần còn lại"), ("chuyen sang", "chuyển sang"),
    ("ke tiep", "kế tiếp"), ("phan tu thu", "phần tử thứ"),
    ("day du", "đầy đủ"), ("cau lenh", "câu lệnh"),
    ("trinh bien dich", "trình biên dịch"), ("su dung", "sử dụng"),
    ("nguyen mau", "nguyên mẫu"), ("xac minh", "xác minh"),
    ("loi goi", "lời gọi"), ("tham so", "tham số"),
    ("ket thuc", "kết thúc"), ("thu tu", "thứ tự"),
    ("than vong lap", "thân vòng lặp"), ("kiem tra", "kiểm tra"),
    ("dieu kien", "điều kiện"), ("ep kieu", "ép kiểu"),
    ("so phurc", "số thực"), ("phuong an", "phương án"),
    ("phurong an", "phương án"), ("so lurong", "số lượng"),
    ("phurong", "phương"), ("tur", "từ"), ("thur", "thứ"),
    ("sir dung", "sử dụng"), ("thyc hien", "thực hiện"),
    ("truoc", "trước"), ("trc", "trước"),
    ("tại su đúng", "tái sử dụng"), ("tai su dung", "tái sử dụng"),
    ("de bao tri", "để bảo trì"), ("bao tri", "bảo trì"),
    ("doan lenh", "đoạn lệnh"), ("tac dung", "tác dụng"),
    ("bat ky", "bất kỳ"), ("bo dem", "bộ đệm"),
    ("ky từ", "ký tự"), ("ky tu", "ký tự"),
    ("kieu số", "kiểu số"), ("ngon ngữ", "ngôn ngữ"),
    ("con tr?", "con trỏ"), ("m?ng", "mảng"),
    ("nao duoi day", "nào dưới đây"), ("kieu co ban", "kiểu cơ bản"),
    ("co ban", "cơ bản"), ("gia sur", "giả sử"),
    ("bieu thurc", "biểu thức"), ("toan tur", "toán tử"),
    ("cu phap", "cú pháp"), ("he so", "hệ số"),
    ("trong cac", "trong các"), ("thu tuc", "thủ tục"),
    ("hanh vi", "hành vi"), ("dinh nghia", "định nghĩa"),
    ("nguoi dung", "người dùng"), ("nhieu", "nhiều"),
    ("cung scope", "cùng scope"), ("pham vi", "phạm vi"),
    ("ky tu", "ký tự"), ("ban phim", "bàn phím"),
    ("quy uoc", "quy ước"), ("phuong an", "phương án"),
    ("loi ich", "lợi ích"), ("bao tri", "bảo trì"),
    ("ngon ngur", "ngôn ngữ"), ("ngon ngu", "ngôn ngữ"),
    ("lap trinh", "lập trình"), ("phat trien", "phát triển"),
    ("dua tren", "dựa trên"), ("kieu dir lieu", "kiểu dữ liệu"),
    ("kieu dur lieu", "kiểu dữ liệu"), ("kieu du lieu", "kiểu dữ liệu"),
    ("du lieu", "dữ liệu"), ("bien toan cuc", "biến toàn cục"),
    ("bien dia phuong", "biến địa phương"), ("con tro", "con trỏ"),
    ("cau truc", "cấu trúc"), ("khai bao", "khai báo"),
    ("ben trong", "bên trong"), ("ben ngoai", "bên ngoài"),
    ("tat ca", "tất cả"), ("ke ca", "kể cả"), ("mien nho", "miền nhớ"),
    ("thay doi", "thay đổi"), ("qua trinh", "quá trình"),
    ("thuc hien", "thực hiện"), ("chuong trinh", "chương trình"),
    ("gia tri", "giá trị"), ("bieu thuc", "biểu thức"),
    ("khong dung", "không đúng"), ("xau dinh dang", "xâu định dạng"),
    ("so nguyen", "số nguyên"), ("so thuc", "số thực"),
    ("duoc phep", "được phép"), ("dung de", "dùng để"),
    ("vi tri", "vị trí"), ("man hinh", "màn hình"),
    ("toa do", "tọa độ"), ("danh sach", "danh sách"),
    ("do dai", "độ dài"), ("kich thuoc", "kích thước"),
    ("vung nho", "vùng nhớ"), ("cap phat", "cấp phát"),
    ("phan tu", "phần tử"), ("mang mot", "mảng một"),
    ("nhieu chieu", "nhiều chiều"), ("truy cap", "truy cập"),
    ("phat bieu", "phát biểu"), ("khong co", "không có"),
    ("khong phai", "không phải"), ("khong the", "không thể"),
    ("khong xac dinh", "không xác định"), ("tat ca", "tất cả"),
    ("bao loi", "báo lỗi"), ("loi bien dich", "lỗi biên dịch"),
    ("loi runtime", "lỗi runtime"), ("vong lap", "vòng lặp"),
    ("vo han", "vô hạn"), ("day huu han", "dãy hữu hạn"),
    ("bai toan", "bài toán"), ("mot chuong", "một chương"),
    ("mot ngon", "một ngôn"), ("mot bien", "một biến"),
    ("mot so", "một số"), ("mot mang", "một mảng"),
    ("mot ham", "một hàm"), ("mot cach", "một cách"),
    ("cua mot", "của một"), ("cua cac", "của các"),
    ("cua bien", "của biến"), ("cua ham", "của hàm"),
    ("cua mang", "của mảng"), ("cua cau", "của câu"),
    ("de bao", "để bảo"), ("de cai", "để cài"),
    ("de hien", "để hiển"), ("de in", "để in"),
    ("de mo", "để mở"), ("de doc", "để đọc"),
)

WORD_REPLACEMENTS = {
    "khong": "không", "duoc": "được", "dung": "đúng", "sai": "sai",
    "la": "là", "va": "và", "cua": "của", "voi": "với", "trong": "trong",
    "ngoai": "ngoài", "noi": "nối", "noi": "nối", "nay": "này", "do": "đó",
    "mot": "một", "cac": "các", "nhung": "những", "nguoi": "người",
    "ten": "tên", "quy tac": "quy tắc", "viet": "viết", "dau": "đầu",
    "cuoi": "cuối", "tep": "tệp", "tap tin": "tập tin", "nhap": "nhập",
    "xoa": "xóa", "bo": "bộ", "doc": "đọc", "luu": "lưu", "dat": "đặt",
    "tai": "tại", "cot": "cột", "dong": "dòng", "di chuyen": "di chuyển",
    "dem": "đệm", "tac": "tác", "tri": "trì", "nao": "nào",
    "toi": "tới", "tu": "từ", "den": "đến", "chi": "chỉ", "chi thi": "chỉ thị",
    "ro rang": "rõ ràng", "giai": "giải", "phan": "phần", "tuong": "tương",
    "duong": "đường", "dan": "dẫn", "he dieu hanh": "hệ điều hành",
    "tai su dung": "tái sử dụng", "tranh lap ma": "tránh lặp mã",
}


MANUAL_CHOICE_OVERRIDES = {
    225: ["Khi đọc kí tự có mã 1A từ file văn bản, C sẽ đọc thành kí tự có mã -1.", "Khi đọc file văn bản, cả hai kí tự 0D và 0A sẽ được C đọc thành một kí tự có mã 0A.", "Khi đọc kí tự có mã 0D từ file văn bản thì C sẽ bỏ qua.", "1, 2 và 3 đều đúng."],
    244: ["Độ dài các trường không vượt quá 16 bit.", "Áp dụng được cho các trường có kiểu số nguyên và số thực.", "Cho phép lấy địa chỉ trường kiểu nhóm bit.", "Xây dựng các mảng kiểu nhóm bit."],
    478: ["Mảng là kiểu do người dùng định nghĩa.", "Mảng có một hoặc nhiều chiều.", "Truy cập qua chỉ số.", "A và D không đúng."],
    659: ["Mở tệp nhị phân để ghi.", "Xóa nội dung của tệp. Cờ O_TRUNC có nghĩa là cắt ngắn tệp về độ dài 0.", "Mở tệp văn bản để đọc và ghi.", "Tất cả các đáp án trên."],
    672: ["Cấu trúc ra quyết định if-else.", "Cấu trúc lặp while.", "Cấu trúc lặp for.", "Cấu trúc lặp do-while."],
    683: ["Kiểu của hàm, tên hàm, kiểu và tên các tham số.", "Kiểu của hàm, danh sách tham số, kết thúc bằng dấu chấm phẩy.", "Kiểu của hàm, kiểu và thứ tự các tham số.", "Kiểu của hàm, tên hàm, kiểu và thứ tự các tham số, kết thúc bằng dấu chấm phẩy."],
    696: ["Vòng lặp do-while thực hiện thân vòng lặp trước, kiểm tra điều kiện lặp sau.", "Vòng lặp do-while dễ sử dụng hơn các vòng lặp khác.", "Vòng lặp do-while thực hiện thân vòng lặp sau, kiểm tra điều kiện lặp trước.", "Vòng lặp do-while nhìn đẹp hơn các vòng lặp khác."],
    209: ["“29b”.", "“29h b”.", "“29h”.", "Kết quả khác."],
    216: ["Nhập vào 1 kí tự cho đến khi gặp kí tự `*`.", "Nhập vào các kí tự cho tới khi gặp kí tự `*`.", "Nhập các kí tự `*`.", "Lỗi khi xây dựng chương trình."],
    223: ["6 chuỗi “Hello”.", "12 chuỗi “Hello”.", "Không có kết quả xuất ra màn hình.", "23 chuỗi “Hello”."],
    231: ["Mở tệp nhị phân để ghi.", "Xóa nội dung của tệp.", "Mở tệp văn bản để đọc và ghi.", "Tất cả các đáp án trên."],
    232: ["(*p).a;", "*p->a;", "A và B đều đúng.", "A và B đều sai."],
    238: ["“FFE6FFE6”.", "“FFE6FFE7”.", "“FFE66EFF”.", "Kết quả khác."],
    241: ["-4.", "2.", "5.", "Không có kết quả đúng."],
    247: ["Câu lệnh bị lỗi.", "Giá trị info trong phần tử thứ 3 đã bị thay đổi.", "Giá trị info trong phần tử thứ 2 đã bị thay đổi.", "Giá trị info trong phần tử bất kỳ đã bị thay đổi."],
    251: ["A[chỉ_số].tên_trường;", "A.tên_trường;", "&A.tên_trường;", "&A[chỉ_số].tên_trường;"],
    310: ["Vẽ một điểm tại tọa độ (x, y).", "Lấy giá trị màu của điểm tại tọa độ (x, y).", "Vẽ một điểm tại vị trí con trỏ.", "Cả 3 phương án đều sai."],
    313: ["Thiết lập màu nền.", "Đặt màu vẽ hiện tại.", "Cả 2 ý trên đều đúng.", "Cả hai ý trên đều sai."],
    315: ["0 đến 255.", "-32768 đến 32767.", "-128 đến 127.", "0 đến 65535."],
    317: ["12.", "10.", "8.", "Kết quả khác."],
    321: ["98.", "b.", "B.", "Kết quả khác."],
    325: ["“1 2 3 4”.", "“4”.", "“3”.", "Kết quả khác."],
    328: ["“21 15”.", "“15 21”.", "Báo lỗi khi thực hiện chương trình.", "Kết quả khác."],
    331: ["“16”.", "“16.00”.", "“16.67”.", "Kết quả khác."],
    337: ["5.", "10.", "0.", "Báo lỗi khi thực hiện chương trình."],
    338: ["5.", "10.", "0.", "Báo lỗi khi thực hiện chương trình."],
    341: ["Số phần tử tối đa của mảng.", "Kích thước bộ nhớ sẽ cấp phát cho mảng.", "Cả hai câu trên đều đúng.", "Cả hai câu trên đều sai."],
    345: ["“Chào Các Bạn”.", "“Chào Các”.", "“Chào”.", "Không hiển thị kết quả gì."],
    349: ["Dãy kết quả là: 63.20, -45.60, 70.10, 3.60, 14.50.", "Dãy kết quả là: 14.50, 3.60, 70.10, -45.60, 63.20.", "Kết quả khác.", "1 và 2."],
    350: ["Nhập vào một kí tự thường, sau đó chuyển sang chữ hoa rồi in ra màn hình.", "Nhập một kí tự hoa, sau đó chuyển sang chữ thường rồi in ra màn hình.", "1 và 2.", "Kết quả khác."],
    358: ["Khai báo biến cho cấu trúc để ta không cần sử dụng từ khóa struct nữa.", "Khai báo biến cho loại cấu trúc để ta cần sử dụng từ khóa struct.", "Không thể khai báo thêm biến cấu trúc nào nữa.", "Không có đáp án đúng."],
    383: ["Góc trên bên trái.", "Góc trên bên phải.", "Góc dưới bên trái.", "Góc dưới bên phải."],
    385: ["outtextxy(int x, int y, char far *textstring);", "outtext(char far *textstring);", "settextstyle(int font, int direction, int charsize);", "Cả 3 phương án trên."],
    390: ["“%ld”.", "“%x”.", "“%d”.", "Kết quả khác."],
    407: ["getch();", "closegraph();", "Cả 2 phương án trên đều sai.", "Cả 2 phương án trên đều đúng."],
    428: ["Đoạn code gây lỗi. (Đoạn code không báo lỗi nhưng sai mode.)", "Đoạn code không lỗi.", "Đoạn code này sẽ ghi trị 7 lên file “FL.txt”.", "Đoạn code này sẽ đọc một trị từ file “FL.txt” vào biến n."],
    499: ["Kiểu double.", "Kiểu con trỏ.", "Kiểu hợp.", "Kiểu mảng."],
    690: ["Tại vì hàm nhận được bản sao của giá trị gốc chứ không phải là giá trị gốc nên mọi thay đổi trên bản sao này không hề ảnh hưởng đến giá trị gốc ban đầu.", "Tại vì hàm nhận được bản gốc của giá trị ban đầu nên khi có sự thay đổi xảy ra thì giá trị bản sao không truyền đi nên không bị ảnh hưởng.", "Tại vì hàm được gọi để làm thay đổi một biến khác.", "Tại vì hàm được gọi không thể tác động đến bất kỳ sự thay đổi nào của biến dùng làm đối số truyền đi."],
}

MANUAL_DUPLICATE_TARGETS = {
    209: (562,), 223: (622,), 225: (632,), 231: (658,), 232: (714,),
    317: (516, 529, 610, 611, 612), 325: (591,), 328: (546,),
    341: (626,), 390: (506,), 428: (629,),
}

MANUAL_EXPLANATION_OVERRIDES = {
    295: "Đáp án đúng là B: Đặt con trỏ tại cột x, dòng y. gotoxy(x, y) của conio.h đặt con trỏ ở cột x, dòng y; đây là hàm đặc thù của Turbo C/console, không thuộc ISO C.",
    583: "Đáp án đúng là B: Đặt con trỏ tại cột x, dòng y. gotoxy(x, y) của conio.h đặt con trỏ ở cột x, dòng y; đây là hàm đặc thù của Turbo C/console, không thuộc ISO C.",
}


def _preserve_initial_case(match: re.Match[str], replacement: str) -> str:
    return replacement[:1].upper() + replacement[1:] if match.group(0)[:1].isupper() else replacement


def restore_ocr_quotes(text: str) -> str:
    """Restore a pair of quotation marks that a legacy PDF extractor emitted as ``?``."""
    match = re.fullmatch(r"\?([^?]+)\?([.,;:]?)", text.strip())
    if match is None:
        return text
    return f"“{match.group(1)}”{match.group(2)}"


def restore_vietnamese_phrases(text: str) -> str:
    """Restore unambiguous Vietnamese prose while leaving C syntax intact."""
    restored = restore_ocr_quotes(text)
    for source, replacement in PHRASE_REPLACEMENTS:
        restored = re.sub(
            rf"(?<!\w){re.escape(source)}(?!\w)",
            lambda match: _preserve_initial_case(match, replacement),
            restored,
            flags=re.IGNORECASE,
        )
    for source, replacement in WORD_REPLACEMENTS.items():
        restored = re.sub(
            rf"(?<!\w){re.escape(source)}(?!\w)",
            lambda match: _preserve_initial_case(match, replacement),
            restored,
            flags=re.IGNORECASE,
        )
    replacements = {
        "Ki?u": "Kiểu", "ki?u": "kiểu", "h?p": "hợp", "Kh?ng": "Không",
        "kh?ng": "không", "c?u": "câu", "n?o": "nào", "??ng": "đúng",
        "K?t qu?": "Kết quả", "k?t qu?": "kết quả",
        "phài": "phải", "đươc": "được",
    }
    for source, replacement in replacements.items():
        restored = restored.replace(source, replacement)
    return restored


def comparable_text(text: str) -> str:
    """Fold Vietnamese accents and common OCR substitutions for comparison only."""
    normalized = unicodedata.normalize("NFD", text.casefold())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = normalized.replace("đ", "d")
    for broken, corrected in (
        ("ngur", "ngu"), ("dur", "du"), ("dir", "du"), ("xur", "xu"),
        ("thur", "thu"), ("trur", "tru"), ("n6", "no"), ("dennish", "dennis"),
    ):
        normalized = normalized.replace(broken, corrected)
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def comparison_variants(text: str) -> tuple[str, ...]:
    """Include the initial prompt line because OCR often appends answer notes."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    full = comparable_text(text)
    if not lines:
        return (full,)
    first_line = comparable_text(lines[0])
    return tuple(dict.fromkeys((full, first_line)))


def best_authoritative_match(target: str, candidates: list[tuple[int, str]]) -> tuple[int, float]:
    """Return the closest clean source question and its deterministic similarity score."""
    target_keys = comparison_variants(target)

    def score_candidate(candidate: tuple[int, str]) -> float:
        return max(
            difflib.SequenceMatcher(None, left, right, autojunk=False).ratio()
            for left in target_keys
            for right in comparison_variants(candidate[1])
        )

    matched_id, matched_text = max(candidates, key=score_candidate)
    score = score_candidate((matched_id, matched_text))
    return matched_id, score


def restore_from_authoritative_duplicates(db_path: Path, threshold: float = 0.92) -> dict[str, int]:
    """Copy display text only when the answer key agrees with a clean duplicate."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT source.id AS source_question_id, source.source_id, source.canonical_id,
                   canonical.id, canonical.question, canonical.choices_json,
                   canonical.answer, canonical.explanation, canonical.topic, canonical.difficulty
            FROM source_questions AS source
            JOIN canonical_questions AS canonical ON canonical.id = source.canonical_id
            """
        ).fetchall()
        clean = [row for row in rows if row["source_id"] != 4]
        ocr = [row for row in rows if row["source_id"] == 4]
        restored = 0
        skipped = 0
        with connection:
            for target in ocr:
                candidate_id, score = best_authoritative_match(
                    target["question"], [(row["id"], row["question"]) for row in clean]
                )
                source = next(row for row in clean if row["id"] == candidate_id)
                if score < threshold:
                    skipped += 1
                    continue
                choices = json.loads(source["choices_json"])
                answer_index = "ABCD".index(target["answer"])
                suffix_marker = "Đây là phương án phù hợp"
                suffix = source["explanation"]
                if suffix_marker in suffix:
                    suffix = suffix[suffix.index(suffix_marker):]
                explanation = f"Đáp án đúng là {target['answer']}: {choices[answer_index]}. {suffix}"
                connection.execute(
                    """
                    UPDATE canonical_questions
                    SET question = ?, choices_json = ?, explanation = ?, topic = ?, difficulty = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        source["question"], source["choices_json"], explanation,
                        source["topic"], source["difficulty"], target["canonical_id"],
                    ),
                )
                connection.execute(
                    """
                    UPDATE source_questions
                    SET raw_choices_json = ?, solution = ?, answer_reason = ?
                    WHERE id = ?
                    """,
                    (
                        source["choices_json"], explanation,
                        f"Restored Vietnamese display text from clean duplicate canonical question {source['id']}.",
                        target["source_question_id"],
                    ),
                )
                restored += 1
        return {"restored": restored, "skipped": skipped}
    finally:
        connection.close()


def restore_remaining_display_text(db_path: Path) -> int:
    """Apply conservative diacritic fixes to unmatched PDF/OCR display records."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    changed = 0
    try:
        rows = connection.execute(
            """
            SELECT source.id AS source_question_id, source.canonical_id, canonical.question,
                   canonical.choices_json, canonical.answer, canonical.explanation
            FROM source_questions AS source
            JOIN canonical_questions AS canonical ON canonical.id = source.canonical_id
            WHERE source.source_id IN (2, 3, 4)
            """
        ).fetchall()
        with connection:
            for row in rows:
                choices = [restore_vietnamese_phrases(choice) for choice in json.loads(row["choices_json"])]
                question = restore_vietnamese_phrases(row["question"])
                explanation = restore_vietnamese_phrases(row["explanation"])
                answer_index = "ABCD".index(row["answer"])
                suffix_marker = "Đây là phương án phù hợp"
                if suffix_marker in explanation:
                    explanation = (
                        f"Đáp án đúng là {row['answer']}: {choices[answer_index]}. "
                        + explanation[explanation.index(suffix_marker):]
                    )
                if (question, choices, explanation) == (
                    row["question"], json.loads(row["choices_json"]), row["explanation"]
                ):
                    continue
                choices_json = json.dumps(choices, ensure_ascii=False)
                connection.execute(
                    """
                    UPDATE canonical_questions
                    SET question = ?, choices_json = ?, explanation = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (question, choices_json, explanation, row["canonical_id"]),
                )
                connection.execute(
                    "UPDATE source_questions SET raw_choices_json = ?, solution = ? WHERE id = ?",
                    (choices_json, explanation, row["source_question_id"]),
                )
                changed += 1
            for canonical_id, explanation in MANUAL_EXPLANATION_OVERRIDES.items():
                connection.execute(
                    "UPDATE canonical_questions SET explanation = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (explanation, canonical_id),
                )
                connection.execute(
                    "UPDATE source_questions SET solution = ? WHERE canonical_id = ?",
                    (explanation, canonical_id),
                )
        return changed
    finally:
        connection.close()


def apply_manual_choice_overrides(db_path: Path) -> int:
    """Apply reviewed Vietnamese wording for legacy PDF encoding failures."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    changed = 0
    try:
        with connection:
            for canonical_id, choices in MANUAL_CHOICE_OVERRIDES.items():
                row = connection.execute(
                    "SELECT answer, explanation FROM canonical_questions WHERE id = ?", (canonical_id,)
                ).fetchone()
                if row is None:
                    continue
                suffix_marker = "Đây là phương án phù hợp"
                suffix = row["explanation"]
                if suffix_marker in suffix:
                    suffix = suffix[suffix.index(suffix_marker):]
                explanation = f"Đáp án đúng là {row['answer']}: {choices['ABCD'.index(row['answer'])]}. {suffix}"
                choices_json = json.dumps(choices, ensure_ascii=False)
                connection.execute(
                    "UPDATE canonical_questions SET choices_json = ?, explanation = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (choices_json, explanation, canonical_id),
                )
                connection.execute(
                    "UPDATE source_questions SET raw_choices_json = ?, solution = ? WHERE canonical_id = ?",
                    (choices_json, explanation, canonical_id),
                )
                for duplicate_id in MANUAL_DUPLICATE_TARGETS.get(canonical_id, ()):
                    duplicate = connection.execute(
                        "SELECT answer, explanation FROM canonical_questions WHERE id = ?", (duplicate_id,)
                    ).fetchone()
                    if duplicate is None:
                        continue
                    duplicate_suffix = duplicate["explanation"]
                    if suffix_marker in duplicate_suffix:
                        duplicate_suffix = duplicate_suffix[duplicate_suffix.index(suffix_marker):]
                    duplicate_explanation = (
                        f"Đáp án đúng là {duplicate['answer']}: "
                        f"{choices['ABCD'.index(duplicate['answer'])]}. {duplicate_suffix}"
                    )
                    connection.execute(
                        "UPDATE canonical_questions SET choices_json = ?, explanation = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (choices_json, duplicate_explanation, duplicate_id),
                    )
                    connection.execute(
                        "UPDATE source_questions SET raw_choices_json = ?, solution = ? WHERE canonical_id = ?",
                        (choices_json, duplicate_explanation, duplicate_id),
                    )
                changed += 1
        return changed
    finally:
        connection.close()


def main() -> None:
    database = ROOT / "data" / "review.db"
    print(restore_from_authoritative_duplicates(database))
    print({"phrase_restored": restore_remaining_display_text(database)})
    print({"manual_restored": apply_manual_choice_overrides(database)})


if __name__ == "__main__":
    main()
