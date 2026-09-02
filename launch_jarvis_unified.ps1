Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $PSScriptRoot

$python = $null
foreach ($candidate in @(
    "C:\Users\pharo\AppData\Local\Programs\Python\Python312\python.exe",
    "C:\Users\pharo\AppData\Local\Programs\Python\Python311\python.exe",
    "C:\Users\pharo\AppData\Local\Programs\Python\Python310\python.exe"
)) {
    if (Test-Path -LiteralPath $candidate) {
        $python = $candidate
        break
    }
}

if (-not $python) {
    $python = (Get-Command python -ErrorAction SilentlyContinue)?.Source
}

if (-not $python) {
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $python = "py"
    }
}

Write-Host "+----------------------------------------+" -ForegroundColor Cyan
Write-Host "|   JARVIS V4.0 UNIFIED LAUNCHER        |" -ForegroundColor Cyan
Write-Host "|   Tkinter HUD + Local Control Panel   |" -ForegroundColor Cyan
Write-Host "+----------------------------------------+" -ForegroundColor Cyan
Write-Host ""

Write-Host "[INIT] Python: $python" -ForegroundColor Yellow
Write-Host "[INIT] Repo: $PSScriptRoot" -ForegroundColor Yellow

if ($python -and ($python -ne "py")) {
    & $python "$PSScriptRoot\launch_jarvis_unified.py"
    exit $LASTEXITCODE
}

if ($python -eq "py") {
    & py -3 "$PSScriptRoot\launch_jarvis_unified.py"
    exit $LASTEXITCODE
}

Write-Error "Python executable not found. Install Python 3.10+ and try again."
exit 1
