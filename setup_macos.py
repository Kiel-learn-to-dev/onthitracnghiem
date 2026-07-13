from pathlib import Path

from setuptools import setup


ROOT = Path(__file__).resolve().parent
DATA_FILES = [
    ("templates", [str(path) for path in (ROOT / "templates").glob("*.html")]),
    ("static", [str(path) for path in (ROOT / "static").glob("*") if path.is_file()]),
    ("data", [str(ROOT / "data" / "review.db")]),
]

setup(
    app=["desktop.py"],
    name="CSLT-OnThi",
    data_files=DATA_FILES,
    options={
        "py2app": {
            "argv_emulation": True,
            "plist": {
                "CFBundleDisplayName": "CSLT Ôn thi",
                "CFBundleIdentifier": "vn.csltonthi.desktop",
                "LSMinimumSystemVersion": "11.0",
            },
        }
    },
)
