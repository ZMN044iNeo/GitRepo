Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get desktop path
strDesktop = objShell.SpecialFolders("Desktop")
strShortcutPath = strDesktop & "\JARVIS HUD.lnk"
strBatchPath = "e:\Users\pharo\Desktop\GitRepo\launch_jarvis.bat"

' Create shortcut object
Set objShortcut = objShell.CreateShortCut(strShortcutPath)
objShortcut.TargetPath = strBatchPath
objShortcut.WorkingDirectory = "e:\Users\pharo\Desktop\GitRepo"
objShortcut.Description = "Launch JARVIS HUD V4.0"
objShortcut.IconLocation = "C:\Windows\System32\cmd.exe"
objShortcut.Save()

WScript.Echo "✓ Desktop shortcut created: " & strShortcutPath
