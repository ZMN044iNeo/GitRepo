Set objWS = CreateObject("WScript.Shell")
Set objFS = CreateObject("Scripting.FileSystemObject")

strDesktop = objWS.SpecialFolders("Desktop")
strRepo = "E:\Users\pharo\Desktop\GitRepo"
strLauncher = strRepo & "\launch_jarvis_unified.cmd"
strShortcut = strDesktop & "\Jarvis.lnk"

legacy = Array(_
    strDesktop & "\JARVIS HUD V4.0.lnk", _
    strDesktop & "\launch_jarvis_unified.lnk", _
    strDesktop & "\Jarvis HUD V4.0.lnk", _
    strDesktop & "\JARVIS.lnk", _
    strDesktop & "\Jarvis Desktop Launcher.lnk", _
    strDesktop & "\Jarvis.lnk"
)

For Each item In legacy
    If objFS.FileExists(item) Then
        objFS.DeleteFile item, True
    End If
Next

Set shortcut = objWS.CreateShortcut(strShortcut)
shortcut.TargetPath = "C:\Windows\System32\cmd.exe"
shortcut.Arguments = "/c """ & strLauncher & """"
shortcut.WorkingDirectory = strRepo
shortcut.WindowStyle = 1
shortcut.IconLocation = "C:\Windows\System32\cmd.exe,0"
shortcut.Description = "Launch JARVIS HUD V4.0"
shortcut.Save

WScript.Echo "Created: " & strShortcut
WScript.Echo "Launcher: " & strLauncher
