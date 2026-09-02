"""JARVIS local desktop launcher."""
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent


def log(msg: str, level="INFO"):
    """Print with timestamp."""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")


def start_hud():
    """Start HUD in foreground (this blocks)."""
    log("Starting JARVIS HUD V4.0...", "INIT")
    try:
        # Check dependencies
        import whisper
        import sounddevice
        import numpy
    except ImportError as e:
        log(f"Missing dependency: {e}. Installing...", "WARN")
        subprocess.run([sys.executable, "-m", "pip", "install", 
                       "openai-whisper", "sounddevice", "numpy"],
                      check=True, capture_output=True)
    
    hud_script = REPO_ROOT / "jarvis_hud.py"
    if hud_script.exists():
        subprocess.run([sys.executable, str(hud_script)])
    else:
        log(f"HUD script not found: {hud_script}", "ERROR")


def main():
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
