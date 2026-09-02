"""
JARVIS System Launcher
Orchestrates startup of all components: HUD, Sync Server, Hologram Dashboard
"""
import subprocess
import sys
import os
import time
import signal
from pathlib import Path

REPO_ROOT = Path(__file__).parent


def log(msg: str, level="INFO"):
    """Print with timestamp."""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")


def start_sync_server():
    """Start WebSocket sync server in background."""
    log("Starting Sync Server...", "INIT")
    try:
        # Check if websockets is installed
        import websockets
    except ImportError:
        log("websockets module not found. Installing...", "WARN")
        subprocess.run([sys.executable, "-m", "pip", "install", "websockets"], 
                      check=True, capture_output=True)
    
    proc = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "jarvis_sync_server.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    time.sleep(1)
    if proc.poll() is None:
        log("✓ Sync Server running (PID: {})".format(proc.pid), "SUCCESS")
        return proc
    else:
        stderr = proc.stderr.read() if proc.stderr else ""
        log(f"Sync Server failed to start: {stderr}", "ERROR")
        return None


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
    
    # Launch HUD
    hud_script = REPO_ROOT / "jarvis_hud.py"
    if hud_script.exists():
        subprocess.run([sys.executable, str(hud_script)])
    else:
        log(f"HUD script not found: {hud_script}", "ERROR")


def start_hologram(enable=False):
    """Start Hologram Dashboard in background (optional)."""
    if not enable:
        return None
    
    log("Starting Hologram Dashboard...", "INIT")
    try:
        import streamlit
    except ImportError:
        log("Streamlit not found. Installing...", "WARN")
        subprocess.run([sys.executable, "-m", "pip", "install", "streamlit"],
                      check=True, capture_output=True)
    
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", 
         str(REPO_ROOT / "hologram_dashboard.py"), "--logger.level=error"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    time.sleep(2)
    if proc.poll() is None:
        log("✓ Hologram Dashboard running at http://localhost:8501", "SUCCESS")
        return proc
    else:
        log("Hologram Dashboard failed to start", "ERROR")
        return None


def main():
    """Orchestrate full system startup."""
    log("╔════════════════════════════════════════╗", "INFO")
    log("║   JARVIS V4.0 UNIFIED LAUNCHER        ║", "INFO")
    log("║   Tkinter HUD + Sync Server            ║", "INFO")
    log("╚════════════════════════════════════════╝", "INFO")
    
    # Parse args
    enable_hologram = "--hologram" in sys.argv
    if enable_hologram:
        log("Hologram Dashboard ENABLED", "INFO")
    
    # Start components
    sync_proc = start_sync_server()
    hologram_proc = None
    
    if enable_hologram:
        hologram_proc = start_hologram(enable=True)
    
    log("", "INFO")
    log("═" * 50, "INFO")
    
    try:
        # Main loop: HUD runs in foreground
        start_hud()
    except KeyboardInterrupt:
        log("Shutdown signal received", "WARN")
    finally:
        # Cleanup
        log("Shutting down all components...", "WARN")
        
        if sync_proc and sync_proc.poll() is None:
            log("Stopping Sync Server...", "INFO")
            sync_proc.terminate()
            try:
                sync_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                sync_proc.kill()
        
        if hologram_proc and hologram_proc.poll() is None:
            log("Stopping Hologram Dashboard...", "INFO")
            hologram_proc.terminate()
            try:
                hologram_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                hologram_proc.kill()
        
        log("✓ JARVIS system offline", "SUCCESS")
        sys.exit(0)


if __name__ == "__main__":
    main()
