"""Create a Windows desktop shortcut for JARVIS HUD V4.0"""
import os
import sys
from pathlib import Path

def create_desktop_shortcut():
    """Create .lnk shortcut on user's desktop"""
    try:
        # Import Windows COM interface
        from win32com.client import Dispatch
    except ImportError:
        print("ERROR: pywin32 not installed. Installing now...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "pywin32"], 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            from win32com.client import Dispatch
        except ImportError:
            print("FAILED: Could not install pywin32. Create shortcut manually:")
            print("1. Right-click Desktop → New → Shortcut")
            print("2. Target: python.exe e:\\Users\\pharo\\Desktop\\GitRepo\\jarvis_hud.py")
            print("3. Start in: e:\\Users\\pharo\\Desktop\\GitRepo")
            print("4. Name: JARVIS HUD")
            return False

    desktop = Path.home() / "Desktop"
    shortcut_path = desktop / "JARVIS HUD.lnk"
    target_script = r"e:\Users\pharo\Desktop\GitRepo\jarvis_hud.py"
    working_dir = r"e:\Users\pharo\Desktop\GitRepo"

    try:
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.TargetPath = sys.executable  # python.exe
        shortcut.Arguments = f'"{target_script}"'
        shortcut.WorkingDirectory = working_dir
        shortcut.Description = "Launch JARVIS HUD V4.0"
        shortcut.IconLocation = r"C:\Windows\System32\cmd.exe,0"
        shortcut.save()
        
        print(f"✓ Desktop shortcut created: {shortcut_path}")
        print(f"  Target: {sys.executable}")
        print(f"  Arguments: {target_script}")
        print(f"  Start in: {working_dir}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to create shortcut: {e}")
        return False

if __name__ == "__main__":
    success = create_desktop_shortcut()
    sys.exit(0 if success else 1)
