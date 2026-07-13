#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m pip install -r requirements-macos.txt
npm run build
rm -rf build dist
python3 setup_macos.py py2app
mkdir -p output
hdiutil create -volname "CSLT Ôn thi" -srcfolder "dist/CSLT-OnThi.app" -ov -format UDZO "output/CSLT-OnThi-1.0.0.dmg"
