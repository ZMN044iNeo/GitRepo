<#
.SYNOPSIS
    Creates or replaces the Jarvis desktop shortcut for this workspace.
#>

$desktopCandidates = @(
    [Environment]::GetFolderPath("Desktop"),
    (Split-Path -Parent $PSScriptRoot)
) | Select-Object -Unique

$desktop = $desktopCandidates | Where-Object {
    if (-not (Test-Path -LiteralPath $_)) { return $false }
    try {
        $probePath = Join-Path $_ ".jarvis-shortcut-write-test"
        [System.IO.File]::WriteAllText($probePath, "ok")
        Remove-Item -LiteralPath $probePath -Force
        return $true
    }
    catch {
        return $false
    }
} | Select-Object -First 1

if (-not $desktop) {
    throw "No writable Desktop location was found."
}

$shortcutPath = Join-Path $desktop "Jarvis.lnk"
$legacyShortcutPaths = @(
    (Join-Path $desktop "JARVIS HUD V4.0.lnk"),
    (Join-Path $desktop "launch_jarvis_unified.lnk"),
    (Join-Path $desktop "Jarvis HUD V4.0.lnk"),
    (Join-Path $desktop "JARVIS.lnk")
) | Select-Object -Unique

$cmdLauncher = Join-Path $PSScriptRoot "launch_jarvis_unified.cmd"
$batLauncher = Join-Path $PSScriptRoot "launch_jarvis_unified.bat"

if (-not (Test-Path -LiteralPath $cmdLauncher) -and -not (Test-Path -LiteralPath $batLauncher)) {
    throw "No working JARVIS launcher was found in the repo root."
}

$launcherToUse = if (Test-Path -LiteralPath $cmdLauncher) { $cmdLauncher } else { $batLauncher }

$pythonPath = $null
foreach ($candidate in @(
    "C:\Users\pharo\AppData\Local\Programs\Python\Python312\python.exe",
    "C:\Users\pharo\AppData\Local\Programs\Python\Python311\python.exe",
    "C:\Users\pharo\AppData\Local\Programs\Python\Python310\python.exe"
)) {
    if (Test-Path -LiteralPath $candidate) {
        $pythonPath = $candidate
        break
    }
}

if (-not $pythonPath) {
    $pythonPath = (Get-Command python -ErrorAction SilentlyContinue)?.Source
}

if (-not $pythonPath) {
    $pythonPath = (Get-Command py -ErrorAction SilentlyContinue)?.Source
}

if (-not $pythonPath) {
    $pythonPath = "C:\Windows\System32\cmd.exe"
}

foreach ($legacy in $legacyShortcutPaths) {
    if ($legacy -and $legacy -ne $shortcutPath -and (Test-Path -LiteralPath $legacy)) {
        Remove-Item -LiteralPath $legacy -Force
    }
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "C:\Windows\System32\cmd.exe"
$shortcut.Arguments = "/c \"\"$launcherToUse\"\""
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.WindowStyle = 1
$shortcut.IconLocation = "$pythonPath,0"
$shortcut.Description = "Launch JARVIS HUD V4.0 and native control surface"
$shortcut.Save()

Write-Host "Created working shortcut: $shortcutPath"
Write-Host "Launcher used: $launcherToUse"
