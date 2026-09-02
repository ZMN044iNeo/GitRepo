"""
JARVIS Hologram Dashboard — Streamlit UI
Real-time telemetry, command palette, and system visualization
Connect to sync server for live updates
"""
import streamlit as st
import asyncio
import json
import websockets
from datetime import datetime

SYNC_HOST = "localhost"
SYNC_PORT = 8765
SYNC_URI = f"ws://{SYNC_HOST}:{SYNC_PORT}"

# Page config
st.set_page_config(
    page_title="JARVIS V4.0 Hologram",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Matrix theme
st.markdown("""
<style>
    :root {
        --primary: #00FFFF;
        --accent: #AA00FF;
        --success: #00FF00;
        --warning: #FFAA00;
        --danger: #FF0000;
    }
    
    .main { background-color: #000000; }
    h1, h2, h3 { color: var(--primary); font-family: 'Courier New', monospace; }
    .stMetric { background-color: #050505; border-left: 3px solid var(--accent); }
    .stButton>button { 
        background-color: var(--accent); 
        color: white;
        border: 1px solid var(--primary);
    }
    .status-online { color: var(--success); }
    .status-offline { color: var(--danger); }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================
if "connected" not in st.session_state:
    st.session_state.connected = False
if "matrix_mode" not in st.session_state:
    st.session_state.matrix_mode = "DEFAULT"
if "status" not in st.session_state:
    st.session_state.status = "BOOTING"
if "voice_active" not in st.session_state:
    st.session_state.voice_active = False
if "last_voice" not in st.session_state:
    st.session_state.last_voice = ""
if "blueprint_active" not in st.session_state:
    st.session_state.blueprint_active = False
if "daemon_alert" not in st.session_state:
    st.session_state.daemon_alert = ""
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True


# ============================================================
# SYNC CLIENT
# ============================================================
async def ws_request(packet: dict, timeout: float = 2.0):
    """Open a short-lived websocket connection and request data."""
    try:
        async with websockets.connect(SYNC_URI) as ws:
            await ws.send(json.dumps(packet))
            response = await asyncio.wait_for(ws.recv(), timeout=timeout)
            return json.loads(response)
    except Exception as e:
        return {"type": "error", "error": str(e)}


def sync_state_once(show_errors: bool = False):
    packet = asyncio.run(ws_request({"type": "state_request"}))
    if packet.get("type") == "error":
        st.session_state.connected = False
        if show_errors:
            st.error(f"Sync error: {packet.get('error')}" )
        return False
    process_sync_packet(packet)
    st.session_state.connected = True
    return True


def send_sync_packet(packet: dict, show_errors: bool = True):
    result = asyncio.run(ws_request(packet))
    if result.get("type") == "error":
        st.session_state.connected = False
        if show_errors:
            st.error(f"Send failed: {result.get('error')}" )
        return False
    st.session_state.connected = True
    if result.get("type") == "state_sync":
        process_sync_packet(result)
    return True


def process_sync_packet(packet: dict):
    """Update session state based on sync events."""
    ptype = packet.get("type", "unknown")
    
    if ptype == "matrix_mode":
        st.session_state.matrix_mode = packet.get("value", "DEFAULT")
    elif ptype == "status":
        st.session_state.status = packet.get("value", "ONLINE")
    elif ptype == "voice_event":
        st.session_state.last_voice = packet.get("value", "")
        st.session_state.voice_active = True
    elif ptype == "blueprint_overlay":
        st.session_state.blueprint_active = True
    elif ptype == "daemon_alert":
        st.session_state.daemon_alert = packet.get("value", "")
    elif ptype == "state_sync":
        payload = packet.get("payload", {})
        st.session_state.matrix_mode = payload.get("matrix_mode", "DEFAULT")
        st.session_state.status = payload.get("status", "ONLINE")
        st.session_state.voice_active = payload.get("voice_active", False)
        st.session_state.last_voice = payload.get("last_voice", "")
        st.session_state.blueprint_active = payload.get("blueprint_active", False)
        st.session_state.daemon_alert = payload.get("daemon_alert", "")


# ============================================================
# UI LAYOUT
# ============================================================
st.title("[ 🤖 JARVIS V4.0 HOLOGRAM ]")
st.markdown("Real-time system telemetry and command interface")

if st.session_state.auto_refresh and hasattr(st, "autorefresh"):
    st.autorefresh(interval=2000, key="jarvis_auto_refresh")
if st.session_state.auto_refresh:
    sync_state_once(show_errors=False)

# Sidebar: Connection & Settings
with st.sidebar:
    st.header("⚙️ System Control")
    
    # Connection Status
    connection_status = "🟢 ONLINE" if st.session_state.connected else "🔴 OFFLINE"
    st.subheader(f"Status: {connection_status}")
    
    # Server Connection
    if st.button("🔗 Connect to Sync Server"):
        if sync_state_once(show_errors=True):
            st.success(f"Connected to sync server at {SYNC_URI}")
    
    if st.button("🔌 Disconnect"):
        st.session_state.connected = False
        st.warning("Disconnected from sync server.")

    st.session_state.auto_refresh = st.checkbox(
        "Auto refresh telemetry", value=st.session_state.auto_refresh
    )
    if st.button("🔄 Refresh Now"):
        sync_state_once(show_errors=True)
    
    st.divider()
    
    # Quick Commands
    st.subheader("Quick Commands")
    if st.button("🟪 Quantum Mode"):
        send_sync_packet({"type": "matrix_mode", "value": "QUANTUM"})
        st.session_state.matrix_mode = "QUANTUM"
    if st.button("🟩 Stealth Mode"):
        send_sync_packet({"type": "matrix_mode", "value": "STEALTH"})
        st.session_state.matrix_mode = "STEALTH"
    if st.button("🟥 Overclock Mode"):
        send_sync_packet({"type": "matrix_mode", "value": "OVERCLOCK"})
        st.session_state.matrix_mode = "OVERCLOCK"
    if st.button("🔵 Default Mode"):
        send_sync_packet({"type": "matrix_mode", "value": "DEFAULT"})
        st.session_state.matrix_mode = "DEFAULT"


# Main Grid: Telemetry
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🌐 MATRIX MODE", st.session_state.matrix_mode, delta="System Status")
with col2:
    status_color = "🟢" if st.session_state.status == "ONLINE" else "🔴"
    st.metric("⚡ POWER STATE", f"{status_color} {st.session_state.status}")
with col3:
    voice_icon = "🎤" if st.session_state.voice_active else "🔇"
    st.metric("🔊 VOICE STATUS", f"{voice_icon} {'ACTIVE' if st.session_state.voice_active else 'IDLE'}")
with col4:
    blueprint_icon = "📐" if st.session_state.blueprint_active else "⬜"
    st.metric("🔷 BLUEPRINT", f"{blueprint_icon} {'SCANNING' if st.session_state.blueprint_active else 'IDLE'}")

st.divider()

# Main Content Area
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Telemetry", "🎤 Voice Log", "⚡ Daemon", "🛠️ Tools"]
)

# TAB 1: Telemetry
with tab1:
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        st.subheader("System Telemetry")
        telemetry = {
            "Matrix Mode": st.session_state.matrix_mode,
            "Power State": st.session_state.status,
            "Voice Active": st.session_state.voice_active,
            "Blueprint Scan": st.session_state.blueprint_active,
            "Last Update": datetime.now().strftime("%H:%M:%S")
        }
        st.json(telemetry)
    
    with col_b:
        st.subheader("Mode Colors")
        mode_colors = {
            "DEFAULT": "#00FFFF",
            "QUANTUM": "#AA00FF",
            "STEALTH": "#888888",
            "OVERCLOCK": "#FF0000"
        }
        for mode, color in mode_colors.items():
            indicator = "●" if mode == st.session_state.matrix_mode else "○"
            st.markdown(f"{indicator} {mode}: `{color}`")

# TAB 2: Voice Log
with tab2:
    st.subheader("Last Voice Transcription")
    if st.session_state.last_voice:
        st.info(f"**Heard:** {st.session_state.last_voice}")
    else:
        st.info("No recent voice input")
    
    # Voice Command Input (local simulation)
    st.subheader("Test Voice Commands")
    test_commands = [
        "Matrix quantum",
        "Scan blueprint",
        "Pulse daemon",
        "Voice on",
        "Compress video",
    ]
    for cmd in test_commands:
        if st.button(f"→ {cmd}"):
            st.session_state.last_voice = cmd
            send_sync_packet({"type": "voice_event", "value": cmd}, show_errors=False)
            st.success(f"Command: {cmd}")

# TAB 3: Daemon Alerts
with tab3:
    st.subheader("System Alerts")
    if st.session_state.daemon_alert:
        st.warning(f"⚠️ {st.session_state.daemon_alert}")
    else:
        st.success("✅ No active alerts")
    
    # Daemon Actions
    if st.button("▶️ Pulse Daemon"):
        st.session_state.daemon_alert = "Daemon pulse initiated"
        send_sync_packet({"type": "daemon_alert", "value": st.session_state.daemon_alert}, show_errors=False)
    if st.button("⏹️ Calm Daemon"):
        st.session_state.daemon_alert = ""
        send_sync_packet({"type": "daemon_alert", "value": ""}, show_errors=False)

# TAB 4: Tools & Integrations
with tab4:
    st.subheader("Integration Tools")
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.subheader("🌐 Network")
        if st.button("📱 Telegram"):
            st.info("Telegram integration ready")
        if st.button("🔐 VPN Control"):
            st.info("VPN ready (vpn on/off)")
    
    with col_t2:
        st.subheader("🎮 Hardware")
        if st.button("🖨️ 3D Printer"):
            st.info("Printer status: idle")
        if st.button("🎮 Steam/VR"):
            st.info("Steam library loaded")
    
    st.subheader("🎬 Media Processing")
    media_tools = [
        ("🎥 Compress", "Reduce video file size"),
        ("🔊 Extract", "Pull audio from video"),
        ("🧹 Clean", "Normalize audio"),
        ("🎵 DJ Prep", "Prepare track for mixing"),
    ]
    for tool, desc in media_tools:
        st.markdown(f"- **{tool}**: {desc}")

# Footer
st.divider()
st.markdown(
    "<small style='color: #888888;'>JARVIS V4.0 Hologram Dashboard | Sync Server: "
    f"{'Connected' if st.session_state.connected else 'Disconnected'} | "
    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>",
    unsafe_allow_html=True
)
