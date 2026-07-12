"""Rebuild the local database from the source documents processed so far."""

from __future__ import annotations

from pathlib import Path

from scripts.import_excel import import_excel
from scripts.import_text_pdfs import import_text_pdf
from scripts.storage import create_database


ROOT = Path(__file__).resolve().parent.parent
DATABASE = ROOT / "data" / "review.db"


def main() -> None:
    if DATABASE.exists():
        DATABASE.unlink()
    create_database(DATABASE)
    import_excel(DATABASE, ROOT / "200_cau_hoi_CSLT.xlsx")
    for pdf_name in ("đề 1.pdf", "đề 2.pdf"):
        count = import_text_pdf(DATABASE, ROOT / pdf_name)
        print(f"{pdf_name}: {count} câu")


if __name__ == "__main__":
    main()
