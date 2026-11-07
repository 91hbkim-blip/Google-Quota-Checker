@echo off
cd /d "%~dp0"

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:LOOP
cls
chcp 65001 > nul
python main.py
chcp 949 > nul

echo.
echo =======================================================
echo [Auto-Refresh: 20 mins (1200s)]
echo Press ENTER or SPACEBAR to refresh (F5) immediately.
echo (Press Ctrl + C or close window to exit)
echo =======================================================
timeout /t 1200
goto LOOP