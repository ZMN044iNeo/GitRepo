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
$legacyShortcutPath = Join-Path $desktop "JARVIS HUD V4.0.lnk"
$launcherPath = Join-Path $PSScriptRoot "launch_jarvis_unified.ps1"

if (-not (Test-Path -LiteralPath $launcherPath)) {
    throw "Jarvis launcher was not found: $launcherPath"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$launcherPath`""
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.WindowStyle = 1
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,220"
$shortcut.Description = "Launch JARVIS HUD V4.0 with the native control surface"
$shortcut.Save()

if ($legacyShortcutPath -ne $shortcutPath -and (Test-Path -LiteralPath $legacyShortcutPath)) {
    Remove-Item -LiteralPath $legacyShortcutPath -Force
}

Write-Host "Created shortcut: $shortcutPath"