import os
import subprocess
from jarvis2.core.config import STEAM_PATH


def launch_steam() -> str:
    if not os.path.exists(STEAM_PATH):
        return f"Steam is not installed at {STEAM_PATH}."
    try:
        subprocess.Popen([STEAM_PATH])
        return "Steam launched."
    except Exception:
        return "Steam could not be launched on this machine."


def launch_vr_game(game_id: str) -> str:
    if not os.path.exists(STEAM_PATH):
        return f"Steam is not installed at {STEAM_PATH}."
    try:
        subprocess.Popen([STEAM_PATH, f"steam://rungameid/{game_id}"])
        return f"Launching VR game {game_id}."
    except Exception:
        return f"VR game {game_id} could not be launched on this machine."


def register(jarvis):
    jarvis.register_tool("steam", lambda **_: launch_steam())
    jarvis.register_tool("vr",    lambda game_id="", **_: launch_vr_game(game_id))
