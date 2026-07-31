@echo off
chcp 65001 > nul
rem Sky Strike 1942 啟動器（雙擊即可執行）
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
pause