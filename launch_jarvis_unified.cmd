@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if not errorlevel 1 (
    python "%~dp0launch_jarvis_unified.py"
    exit /b %ERRORLEVEL%
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0launch_jarvis_unified.py"
    exit /b %ERRORLEVEL%
)

where pythonw >nul 2>nul
if not errorlevel 1 (
    pythonw "%~dp0launch_jarvis_unified.py"
    exit /b %ERRORLEVEL%
)

echo JARVIS launcher requires Python 3.10+ to be installed and on PATH.
exit /b 1
