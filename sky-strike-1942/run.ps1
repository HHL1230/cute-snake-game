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

    $exitCode = 0
    if ($SelfCheck) {
        Write-Host "[自我檢查] 執行 tools\window_check.py ..." -ForegroundColor Cyan
        & $python -u tools\window_check.py
        $exitCode = $LASTEXITCODE
    }
    else {
        Write-Host "[2/2] 啟動 Sky Strike 1942 ..." -ForegroundColor Green
        if (-not ("WinFg" -as [type])) {
            Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class WinFg {
    [DllImport("user32.dll")] public static extern bool AllowSetForegroundWindow(int dwProcessId);
    [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
        }
        $console = [IntPtr]::Zero
        try { $console = [WinFg]::GetConsoleWindow() } catch { }

        # 以子行程啟動，並把「可切換到前景」的權限授權給它，
        # 否則 Windows 會擋下遊戲視窗搶前景，導致視窗停在主控台後面、按鍵全無反應。
        $proc = Start-Process -FilePath $python -ArgumentList "main.py" -NoNewWindow -PassThru
        try { [void][WinFg]::AllowSetForegroundWindow($proc.Id) } catch { }

        # 遊戲執行期間把主控台視窗收起來，避免它一直霸佔前景把按鍵吃掉
        try {
            if ($console -ne [IntPtr]::Zero) {
                Start-Sleep -Milliseconds 1200
                [void][WinFg]::ShowWindow($console, 6)   # SW_MINIMIZE
            }
        }
        catch { }

        $proc.WaitForExit()
        $exitCode = $proc.ExitCode

        try {
            if ($console -ne [IntPtr]::Zero) { [void][WinFg]::ShowWindow($console, 9) }  # SW_RESTORE
        }
        catch { }
    }

    if ($null -eq $exitCode) { $exitCode = 0 }
    if ($exitCode -ne 0) { throw "程式以非零狀態結束 (exit=$exitCode)" }
}
catch {
    Write-Host ""
    Write-Host "[錯誤] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}