import tkinter as tk
import queue
import threading
import math
import re

import sounddevice as sd
import numpy as np
import whisper

from jarvis_sync_client_tk import JarvisSyncClientTK


# Silence gate: frames with RMS below this value are skipped
VOICE_SILENCE_THRESHOLD = 0.01


class JarvisHUD(tk.Tk):
    def __init__(self):
        super().__init__()

        # ============================
        # WINDOW
        # ============================
        self.title("JARVIS HUD V4.0")
        self.geometry("1280x720")
        self.configure(bg="#000000")

        # ============================
        # HUD STATE  (must come before any after() scheduling)
        # ============================
        self.matrix_mode    = "DEFAULT"
        self.current_status = "BOOTING"
        self.msg_queue      = queue.Queue()

        # Animation state
        self.particle_running  = False
        self.waveform_running  = False
        self.daemon_running    = False
        self.blueprint_scanning = False
        self.particle_phase    = 0
        self.waveform_phase    = 0
        self.daemon_phase      = 0
        self.blueprint_phase   = 0

        # Voice state
        self.voice_running = False
        self.voice_model   = None

        # ============================
        # SYNC CLIENT
        # ============================
        self.sync = JarvisSyncClientTK(self)

        # ============================
        # BUILD UI
        # ============================
        self._build_ui()

        # ============================
        # SCHEDULE STARTUP
        # ============================
        self.after(100, self.cinematic_boot)
        self.after(500, self._sync_ready)
        self.after(100, self._poll_queue)

    # ============================================================
    # UI CONSTRUCTION
    # ============================================================
    def _build_ui(self):
        self.lbl_telemetry_1 = tk.Label(
            self,
            text="[ 🌐 4D MATRIX: DEFAULT ]",
            fg="#00FFFF",
            bg="#000000",
            font=("Consolas", 16),
        )
        self.lbl_telemetry_1.pack(pady=10)

        self.lbl_status = tk.Label(
            self,
            text="● BOOTING",
            fg="#FFAA00",
            bg="#000000",
            font=("Consolas", 16),
        )
        self.lbl_status.pack(pady=10)

        # ---- canvases ----
        self.main_canvas = tk.Canvas(
            self, width=1280, height=300, bg="#000000", highlightthickness=0
        )
        self.main_canvas.pack(fill="x")

        self.blueprint_canvas = tk.Canvas(
            self.main_canvas, width=800, height=200, bg="#000000", highlightthickness=0
        )
        self.blueprint_canvas.place(x=240, y=40)

        self.particle_canvas = tk.Canvas(
            self.main_canvas, width=240, height=200, bg="#000000", highlightthickness=0
        )
        self.particle_canvas.place(x=10, y=40)

        self.waveform_canvas = tk.Canvas(
            self.main_canvas, width=240, height=80, bg="#000000", highlightthickness=0
        )
        self.waveform_canvas.place(x=10, y=250)

        self.sync_beam_canvas = tk.Canvas(
            self.main_canvas, width=800, height=40, bg="#000000", highlightthickness=0
        )
        self.sync_beam_canvas.place(x=240, y=10)

        # ---- chat & console (read-only Text widgets) ----
        self.chat_box = tk.Text(
            self,
            fg="#00FF00",
            bg="#000000",
            font=("Consolas", 12),
            height=10,
            state="disabled",
        )
        self.chat_box.pack(fill="x", padx=10, pady=5)

        self.console_box = tk.Text(
            self,
            fg="#00FFFF",
            bg="#050505",
            font=("Consolas", 10),
            height=6,
            state="disabled",
        )
        self.console_box.pack(fill="x", padx=10, pady=5)

        # ---- command entry ----
        self.cmd_entry = tk.Entry(
            self, fg="#00FFFF", bg="#000000", font=("Consolas", 14)
        )
        self.cmd_entry.pack(fill="x", padx=10, pady=5)
        self.cmd_entry.bind("<Return>", lambda _e: self._on_cmd_enter())
        self.cmd_entry.focus_set()

    # ============================================================
    # LOCAL RESPONSE ENGINE  (no network required)
    # ============================================================
    # Ordered list of (regex_pattern, response_template) pairs.
    # {cmd} is substituted with the captured remainder where used.
    _RESPONSES = [
        (r"time",               lambda: f"Current system time: {__import__('datetime').datetime.now().strftime('%H:%M:%S')}"),
        (r"date",               lambda: f"Today is {__import__('datetime').datetime.now().strftime('%A, %B %d %Y')}"),
        (r"hello|hi|hey",       lambda: "Online and standing by, sir."),
        (r"who are you|your name", lambda: "I am JARVIS — Just A Rather Very Intelligent System."),
        (r"what can you do|help", lambda: "I can manage matrix modes, run blueprint scans, pulse the daemon, handle voice input, execute ffmpeg tasks, and respond to your queries locally."),
        (r"thank",              lambda: "Always at your service."),
        (r"shutdown|power off", lambda: "Initiating shutdown sequence."),
        (r"joke",               lambda: "Why do programmers prefer dark mode? Because light attracts bugs."),
        (r"weather",            lambda: "No network access. Weather module offline."),
        (r"ffmpeg|compress|video", lambda: "ffmpeg command ready. Specify input and output files."),
        (r"dj|prep|track",      lambda: "DJ prep sequence standing by. Specify your audio file."),
    ]

    def _local_respond(self, text: str):
        t = text.lower()
        for pattern, fn in self._RESPONSES:
            if re.search(pattern, t):
                self.msg_queue.put(("jarvis", fn()))
                return
        # Generic fallback
        self.msg_queue.put(("jarvis", f"Understood: \"{text}\". No local handler matched. Expand _RESPONSES to add support."))

    # ============================================================
    # SYNC / QUEUE
    # ============================================================
    def _sync_ready(self):
        self.sync.running = True

    def _poll_queue(self):
        while not self.msg_queue.empty():
            msg_type, text = self.msg_queue.get_nowait()
            self.log_chat(msg_type, text)
        self.after(100, self._poll_queue)

    # ============================================================
    # COMMAND SYSTEM
    # ============================================================
    def ai_interpret(self, text: str) -> str:
        """Map natural language to a canonical command string."""
        t = text.lower().strip()

        # Pass through already-structured commands
        if t.startswith("jarvis "):
            return t

        # ---- matrix modes ----
        if "quantum" in t:
            return "jarvis matrix quantum"
        if "stealth" in t:
            return "jarvis matrix stealth"
        if "overclock" in t or "over clock" in t:
            return "jarvis matrix overclock"
        if ("default" in t or "normal" in t) and "matrix" not in t:
            return "jarvis matrix default"

        # ---- visual / animation ----
        if "scan" in t and ("blueprint" in t or "grid" in t):
            return "jarvis scan blueprint"
        if "daemon" in t or ("pulse" in t and "daemon" not in t):
            return "jarvis pulse daemon"

        # ---- voice ----
        if ("voice" in t or "microphone" in t) and ("stop" in t or "off" in t):
            return "jarvis voice off"
        if "voice" in t or "microphone" in t or "listen" in t:
            return "jarvis voice on"

        # ---- ffmpeg / media  (from whisper_bridge classify_intent) ----
        if "make this video smaller" in t or "compress" in t:
            return "jarvis ffmpeg compress"
        if "pull the audio" in t or "extract audio" in t:
            return "jarvis ffmpeg extract"
        if "clean this up" in t or "fix the audio" in t:
            return "jarvis ffmpeg clean"
        if "prep this track" in t or "dj prep" in t:
            return "jarvis dj prep"
        if "dj setup" in t or "show me the dj setup" in t:
            return "jarvis blueprint dj"

        # ---- system ----
        if "sync" in t or "beam" in t:
            return "jarvis sync"
        if "stop" in t or "calm" in t or "halt" in t:
            return "jarvis calm"
        if "status" in t or ("system" in t and "info" in t):
            return "jarvis status"
        if "clear" in t or "reset chat" in t:
            return "jarvis clear"
        if "help" in t:
            return "jarvis help"

        # Unknown → local response engine
        return f"ask:{text}"

    def _on_cmd_enter(self):
        raw = self.cmd_entry.get().strip()
        if not raw:
            return
        self.cmd_entry.delete(0, "end")
        self.log_chat("user", raw)
        self.process_command(self.ai_interpret(raw), original=raw)

    def process_command(self, cmd: str, original: str = ""):
        cmd = cmd.strip().lower()

        # Route unknown input to local response engine
        if cmd.startswith("ask:"):
            self._local_respond(cmd[4:].strip() or original)
            return

        if cmd == "jarvis status":
            voice_state = "active" if self.voice_running else "idle"
            self.log_chat(
                "jarvis",
                f"Status: {self.current_status} | Matrix: {self.matrix_mode} | Voice: {voice_state}",
            )
            return

        if cmd == "jarvis help":
            cmds = (
                "matrix <quantum|stealth|overclock|default> · scan blueprint · "
                "pulse daemon · voice on/off · sync · calm · status · clear · "
                "ffmpeg compress/extract/clean · dj prep · blueprint dj · "
                "or ask me anything"
            )
            self.log_chat("jarvis", f"Commands: {cmds}")
            return

        if cmd == "jarvis clear":
            for box in (self.chat_box, self.console_box):
                box.config(state="normal")
                box.delete("1.0", "end")
                box.config(state="disabled")
            return

        if cmd.startswith("jarvis matrix"):
            parts = cmd.split(None, 2)
            if len(parts) >= 3:
                self.set_matrix_mode(parts[2])
                self.log_chat("jarvis", f"Matrix mode set to {parts[2].upper()}")
            else:
                self.log_chat("jarvis", "Usage: jarvis matrix <mode>")
            return

        if cmd == "jarvis scan blueprint":
            self.start_blueprint_scan()
            self.log_chat("jarvis", "Initiating blueprint scan.")
            return

        if cmd == "jarvis pulse daemon":
            self.start_daemon_pulse()
            self.log_chat("jarvis", "Daemon pulse triggered.")
            return

        if cmd == "jarvis voice on":
            self.start_voice_commands()
            return

        if cmd == "jarvis voice off":
            self.stop_voice_commands()
            return

        if cmd == "jarvis sync":
            self.start_sync_beam()
            self.log_chat("jarvis", "Sync beam activated.")
            return

        if cmd == "jarvis calm":
            self.stop_quantum_particles()
            self.stop_voice_waveform()
            self.stop_daemon_pulse()
            self.log_chat("jarvis", "All animations halted.")
            return

        # ---- ffmpeg / media commands ----
        if cmd == "jarvis ffmpeg compress":
            self.log_chat("jarvis", "ffmpeg -i input.mp4 -vcodec libx264 -crf 28 output.mp4")
            return
        if cmd == "jarvis ffmpeg extract":
            self.log_chat("jarvis", "ffmpeg -i input.mp4 -vn -acodec mp3 output.mp3")
            return
        if cmd == "jarvis ffmpeg clean":
            self.log_chat("jarvis", "ffmpeg -i input.wav -af 'highpass=f=200,lowpass=f=3000' output.wav")
            return
        if cmd == "jarvis dj prep":
            self.log_chat("jarvis", "ffmpeg -i input.mp4 -ar 44100 -ac 2 output.wav")
            return
        if cmd == "jarvis blueprint dj":
            self.start_blueprint_scan()
            self.log_chat("jarvis", "DJ blueprint overlay active.")
            return

        # Fallback — anything unmatched goes to local engine
        self._local_respond(original or cmd)

    # ============================================================
    # LOCAL VOICE ENGINE  (Whisper + sounddevice)
    # ============================================================
    def start_voice_commands(self):
        if self.voice_running:
            self.log_chat("jarvis", "Voice already online.")
            return
        try:
            if self.voice_model is None:
                self.log_chat("system", "Loading Whisper model (tiny)…")
                self.voice_model = whisper.load_model("tiny")
        except Exception as exc:
            self.log_chat("error", f"Whisper load failed: {exc}")
            return

        self.voice_running = True
        self.start_voice_waveform()
        threading.Thread(target=self._voice_loop, daemon=True).start()
        self.log_chat("jarvis", "Voice command system online.")

    def stop_voice_commands(self):
        self.voice_running = False
        self.stop_voice_waveform()
        self.log_chat("jarvis", "Voice command system offline.")

    def _voice_loop(self):
        sample_rate = 16_000
        duration    = 4  # seconds per capture window

        while self.voice_running:
            try:
                audio = sd.rec(
                    int(duration * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                )
                sd.wait()

                audio_np = np.squeeze(audio).astype(np.float32)

                # Skip silent frames — avoids wasting Whisper on noise
                rms = float(np.sqrt(np.mean(audio_np ** 2)))
                if rms < VOICE_SILENCE_THRESHOLD:
                    continue

                result = self.voice_model.transcribe(audio_np, fp16=False)
                text   = result.get("text", "").strip()

                if text:
                    self.after(0, lambda t=text: self.on_voice_transcribed(t))
                    cmd = self.ai_interpret(text)
                    self.after(0, lambda c=cmd, t=text: self.process_command(c, original=t))

            except Exception as exc:
                self.msg_queue.put(("error", f"Voice error: {exc}"))

    # ============================================================
    # STATUS / MATRIX
    # ============================================================
    def update_status(self, status: str):
        self.current_status = status.upper()
        color = "#00FF00" if self.current_status == "ONLINE" else "#FFAA00"
        self.lbl_status.config(text=f"● {self.current_status}", fg=color)

    def set_matrix_mode(self, mode: str):
        self.matrix_mode = mode.upper()
        colors = {
            "QUANTUM":   "#AA00FF",
            "STEALTH":   "#888888",
            "OVERCLOCK": "#FF0000",
        }
        color = colors.get(self.matrix_mode, "#00FFFF")
        self.lbl_telemetry_1.config(
            text=f"[ 🌐 4D MATRIX: {self.matrix_mode} ]", fg=color
        )

    # ============================================================
    # CHAT / CONSOLE  (always called from the main thread)
    # ============================================================
    def log_chat(self, msg_type: str, msg: str):
        self.chat_box.config(state="normal")
        self.chat_box.insert("end", f"[{msg_type.upper()}] {msg}\n")
        self.chat_box.see("end")
        self.chat_box.config(state="disabled")

    def log_console(self, msg: str):
        self.console_box.config(state="normal")
        self.console_box.insert("end", f"{msg}\n")
        self.console_box.see("end")
        self.console_box.config(state="disabled")

    # ============================================================
    # CINEMATIC BOOT
    # ============================================================
    def cinematic_boot(self):
        self.log_chat("system", "JARVIS HUD V4.0 initializing…")
        self.update_status("BOOTING")
        self.set_matrix_mode("DEFAULT")
        self.start_quantum_particles()
        self.cinematic_view()
        self.after(1500, lambda: self.update_status("ONLINE"))

    def cinematic_view(self):
        self.main_canvas.create_rectangle(
            0, 0, 1280, 300, fill="#000000", outline="", tags="cinematic_overlay"
        )

        def fade(step=0):
            if step > 25:
                self.main_canvas.delete("cinematic_overlay")
                self.cinematic_arc_reactor()
                return
            alpha = max(0, 255 - step * 10)
            self.main_canvas.itemconfig(
                "cinematic_overlay", fill=f"#{alpha:02x}{alpha:02x}{alpha:02x}"
            )
            self.after(40, lambda: fade(step + 1))

        fade()

    # ============================================================
    # ARC REACTOR INTRO
    # ============================================================
    def cinematic_arc_reactor(self):
        # centered on main_canvas, not sync_beam_canvas
        cx, cy, base_r = 640, 150, 20

        def pulse(step=0):
            self.main_canvas.delete("arc_reactor")
            r = base_r + step
            self.main_canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline="#00FFFF", width=3, tags="arc_reactor",
            )
            if step < 60:
                self.after(20, lambda: pulse(step + 2))
            else:
                self.main_canvas.delete("arc_reactor")
                self.cinematic_grid()

        pulse()

    # ============================================================
    # BLUEPRINT GRID INTRO
    # ============================================================
    def cinematic_grid(self):
        for x in range(0, 1280, 40):
            self.main_canvas.create_line(x, 0, x, 300, fill="#003344", tags="cinematic_grid")
        for y in range(0, 300, 40):
            self.main_canvas.create_line(0, y, 1280, y, fill="#003344", tags="cinematic_grid")

        self.sync_beam_canvas.create_rectangle(
            0, 0, 800, 40, fill="#00FFFF", outline="", tags="sync_flash"
        )

        def fade_flash(step=0):
            if step > 20:
                self.sync_beam_canvas.delete("sync_flash")
                return
            alpha = max(0, 255 - step * 12)
            self.sync_beam_canvas.itemconfig(
                "sync_flash", fill=f"#{alpha:02x}{alpha:02x}{alpha:02x}"
            )
            self.after(40, lambda: fade_flash(step + 1))

        fade_flash()

    # ============================================================
    # PARTICLE ENGINE
    # ============================================================
    def start_quantum_particles(self):
        self.particle_running = True
        self.particle_phase   = 0
        self.animate_particles()

    def stop_quantum_particles(self):
        self.particle_running = False
        self.particle_canvas.delete("all")

    def animate_particles(self):
        if not self.particle_running:
            return
        self.particle_canvas.delete("all")
        cx, cy = 120, 100
        color = "#AA00FF" if self.matrix_mode == "QUANTUM" else "#00FFFF"
        for i in range(40):
            angle  = (self.particle_phase / 10.0) + (i / 5.0)
            radius = 40 + 20 * math.sin(i / 4.0)
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle * 1.5)
            self.particle_canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color, outline="")
        self.particle_phase += 1
        self.after(40, self.animate_particles)

    # ============================================================
    # BLUEPRINT SCAN
    # ============================================================
    def start_blueprint_scan(self):
        self.blueprint_scanning = True
        self.blueprint_phase    = 0
        self.animate_blueprint_scan()

    def animate_blueprint_scan(self):
        if not self.blueprint_scanning:
            return
        self.blueprint_phase = (self.blueprint_phase + 1) % 200
        self.blueprint_canvas.delete("all")
        for x in range(0, 800, 40):
            self.blueprint_canvas.create_line(x, 0, x, 200, fill="#003344")
        for y in range(0, 200, 40):
            self.blueprint_canvas.create_line(0, y, 800, y, fill="#003344")
        x_pos = self.blueprint_phase * 4
        self.blueprint_canvas.create_rectangle(x_pos, 0, x_pos + 20, 200, fill="#00FFFF", outline="")
        self.blueprint_canvas.create_rectangle(0, 0, 800, 200, outline="#00FFFF")
        if self.blueprint_phase == 199:
            self.blueprint_scanning = False
        self.after(40, self.animate_blueprint_scan)

    # ============================================================
    # VOICE WAVEFORM
    # ============================================================
    def start_voice_waveform(self):
        self.waveform_running = True
        self.waveform_phase   = 0
        self.animate_waveform()

    def stop_voice_waveform(self):
        self.waveform_running = False
        self.waveform_canvas.delete("all")

    def animate_waveform(self):
        if not self.waveform_running:
            return
        self.waveform_canvas.delete("all")
        w, h = 240, 80
        for x in range(0, w, 4):
            phase = (self.waveform_phase / 5.0) + (x / 20.0)
            y = h / 2 + 20 * math.sin(phase)
            self.waveform_canvas.create_line(x, h / 2, x, y, fill="#00FFAA")
        self.waveform_phase += 1
        self.after(40, self.animate_waveform)

    # ============================================================
    # DAEMON PULSE
    # ============================================================
    def start_daemon_pulse(self):
        self.daemon_running = True
        self.daemon_phase   = 0
        self.animate_daemon_pulse()

    def stop_daemon_pulse(self):
        self.daemon_running = False
        self.main_canvas.delete("daemon_pulse")

    def animate_daemon_pulse(self):
        if not self.daemon_running:
            return
        self.main_canvas.delete("daemon_pulse")
        intensity = (math.sin(self.daemon_phase / 5.0) + 1) / 2
        alpha = int(50 + 205 * intensity)
        self.main_canvas.create_rectangle(
            0, 0, 1280, 300, outline="", fill=f"#{alpha:02x}0000", tags="daemon_pulse"
        )
        self.daemon_phase += 1
        self.after(40, self.animate_daemon_pulse)

    # ============================================================
    # SYNC BEAM
    # ============================================================
    def start_sync_beam(self):
        self.sync_beam_canvas.delete("all")
        self.sync_beam_canvas.create_rectangle(0, 0, 800, 40, fill="#00FFAA", outline="")
        self.after(500, lambda: self.sync_beam_canvas.delete("all"))

    # ============================================================
    # SYNC HOOKS  (call these from anywhere to push events to the bus)
    # ============================================================
    def on_voice_transcribed(self, transcript: str):
        self.log_chat("voice", transcript)
        self.sync.send_sync({"type": "voice_event", "value": transcript})

    def push_daemon_alert(self, alert: str):
        self.log_chat("daemon", alert)
        self.sync.send_sync({"type": "daemon_alert", "value": alert})

    def update_preview(self, img_path: str):
        self.sync.send_sync({"type": "preview_update", "path": img_path})

    def render_blueprint_overlay(self, overlay_data):
        self.start_blueprint_scan()
        self.sync.send_sync({"type": "blueprint_overlay", "payload": overlay_data})


# ============================================================
# MAIN ENTRY POINT
# ============================================================
if __name__ == "__main__":
    app = JarvisHUD()
    app.mainloop()
