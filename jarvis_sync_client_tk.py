import time
import threading
import random
from datetime import datetime
import queue


class JarvisSyncClientTK:
    """
    Local event-bus style sync client for JarvisHUD.
    No sockets, just in-process events.
    """

    def __init__(self, hud):
        self.hud = hud
        self.running = False
        self.event_log = []
        self.heartbeat_interval = 5
        self.dispatch_queue = queue.Queue()

        # Start background threads
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        threading.Thread(target=self._dispatch_loop, daemon=True).start()

    # ============================================================
    # ARC-ID GENERATOR
    # ============================================================
    def generate_arc_id(self):
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d-%H:%M:%S")
        tail = random.randint(1000, 9999)
        return f"ARC-{timestamp}-{tail}"

    # ============================================================
    # PACKET BUILDER
    # ============================================================
    def build_packet(self, event_name, payload):
        return {
            "packet_id": self.generate_arc_id(),
            "timestamp": int(time.time()),
            "source": "sync_client",
            "event": event_name,
            "payload": payload
        }

    # ============================================================
    # PUBLIC SEND API
    # ============================================================
    def send_sync(self, packet_dict):
        packet = self.build_packet(
            packet_dict["type"],
            packet_dict.get("payload", packet_dict.get("value"))
        )
        self.event_log.append(packet)
        self.dispatch_queue.put(packet)

    # ============================================================
    # DISPATCH LOOP (THREAD-SAFE)
    # ============================================================
    def _dispatch_loop(self):
        while True:
            packet = self.dispatch_queue.get()
            # Route via HUD's Tk-safe callback
            self.hud.after(0, self._route_packet_safe, packet)

    # ============================================================
    # ROUTER
    # ============================================================
    def _route_packet_safe(self, packet):
        event = packet["event"]
        payload = packet["payload"]

        if event == "status":
            self.hud.log_chat("sync", f"Status synced: {payload}")
            self.hud.update_status(payload)

        elif event == "matrix_mode":
            self.hud.log_chat("sync", f"Matrix mode synced: {payload}")
            self.hud.set_matrix_mode(payload)

        elif event == "blueprint_overlay":
            self.hud.log_chat("sync", "Blueprint overlay synced.")
            self.hud.start_blueprint_scan()

        elif event == "voice_event":
            self.hud.log_chat("sync", f"Voice synced: {payload}")
            self.hud.start_voice_waveform()

        elif event == "daemon_alert":
            self.hud.log_chat("sync", f"Daemon alert synced: {payload}")
            self.hud.start_daemon_pulse()

        elif event == "preview_update":
            self.hud.log_chat("sync", f"Preview synced: {payload}")
            self.hud.start_sync_beam()

        elif event == "console_log":
            self.hud.log_console(payload)

        elif event == "heartbeat":
            self.hud.log_console("♥ Heartbeat OK")

        elif event == "command":
            self.hud.process_command(payload)

        else:
            self.hud.log_chat("sync", f"Unknown event: {event}")

    # ============================================================
    # HEARTBEAT LOOP
    # ============================================================
    def _heartbeat_loop(self):
        while True:
            if self.running:
                packet = self.build_packet("heartbeat", {"alive": True})
                self.event_log.append(packet)
                self.dispatch_queue.put(packet)
            time.sleep(self.heartbeat_interval)
