@echo off
setlocal
cd /d "%~dp0"

if exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_jarvis_unified.ps1"
    exit /b %ERRORLEVEL%
)

if exist "%SystemRoot%\System32\cmd.exe" (
    echo JARVIS launcher requires PowerShell to run.
)

exit /b 1
