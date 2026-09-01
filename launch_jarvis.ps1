Set-Location $PSScriptRoot

$python = "C:\Users\pharo\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

& $python "$PSScriptRoot\jarvis_hud.py"
