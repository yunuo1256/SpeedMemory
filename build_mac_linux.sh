#!/usr/bin/env bash
# ============================================================
#  Speed Memory - macOS / Linux packaging script
#  macOS output: dist/SpeedMemory ; Linux output: dist/SpeedMemory
# ============================================================
set -e
cd "$(dirname "$0")"

echo "[1/3] Installing PyInstaller ..."
python3 -m pip install --upgrade pyinstaller

echo "[2/3] Building ..."
python3 -m PyInstaller --noconfirm --clean --onefile --windowed \
  --name SpeedMemory \
  --icon icon.ico \
  --add-data "icon.ico:." \
  --add-data "assets:assets" \
  speed_memory.py

echo "[3/3] Done! Output: dist/SpeedMemory"
echo "Place the executable in any folder and run it. On first launch"
echo "the questions folder is created automatically."
