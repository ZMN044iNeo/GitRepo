@echo off
setlocal
set "SCRIPT_DIR=%~dp0"

where powershell.exe >nul 2>nul
if not errorlevel 1 (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%launch_jarvis_unified.ps1"
    exit /b %ERRORLEVEL%
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%SCRIPT_DIR%launch_jarvis_unified.py"
    exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if not errorlevel 1 (
    python "%SCRIPT_DIR%launch_jarvis_unified.py"
    exit /b %ERRORLEVEL%
)

echo JARVIS launcher requires Python 3.10+ to be installed and on PATH.
exit /b 1
