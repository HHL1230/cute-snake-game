# Sky Strike 1942 啟動腳本
# 自動建立虛擬環境、安裝相依套件並啟動遊戲
# 用法：
#   .\run.ps1              啟動遊戲
#   .\run.ps1 -SelfCheck   只做環境自我檢查（開視窗 4 秒後自動關閉）

[CmdletBinding()]
param([switch]$SelfCheck)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

try {
    if (-not (Test-Path $python)) {
        Write-Host "[1/2] 建立虛擬環境並安裝 pygame-ce ..." -ForegroundColor Cyan
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            uv venv
            uv pip install -r requirements.txt
        }
        else {
            $sys = Get-Command python -ErrorAction SilentlyContinue
            if (-not $sys) { $sys = Get-Command py -ErrorAction SilentlyContinue }
            if (-not $sys) { throw "找不到 Python，請先安裝 Python 3.10 以上版本後再執行。" }
            & $sys.Source -m venv .venv
            & $python -m pip install --upgrade pip
            & $python -m pip install -r requirements.txt
        }
    }

    if (-not (Test-Path $python)) { throw "虛擬環境建立失敗，找不到 $python" }

    if ($SelfCheck) {
        Write-Host "[自我檢查] 執行 tools\window_check.py ..." -ForegroundColor Cyan
        & $python -u tools\window_check.py
    }
    else {
        Write-Host "[2/2] 啟動 Sky Strike 1942 ..." -ForegroundColor Green
        & $python main.py
    }

    if ($LASTEXITCODE -ne 0) { throw "程式以非零狀態結束 (exit=$LASTEXITCODE)" }
}
catch {
    Write-Host ""
    Write-Host "[錯誤] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}