@echo off
rem ============================================================
rem  Speed Memory - Windows packaging script
rem  Double-click to run. Output: dist\SpeedMemory.exe
rem  (--windowed, no console window)
rem ============================================================
chcp 65001 >nul
cd /d %~dp0

echo [1/3] Checking / installing PyInstaller ...
python -m pip install --upgrade pyinstaller || goto :error

echo [2/3] Building ...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name SpeedMemory ^
  --icon icon.ico ^
  --add-data "icon.ico;." ^
  --add-data "assets;assets" ^
  speed_memory.py || goto :error

echo [3/3] Done!
echo.
echo Output: dist\SpeedMemory.exe
echo Place the exe in any folder and double-click to run. On first
echo launch the questions folder is created automatically.
pause
exit /b 0

:error
echo.
echo Build failed. Check the error messages above (Python 3.8+ with
echo tcl/tk enabled is required).
pause
exit /b 1
