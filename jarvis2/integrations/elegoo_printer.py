import requests
from jarvis2.core.config import HA_URL, HA_TOKEN


def _headers():
    return {"Authorization": f"Bearer {HA_TOKEN}"}


def get_printer_status() -> dict:
    try:
        resp = requests.get(
            f"{HA_URL}/api/states/sensor.elegoo_printer",
            headers=_headers(),
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {
            "status": "offline",
            "message": "Elego printer integration is unavailable on this machine.",
            "host": HA_URL,
        }


def register(jarvis):
    jarvis.register_tool("printer status", lambda **_: get_printer_status())
