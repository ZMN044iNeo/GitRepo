#!/usr/bin/env pwsh
<#
.SYNOPSIS
    JARVIS V4.0 Unified System Launcher
    Starts HUD (Tkinter) + Sync Server + optional Hologram Dashboard

.PARAMETER Hologram
    Enable Streamlit Hologram Dashboard (web UI)

.EXAMPLE
    .\launch_jarvis_unified.ps1
    .\launch_jarvis_unified.ps1 -Hologram
#>

param(
    [switch]$Hologram
)

# Setup
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $PSScriptRoot

# Find Python
$python = "C:\Users\pharo\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

# Build args
$args = @("launch_jarvis_unified.py")
if ($Hologram) {
    $args += "--hologram"
}

Write-Host "+----------------------------------------+" -ForegroundColor Cyan
Write-Host "|   JARVIS V4.0 UNIFIED LAUNCHER        |" -ForegroundColor Cyan
Write-Host "|   Tkinter HUD + WebSocket Sync        |" -ForegroundColor Cyan
if ($Hologram) {
    Write-Host "|   + Streamlit Hologram Dashboard      |" -ForegroundColor Cyan
}
Write-Host "+----------------------------------------+" -ForegroundColor Cyan
Write-Host ""

Write-Host "[INIT] Python: $python" -ForegroundColor Yellow
Write-Host "[INIT] Repo: $PSScriptRoot" -ForegroundColor Yellow

# Launch
& $python $args
