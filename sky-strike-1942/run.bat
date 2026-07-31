@echo off
chcp 65001 > nul
cd /d "%~dp0"
rem Sky Strike 1942 launcher - double-click to play
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
if errorlevel 1 (
  echo.
  echo [ERROR] Launch failed. Please read the messages above.
)
pause
