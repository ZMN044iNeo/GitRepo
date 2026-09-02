#!/usr/bin/env pwsh
<#
.SYNOPSIS
    JARVIS V4.0 Unified System Launcher
    Starts the local Tkinter HUD and native control surface.

.EXAMPLE
    .\launch_jarvis_unified.ps1
#>

# Setup
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $PSScriptRoot

# Find Python
$python = "C:\Users\pharo\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

Write-Host "+----------------------------------------+" -ForegroundColor Cyan
Write-Host "|   JARVIS V4.0 UNIFIED LAUNCHER        |" -ForegroundColor Cyan
Write-Host "|   Tkinter HUD + Local Control Panel   |" -ForegroundColor Cyan
Write-Host "+----------------------------------------+" -ForegroundColor Cyan
Write-Host ""

Write-Host "[INIT] Python: $python" -ForegroundColor Yellow
Write-Host "[INIT] Repo: $PSScriptRoot" -ForegroundColor Yellow

# Launch
& $python "$PSScriptRoot\launch_jarvis_unified.py"
