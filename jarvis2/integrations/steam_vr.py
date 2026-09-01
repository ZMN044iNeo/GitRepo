import subprocess
from core.config import STEAM_PATH


def launch_steam() -> str:
    subprocess.Popen([STEAM_PATH])
    return "Steam launched."


def launch_vr_game(game_id: str) -> str:
    subprocess.Popen([STEAM_PATH, f"steam://rungameid/{game_id}"])
    return f"Launching VR game {game_id}."


def register(jarvis):
    jarvis.register_tool("steam", lambda **_: launch_steam())
    jarvis.register_tool("vr",    lambda game_id="", **_: launch_vr_game(game_id))
