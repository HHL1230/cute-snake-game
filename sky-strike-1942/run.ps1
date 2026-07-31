# Sky Strike 1942 啟動腳本
# 自動建立虛擬環境、安裝相依套件並啟動遊戲

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "[1/2] 建立虛擬環境並安裝 pygame-ce ..." -ForegroundColor Cyan
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv venv
        uv pip install -r requirements.txt
    }
    else {
        python -m venv .venv
        & $python -m pip install --upgrade pip
        & $python -m pip install -r requirements.txt
    }
}

Write-Host "[2/2] 啟動 Sky Strike 1942 ..." -ForegroundColor Green
& $python main.py