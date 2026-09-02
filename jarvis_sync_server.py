"""
JARVIS Sync Server — WebSocket-based Event Hub
Broadcasts state changes and commands across all connected clients (HUD, Hologram, etc.)
"""
import asyncio
import subprocess
import json
import websockets
import logging
from datetime import datetime
from typing import Dict, Set

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JarvisSyncServer")

# -----------------------------------------
# CONFIG
# -----------------------------------------
HOST = "localhost"
PORT = 8765

CLIENTS: Set = set()
STATE = {
    "matrix_mode": "DEFAULT",
    "status": "ONLINE",
    "voice_active": False,
    "last_voice": "",
    "blueprint_active": False,
    "daemon_alert": "",
}


# -----------------------------------------
# BROADCAST & ROUTING
# -----------------------------------------
async def broadcast(packet: dict, sender=None):
    """Send a packet to all connected clients except optional sender."""
    message = json.dumps(packet)
    disconnected = set()
    
    for client in CLIENTS:
        if sender is not None and client == sender:
            continue
        try:
            await client.send(message)
        except Exception as e:
            logger.error(f"[BROADCAST ERROR] {e}")
            disconnected.add(client)
    
    # Clean up disconnected clients
    for client in disconnected:
        CLIENTS.discard(client)


def cinematic_ack(cmd: str) -> str:
    """Jarvis-style acknowledgments for commands."""
    cmd = cmd.lower()

    if "compress" in cmd:
        return "Compression underway, Sir."
    if "extract" in cmd:
        return "Extracting audio now."
    if "clean" in cmd:
        return "Cleaning and normalizing the audio."
    if "merge" in cmd:
        return "Merging your clips."
    if "dj prep" in cmd:
        return "Preparing the track for performance."
    if "blueprint" in cmd:
        return "Blueprint overlay engaged."
    if "quantum" in cmd:
        return "Quantum matrix activated."
    if "stealth" in cmd:
        return "Stealth mode engaged."
    if "overclock" in cmd:
        return "Overclock protocols initialized."
    if "voice" in cmd:
        return "Voice command system online."
    if "sync" in cmd:
        return "Sync beam established."
    if "daemon" in cmd:
        return "Daemon pulse initiated."
    
    return "Command acknowledged."


async def handle_client(websocket, path):
    """Handle incoming client connections."""
    CLIENTS.add(websocket)
    client_id = id(websocket)
    logger.info(f"[CLIENT CONNECTED] {client_id} (total: {len(CLIENTS)})")
    
    # Send current state to new client
    init_packet = {
        "type": "state_sync",
        "payload": STATE,
        "timestamp": datetime.now().isoformat()
    }
    await websocket.send(json.dumps(init_packet))

    try:
        async for message in websocket:
            packet = json.loads(message)
            await handle_packet(packet, websocket, client_id)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"[CLIENT ERROR {client_id}] {e}")
    finally:
        CLIENTS.discard(websocket)
        logger.info(f"[CLIENT DISCONNECTED] {client_id} (total: {len(CLIENTS)})")


async def handle_packet(packet: dict, sender, client_id: int):
    """Route and process incoming packets."""
    packet_type = packet.get("type", "unknown")
    
    logger.info(f"[PACKET] type={packet_type} from client {client_id}")

    # ---- State Updates ----
    if packet_type == "matrix_mode":
        mode = packet.get("value", "DEFAULT")
        STATE["matrix_mode"] = mode
        ack = f"Matrix mode set to {mode}."
        await broadcast({
            "type": "matrix_mode",
            "value": mode,
            "ack": ack,
            "timestamp": datetime.now().isoformat()
        }, sender=sender)

    # ---- Voice Events ----
    elif packet_type == "voice_event":
        text = packet.get("value", "")
        STATE["voice_active"] = True
        STATE["last_voice"] = text
        await broadcast({
            "type": "voice_event",
            "value": text,
            "timestamp": datetime.now().isoformat()
        }, sender=sender)

    # ---- Commands ----
    elif packet_type == "command":
        cmd = packet.get("command", "")
        ack = cinematic_ack(cmd)
        STATE["status"] = "EXECUTING"
        await broadcast({
            "type": "command_ack",
            "command": cmd,
            "ack": ack,
            "timestamp": datetime.now().isoformat()
        }, sender=sender)

    # ---- Blueprint Scan ----
    elif packet_type == "blueprint_overlay":
        STATE["blueprint_active"] = True
        payload = packet.get("payload", "")
        await broadcast({
            "type": "blueprint_overlay",
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }, sender=sender)

    # ---- Daemon Alert ----
    elif packet_type == "daemon_alert":
        alert = packet.get("value", "")
        STATE["daemon_alert"] = alert
        await broadcast({
            "type": "daemon_alert",
            "value": alert,
            "timestamp": datetime.now().isoformat()
        }, sender=sender)

    # ---- Status Update ----
    elif packet_type == "status":
        status = packet.get("value", "ONLINE")
        STATE["status"] = status
        await broadcast({
            "type": "status",
            "value": status,
            "timestamp": datetime.now().isoformat()
        }, sender=sender)

    # ---- Heartbeat (silence = no response) ----
    elif packet_type == "heartbeat":
        # Don't broadcast heartbeats, just acknowledge
        await sender.send(json.dumps({
            "type": "heartbeat_ack",
            "timestamp": datetime.now().isoformat()
        }))

    # ---- State Sync Request ----
    elif packet_type == "state_request":
        await sender.send(json.dumps({
            "type": "state_sync",
            "payload": STATE,
            "timestamp": datetime.now().isoformat()
        }))

    else:
        # Unknown packet type — echo back
        await sender.send(json.dumps({
            "type": "ack",
            "message": f"Packet type '{packet_type}' received.",
            "timestamp": datetime.now().isoformat()
        }))


async def main():
    """Start WebSocket server."""
    logger.info(f"[JARVIS SYNC SERVER] Starting on ws://{HOST}:{PORT}")
    async with websockets.serve(handle_client, HOST, PORT):
        logger.info(f"[JARVIS SYNC SERVER] Ready for connections")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
