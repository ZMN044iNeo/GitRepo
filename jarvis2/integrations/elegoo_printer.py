import requests
from core.config import HA_URL, HA_TOKEN


def _headers():
    return {"Authorization": f"Bearer {HA_TOKEN}"}


def get_printer_status() -> dict:
    resp = requests.get(
        f"{HA_URL}/api/states/sensor.elegoo_printer",
        headers=_headers(),
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()


def register(jarvis):
    jarvis.register_tool("printer status", lambda **_: get_printer_status())
