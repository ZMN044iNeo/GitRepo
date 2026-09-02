"""JARVIS local desktop launcher."""
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def log(msg: str, level: str = "INFO") -> None:
    """Print with timestamp."""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")


def install_voice_stack() -> bool:
    """Best-effort install for the optional local voice stack."""
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "numpy", "sounddevice", "openai-whisper"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def start_hud() -> None:
    """Start the Tkinter HUD as a GUI-safe process."""
    log("Starting JARVIS HUD V4.0...", "INIT")
    try:
        import whisper  # noqa: F401
        import sounddevice  # noqa: F401
        import numpy  # noqa: F401
    except ImportError:
        # Optional voice stack is not required for the HUD to boot, but
        # we attempt a repair so live voice can work on supported machines.
        install_voice_stack()

    hud_script = REPO_ROOT / "jarvis_hud.py"
    if not hud_script.exists():
        log(f"HUD script not found: {hud_script}", "ERROR")
        return

    launcher = sys.executable
    if os.name == "nt":
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if pythonw.exists():
            launcher = str(pythonw)

    log(f"Launching GUI process: {launcher}", "INIT")
    subprocess.Popen(
        [launcher, str(hud_script)],
        cwd=str(REPO_ROOT),
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0) if os.name == "nt" else 0,
    )


def main() -> None:
    """Start the HUD and its native control panel."""
    log("JARVIS V4.0 LOCAL DESKTOP LAUNCHER", "INFO")
    log("Tkinter HUD + native control surface", "INFO")
    try:
        start_hud()
    except KeyboardInterrupt:
        log("Shutdown signal received", "WARN")
    finally:
        log("JARVIS system offline", "SUCCESS")


if __name__ == "__main__":
    main()
