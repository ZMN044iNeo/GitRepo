import subprocess
from core.config import VPN_INTERFACE


def vpn_on() -> str:
    subprocess.run(["wg-quick", "up", VPN_INTERFACE], check=True)
    return f"VPN {VPN_INTERFACE} enabled."


def vpn_off() -> str:
    subprocess.run(["wg-quick", "down", VPN_INTERFACE], check=True)
    return f"VPN {VPN_INTERFACE} disabled."


def register(jarvis):
    jarvis.register_tool("vpn on",  lambda **_: vpn_on())
    jarvis.register_tool("vpn off", lambda **_: vpn_off())
