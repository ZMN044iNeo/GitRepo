import shutil
import subprocess
from jarvis2.core.config import VPN_INTERFACE


def vpn_on() -> str:
    if shutil.which("wg-quick") is None:
        return f"VPN integration not available: wg-quick is not installed for {VPN_INTERFACE}."
    try:
        subprocess.run(["wg-quick", "up", VPN_INTERFACE], check=True)
        return f"VPN {VPN_INTERFACE} enabled."
    except Exception:
        return f"VPN {VPN_INTERFACE} could not be enabled on this machine."


def vpn_off() -> str:
    if shutil.which("wg-quick") is None:
        return f"VPN integration not available: wg-quick is not installed for {VPN_INTERFACE}."
    try:
        subprocess.run(["wg-quick", "down", VPN_INTERFACE], check=True)
        return f"VPN {VPN_INTERFACE} disabled."
    except Exception:
        return f"VPN {VPN_INTERFACE} could not be disabled on this machine."


def register(jarvis):
    jarvis.register_tool("vpn on",  lambda **_: vpn_on())
    jarvis.register_tool("vpn off", lambda **_: vpn_off())
