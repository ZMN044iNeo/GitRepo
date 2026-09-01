# Central config — override values via environment variables where sensitive
import os

TELEGRAM_TOKEN   = os.getenv("JARVIS_TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
HA_URL           = os.getenv("JARVIS_HA_URL",         "http://homeassistant.local:8123")
HA_TOKEN         = os.getenv("JARVIS_HA_TOKEN",       "YOUR_HA_TOKEN")
VPN_INTERFACE    = os.getenv("JARVIS_VPN_INTERFACE",  "myvpn")
STEAM_PATH       = os.getenv("JARVIS_STEAM_PATH",     "steam")
