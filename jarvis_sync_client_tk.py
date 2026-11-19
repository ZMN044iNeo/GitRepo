import time
import threading
import random
import queue
from datetime import datetime


class JarvisSyncClientTK:
    """
    Local event-bus style sync client for JarvisHUD.
    No sockets, just in-process events.

    Usage from the HUD (Tk main thread):
        self.sync = JarvisSyncClientTK(self)
        self.sync.start()
        self.sync.start_polling()
    """

    def __init__(self, hud, heartbeat_interval=5, max_log=500):
        self.hud = hud
        self.running = False
        self.event_log = []
        self.max_log = max_log
        self.heartbeat_interval = heartbeat_interval
        self.dispatch_queue = queue.Queue()
        self._polling = False

        # Heartbeat runs in a background thread; it only queues packets.
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    # ============================================================
    # LIFECYCLE
    # ============================================================
    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def start_polling(self):
        """Begin draining the queue. Call from the Tk main thread."""
        if not self._polling:
            self._polling = True
            self._poll()

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

    def _log(self, packet):
        self.event_log.append(packet)
        if len(self.event_log) > self.max_log:
            del self.event_log[: len(self.event_log) - self.max_log]

    # ============================================================
    # PUBLIC SEND API
    # ============================================================
    def send_sync(self, packet_dict):
        """
        Queue an event. Expects {"type": "...", "payload": ...}.
        Safe to call from any thread.
        """
        packet = self.build_packet(
            packet_dict["type"],
            packet_dict.get("payload", packet_dict.get("value"))
        )
        self._log(packet)
        self.dispatch_queue.put(packet)

    # ============================================================
    # POLL LOOP (TK MAIN THREAD ONLY)
    # ============================================================
    def _poll(self):
        try:
            while True:
                packet = self.dispatch_queue.get_nowait()
                self._route_packet(packet)
        except queue.Empty:
            pass
        self.hud.after(50, self._poll)

    # ============================================================
    # ROUTER
    # ============================================================
    def _route_packet(self, packet):
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
    # HEARTBEAT LOOP (BACKGROUND THREAD, QUEUE ONLY)
    # ============================================================
    def _heartbeat_loop(self):
        while True:
            if self.running:
                packet = self.build_packet("heartbeat", {"alive": True})
                self._log(packet)
                self.dispatch_queue.put(packet)
            time.sleep(self.heartbeat_interval)
            
