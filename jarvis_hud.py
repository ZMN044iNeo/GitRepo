import tkinter as tk
import queue
import threading
import math
import re
import importlib
import base64
import subprocess
import sys
from pathlib import Path

# Optional runtime dependencies: the HUD must still boot in a local-safe mode
# if the voice stack is unavailable on this machine.
try:
    import sounddevice as sd
except Exception:
    sd = None

try:
    import numpy as np
except Exception:
    np = None

try:
    import whisper
except Exception:
    whisper = None

from jarvis_sync_client_tk import JarvisSyncClientTK
from jarvis_control_panel import JarvisControlPanel
from jarvis_coding_assistant import JarvisCodingAssistant

# Try to load router; fallback to local-only mode if jarvis2 not available
try:
    from jarvis2.core.router import JarvisRouter
    ROUTER_AVAILABLE = True
    ROUTER_IMPORT_ERROR = ""
except Exception as exc:
    ROUTER_AVAILABLE = False
    JarvisRouter = None
    ROUTER_IMPORT_ERROR = str(exc)


# Silence gate: frames with RMS below this value are skipped
VOICE_SILENCE_THRESHOLD = 0.01

# Wake word configuration
WAKE_WORD = "jarvis"


class JarvisHUD(tk.Tk):
    def __init__(self):
        super().__init__()

        # ============================
        # WINDOW
        # ============================
        self.title("JARVIS HUD V4.0")
        self.geometry("1600x900")
        self.minsize(1200, 760)
        self.configure(bg="#020b12")
        self.attributes("-alpha", 1.0)
        self.fullscreen_mode = False
        self.bind("<F11>", lambda event=None: self.toggle_fullscreen())
        self.bind("<Escape>", lambda event=None: self.exit_fullscreen())

        # The HUD should behave as a solid desktop shell, not a translucent
        # window that reveals the underlying desktop through the background.

        # ============================================================
        # HUD STATE / STATUS SYNC (Fixes control panel crash)
        # ============================================================
        # Core HUD status (Control Panel reads this)
        self.current_status = "BOOTING"

        # HUD mode flags
        self.matrix_mode       = "DEFAULT"
        self.voice_enabled     = False
        self.sync_enabled      = False
        self.premium_enabled   = False

        # Message queue for thread-safe logging
        self.msg_queue         = queue.Queue()

        # ============================================================
        # ANIMATION FLAGS + PHASES (Unified Master Loop)
        # ============================================================
        # Animation flags
        self.particle_running      = True
        self.waveform_running      = True
        self.daemon_running        = True
        self.blueprint_scanning    = True
        self.grid_pulse_running    = True
        self.premium_running       = True

        # Animation phases
        self.particle_phase        = 0
        self.waveform_phase        = 0  # Master phase for holographic matrix
        self.daemon_phase          = 0
        self.blueprint_phase       = 0
        self.grid_pulse_phase      = 0
        self.premium_phase         = 0

        # Voice state
        self.voice_running = False
        self.voice_model   = None
        self.voice_loading = False
        self.voice_requested = False
        self.voice_output_enabled = True
        self.audio_level = 0.5  # Idle hologram pulse even without voice
        self.coding_assistant = JarvisCodingAssistant(Path(__file__).parent)

        # Cinematic state
        self.core_running = False
        self.core_phase = 0
        self.daemon_stop_job = None
        self.upgrade_running = False
        self.cinematic_active = False

        # ============================
        # ROUTER (modular command system)
        # ============================
        self.router, self._router_tools, self._router_init_status = self._init_router()

        # ============================
        # SYNC CLIENT
        # ============================
        self.sync = JarvisSyncClientTK(self)

        # ============================
        # BUILD UI
        # ============================
        self._build_ui()

        # Ensure the optional voice stack is available after the UI is ready.
        self.ensure_voice_dependencies()

        self.control_panel = JarvisControlPanel(self)
        self.control_panel.place_forget()

        # ============================
        # SCHEDULE STARTUP
        # ============================
        self.after(100, self.cinematic_boot)
        self.after(500, self._sync_ready)
        self.after(100, self._poll_queue)
        self.after(200, self._show_in_foreground)
        self.after(16, self.animation_loop)  # Start master animation loop (~60 FPS)

    def _show_in_foreground(self):
        """Ensure a windowless shortcut launch is visible to the user."""
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(150, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def auto_run_animations(self):
        """Enable all animation engines simultaneously."""
        self.particle_running      = True
        self.waveform_running      = True
        self.blueprint_scanning    = True
        self.daemon_running        = True
        self.grid_pulse_running    = True
        self.premium_running       = True

    # ============================================================
    # MASTER ANIMATION LOOP (60 FPS unified renderer)
    # ============================================================
    def animation_loop(self):
        """Unified animation loop that updates ONLY what is active."""

        # HOLOGRAPHIC MATRIX (always running)
        self.waveform_phase += 1
        self.animate_matrix_holographic()

        # PARTICLES
        if self.particle_running:
            self.particle_phase += 1
            self.animate_particles()

        # WAVEFORM
        if self.waveform_running:
            self.animate_waveform()

        # DAEMON TERMINAL PULSE
        if self.daemon_running:
            self.daemon_phase += 1
            self.animate_daemon_pulse()

        # BLUEPRINT SCAN
        if self.blueprint_scanning:
            self.blueprint_phase += 1
            self.animate_blueprint_scan()

        # GRID PULSE
        if self.grid_pulse_running:
            self.grid_pulse_phase += 1
            self.animate_grid_pulse()

        # PREMIUM MODE
        if self.premium_running:
            self.premium_phase += 1
            self.animate_premium()

        # LOOP AGAIN (~60 FPS)
        self.after(16, self.animation_loop)

    def _voice_reactivity(self):
        if not self.voice_running:
            return
        level = min(max(self.audio_level, 0.0), 1.0)
        self.main_canvas.delete("voice_reactive")
        cx, cy = 640, 150
        glow = 60 + int(level * 120)
        self.main_canvas.create_oval(
            cx - glow, cy - glow, cx + glow, cy + glow,
            outline="#66f7ff", width=2, tags="voice_reactive", stipple="gray50"
        )
        self.main_canvas.create_oval(
            cx - 30 - int(level * 30), cy - 30 - int(level * 30),
            cx + 30 + int(level * 30), cy + 30 + int(level * 30),
            outline="#b7f7ff", width=3, tags="voice_reactive"
        )
        # Unified voice-reactive animation suite
        self.animate_matrix_unified()
        self.animate_particles()
        self.animate_waveform()
        self.animate_blueprint_scan()
        self.animate_daemon_pulse()
        self.animate_grid_pulse()
        self.animate_premium()
        self.after(60, self._voice_reactivity)

    # ============================================================
    # UI CONSTRUCTION
    # ============================================================
    def _build_ui(self):
        self.lbl_telemetry_1 = tk.Label(
            self,
            text="[ 🌐 4D MATRIX: DEFAULT ]",
            fg="#00FFFF",
            bg="#020b12",
            font=("Consolas", 16),
        )
        self.lbl_telemetry_1.pack(pady=4)

        self.lbl_status = tk.Label(
            self,
            text="● BOOTING",
            fg="#FFAA00",
            bg="#020b12",
            font=("Consolas", 16),
        )
        self.lbl_status.pack(pady=2)

        self.corner_menu = tk.Menubutton(
            self,
            text="▣ FUNCTIONS",
            relief="raised",
            bg="#0a1620",
            fg="#7ff9ff",
            activebackground="#142a35",
            activeforeground="#ffffff",
            borderwidth=1,
            highlightthickness=1,
            padx=12,
            pady=6,
            font=("Consolas", 10, "bold"),
        )
        self.corner_menu.place(relx=1.0, rely=0.0, anchor="ne", x=-18, y=16)

        self.corner_menu.menu = tk.Menu(self.corner_menu, tearoff=0, bg="#0b1218", fg="#b9f7ff", bd=1)
        self.corner_menu["menu"] = self.corner_menu.menu
        self._build_corner_menu()

        # ---- canvases ----
        self.main_canvas = tk.Canvas(
            self, width=1280, height=300, bg="#000000", highlightthickness=0
        )
        self.main_canvas.pack(fill="x")
        self.main_canvas.configure(highlightthickness=0)

        self.blueprint_canvas = tk.Canvas(
            self.main_canvas, width=800, height=200, bg="#000000", highlightthickness=0
        )
        self.blueprint_canvas.place(x=240, y=40)

        self.particle_canvas = tk.Canvas(
            self.main_canvas, width=240, height=200, bg="#000000", highlightthickness=0
        )
        self.particle_canvas.place(x=10, y=40)
        self.particle_canvas.place_forget()  # Hide unused canvas

        self.sync_beam_canvas = tk.Canvas(
            self.main_canvas, width=800, height=40, bg="#000000", highlightthickness=0
        )
        self.sync_beam_canvas.place(x=240, y=10)

        self.waveform_canvas = tk.Canvas(
            self.main_canvas, width=240, height=80, bg="#000000", highlightthickness=0
        )
        self.waveform_canvas.place(x=10, y=250)

        # ---- chat & console (read-only Text widgets) ----
        self.chat_box = tk.Text(
            self,
            fg="#00FF00",
            bg="#000000",
            font=("Consolas", 10),
            height=8,
            state="disabled",
            insertbackground="#00FF00",
        )
        self.chat_box.pack(fill="x", padx=10, pady=(0, 3))

        self.console_box = tk.Text(
            self,
            fg="#00FFFF",
            bg="#050505",
            font=("Consolas", 9),
            height=4,
            state="disabled",
        )
        self.console_box.pack(fill="x", padx=10, pady=(0, 3))

        # ---- command entry ----
        self.cmd_entry = tk.Entry(
            self, fg="#00FFFF", bg="#000000", font=("Consolas", 12)
        )
        self.cmd_entry.pack(fill="x", padx=10, pady=(0, 8))
        self.cmd_entry.bind("<Return>", lambda _e: self._on_cmd_enter())
        self.cmd_entry.focus_set()

    def _build_corner_menu(self):
        menu = self.corner_menu.menu
        menu.add_command(label="System Status", command=lambda: self.process_command("jarvis status", original="jarvis status"))
        menu.add_command(label="Matrix: Default", command=lambda: self.process_command("jarvis matrix default", original="jarvis matrix default"))
        menu.add_command(label="Matrix: Quantum", command=lambda: self.process_command("jarvis matrix quantum", original="jarvis matrix quantum"))
        menu.add_command(label="Matrix: Stealth", command=lambda: self.process_command("jarvis matrix stealth", original="jarvis matrix stealth"))
        menu.add_command(label="Matrix: Overclock", command=lambda: self.process_command("jarvis matrix overclock", original="jarvis matrix overclock"))
        menu.add_separator()
        menu.add_command(label="Voice: On", command=lambda: self.process_command("jarvis voice on", original="jarvis voice on"))
        menu.add_command(label="Voice: Off", command=lambda: self.process_command("jarvis voice off", original="jarvis voice off"))
        menu.add_command(label="Voice Test", command=lambda: self.process_command("jarvis voice test", original="jarvis voice test"))
        menu.add_separator()
        menu.add_command(label="Blueprint Scan", command=lambda: self.process_command("jarvis scan blueprint", original="jarvis scan blueprint"))
        menu.add_command(label="Daemon Pulse", command=lambda: self.process_command("jarvis pulse daemon", original="jarvis pulse daemon"))
        menu.add_command(label="Cinematic Replay", command=lambda: self.process_command("jarvis cinematic replay", original="jarvis cinematic replay"))
        menu.add_command(label="Combined Mode", command=lambda: self.process_command("jarvis combined mode", original="jarvis combined mode"))
        menu.add_separator()
        menu.add_command(label="Self Debug", command=lambda: self.process_command("jarvis self debug", original="jarvis self debug"))
        menu.add_command(label="Toggle Fullscreen", command=self.toggle_fullscreen)
        menu.add_command(label="Toggle Control Panel", command=self.toggle_control_panel)

    def toggle_control_panel(self):
        if self.control_panel.winfo_exists() and self.control_panel.winfo_ismapped():
            self.control_panel.place_forget()
        else:
            self.control_panel.place(x=18, y=68, width=320, height=620)
            self.control_panel.tkraise()
            self.control_panel.focus_set()

    def toggle_fullscreen(self, event=None):
        try:
            self.fullscreen_mode = not self.fullscreen_mode
            if self.fullscreen_mode:
                self.attributes("-fullscreen", True)
                self.log_chat("system", "Fullscreen mode enabled.")
            else:
                self.attributes("-fullscreen", False)
                self.geometry("1280x720")
                self.log_chat("system", "Fullscreen mode disabled.")
        except Exception as exc:
            self.log_chat("error", f"Fullscreen toggle failed: {exc}")
            try:
                self.state("zoomed")
            except Exception:
                self.geometry("1280x720")

    def exit_fullscreen(self, event=None):
        if self.fullscreen_mode:
            self.toggle_fullscreen()

    def _init_router(self):
        if not ROUTER_AVAILABLE:
            reason = ROUTER_IMPORT_ERROR or "jarvis2 router import failed"
            return None, [], f"offline ({reason})"

        try:
            router = JarvisRouter()
        except Exception as exc:
            return None, [], f"offline (router init failed: {exc})"

        loaded = []
        failed = []
        integration_modules = [
            "jarvis2.integrations.browser_duckduckgo",
            "jarvis2.integrations.elegoo_printer",
            "jarvis2.integrations.vpn_control",
            "jarvis2.integrations.steam_vr",
        ]

        for module_name in integration_modules:
            try:
                mod = importlib.import_module(module_name)
                register = getattr(mod, "register", None)
                if callable(register):
                    register(router)
                    loaded.append(module_name.split(".")[-1])
                else:
                    failed.append(f"{module_name}: missing register()")
            except Exception:
                # Optional integrations should never break the base HUD.
                # Keep them silent unless they are explicitly invoked.
                continue

        if loaded:
            status = f"ready ({len(loaded)} integrations)"
            if failed:
                status += f", {len(failed)} failed"
            return router, loaded, status

        return None, [], "offline (no integrations loaded)"

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
        (r"install|upgrade|patch", lambda: "Upgrade pipeline ready. Use: jarvis install upgrades"),
        (r"showcase|premium|cinematic", lambda: "Premium showcase is live. Use: jarvis premium showcase"),
        (r"debug|diagnostic|self check|self debug", lambda: "Self-diagnostic started. Use: jarvis self debug"),
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
    def ensure_voice_dependencies(self):
        """Attempt to repair the optional local voice stack without breaking startup."""
        global sd, np, whisper

        missing = []
        for module_name, module_obj in (("numpy", np), ("sounddevice", sd), ("whisper", whisper)):
            if module_obj is None:
                missing.append(module_name)

        if not missing:
            return

        package_map = {
            "numpy": "numpy",
            "sounddevice": "sounddevice",
            "whisper": "openai-whisper",
        }
        install_targets = [package_map[name] for name in missing if name in package_map]
        if not install_targets:
            return

        try:
            if hasattr(self, "chat_box"):
                self.log_chat("system", f"Missing voice modules: {', '.join(missing)}. Installing local voice stack...")
            else:
                print(f"[SYSTEM] Missing voice modules: {', '.join(missing)}. Installing local voice stack...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", *install_targets],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            if hasattr(self, "chat_box"):
                self.log_chat("warning", f"Voice dependency install failed: {exc}")
            else:
                print(f"[WARNING] Voice dependency install failed: {exc}")
            return

        for module_name in ("numpy", "sounddevice", "whisper"):
            try:
                if module_name == "numpy":
                    import numpy as np_new
                    np = np_new
                elif module_name == "sounddevice":
                    import sounddevice as sd_new
                    sd = sd_new
                elif module_name == "whisper":
                    import whisper as whisper_new
                    whisper = whisper_new
            except Exception:
                pass

        if any(v is None for v in (sd, whisper, np)):
            if hasattr(self, "chat_box"):
                self.log_chat("warning", "Voice stack remains unavailable; running in degraded local-only mode.")
            else:
                print("[WARNING] Voice stack remains unavailable; running in degraded local-only mode.")

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
        """Map natural language to a canonical command string.
        
        First checks for wake-word ("jarvis"), then applies intent classification.
        Returns structured command string for process_command().
        """
        t = text.lower().strip()

        # Wake-word detection: extract remainder after "jarvis"
        if WAKE_WORD in t:
            cleaned = t.replace(WAKE_WORD, "").strip()
            if cleaned:
                # Recurse on cleaned text to classify intent
                return self.ai_interpret(cleaned)
            else:
                # Just "jarvis" → acknowledge
                return "ask:yes jarvis"

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
        if "daemon" in t or "pulse" in t:
            return "jarvis pulse daemon"
        if "cinematic" in t or "replay boot" in t:
            return "jarvis cinematic replay"
        if "premium" in t or "showcase" in t or "movie" in t:
            return "jarvis premium showcase"
        if "combined" in t or "all systems" in t or "full power" in t:
            return "jarvis combined mode"
        if "debug" in t or "diagnostic" in t or "self check" in t:
            return "jarvis self debug"
        if ("install" in t or "upgrade" in t) and ("jarvis" in t or "system" in t or "patch" in t or "feature" in t):
            return "jarvis install upgrades"

        # ---- voice ----
        if "voice output" in t or "speech output" in t or "speaker" in t:
            if "off" in t or "disable" in t:
                return "jarvis voice output off"
            if "test" in t:
                return "jarvis voice test"
            return "jarvis voice output on"
        if ("voice" in t or "microphone" in t or "listen" in t) and ("stop" in t or "off" in t or "disable" in t):
            return "jarvis voice off"
        if "voice" in t or "microphone" in t or "listen" in t:
            return "jarvis voice on"

        # ---- ffmpeg / media  (from whisper_bridge classify_intent) ----
        if "make this video smaller" in t or "compress" in t or "encode" in t:
            return "jarvis ffmpeg compress"
        if "pull the audio" in t or "extract audio" in t or "extract" in t:
            return "jarvis ffmpeg extract"
        if "clean this up" in t or "fix the audio" in t or "normalize" in t:
            return "jarvis ffmpeg clean"
        if "prep this track" in t or "dj prep" in t or "prep track" in t:
            return "jarvis dj prep"
        if "dj setup" in t or "show me the dj setup" in t or "dj blueprint" in t:
            return "jarvis blueprint dj"

        # ---- local coding assistant ----
        if t in ("code status", "coding status", "project status"):
            return "code:status"
        if t in ("check code", "validate code", "check python"):
            return "code:validate"
        if t in ("list code", "list python files"):
            return "code:list"
        if t.startswith("code find "):
            return f"code:search:{text[10:].strip()}"
        if t.startswith("code read "):
            return f"code:read:{text[10:].strip()}"

        # ---- network / integrations (if router available) ----
        if t.startswith("search "):
            return f"router:{t}"
        if "telegram" in t or "send message" in t:
            return "ask:Telegram control is available from jarvis2/main.py."
        if "vpn" in t:
            if "on" in t or "enable" in t:
                return "router:vpn on"
            elif "off" in t or "disable" in t:
                return "router:vpn off"
        if "printer" in t or "print" in t or "3d print" in t:
            return "router:printer status"
        if "steam" in t or "game" in t or "vr" in t:
            return "router:steam"
        if "search" in t or "browse" in t or "web" in t:
            return "router:search"

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

        if cmd.startswith("code:"):
            result = self.run_coding_command(cmd)
            self.log_chat("code", result.replace("\n", " | ")[:600])
            return

        # ---- Router commands (if available) ----
        if cmd.startswith("router:"):
            if self.router:
                try:
                    router_cmd = cmd[7:].strip()
                    result = self.router.handle_command(router_cmd)
                    self.log_chat("jarvis", str(result))
                    return
                except Exception as e:
                    self.log_chat("error", f"Router error: {e}")
                    return
            else:
                self.log_chat("warning", "Router not available (jarvis2 module not found).")
                return

        # Route unknown input to local response engine
        if cmd.startswith("ask:"):
            self._local_respond(cmd[4:].strip() or original)
            return

        if cmd == "jarvis status":
            voice_state = "active" if self.voice_running else "idle"
            router_state = self._router_init_status
            self.log_chat(
                "jarvis",
                f"Status: {self.current_status} | Matrix: {self.matrix_mode} | Voice: {voice_state} | Router: {router_state}",
            )
            return

        if cmd == "jarvis help":
            cmds = (
                "[ MATRIX ] quantum/stealth/overclock/default | scan blueprint | pulse daemon\n"
                "[ VOICE ] voice on/off | listen\n"
                "[ MEDIA ] compress | extract | clean | dj prep | blueprint dj\n"
                "[ SYSTEM ] sync | calm | status | clear | help\n"
                "[ NETWORK ] telegram | vpn on/off | printer | steam | search <query>\n"
                "[ GENERAL ] ask me anything"
            )
            self.log_chat("jarvis", f"Commands:\n{cmds}")
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

        if cmd == "jarvis cinematic replay":
            self.cinematic_view()
            self.log_chat("jarvis", "Cinematic sequence replayed.")
            return

        if cmd == "jarvis premium showcase":
            self.start_premium_showcase()
            self.log_chat("jarvis", "Premium showcase matrix engaged.")
            return

        if cmd == "jarvis combined mode" or cmd == "jarvis all systems":
            self.activate_combined_mode()
            return

        if cmd == "jarvis self debug":
            self.self_debug_status()
            return

        if cmd in ("jarvis install upgrades", "jarvis upgrade install", "jarvis install"):
            self.start_upgrade_pipeline()
            return

        if cmd == "jarvis voice on":
            self.start_voice_commands()
            return

        if cmd == "jarvis voice off":
            self.stop_voice_commands()
            return

        if cmd == "jarvis voice output on":
            self.voice_output_enabled = True
            self.speak("Voice output enabled.")
            self.log_chat("jarvis", "Offline voice output enabled.")
            return

        if cmd == "jarvis voice output off":
            self.voice_output_enabled = False
            self.log_chat("jarvis", "Offline voice output disabled.")
            return

        if cmd == "jarvis voice test":
            self.speak("All systems are operational. Awaiting your directive.")
            self.log_chat("jarvis", "Voice output test sent.")
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

    def run_coding_command(self, command: str) -> str:
        """Run a read-only local coding action and return its result."""
        action, _, value = command.partition(":")
        if action != "code":
            return "Unknown coding action."

        action, _, value = value.partition(":")
        if action == "status":
            return self.coding_assistant.project_status()
        if action == "validate":
            return self.coding_assistant.validate_python()
        if action == "list":
            return self.coding_assistant.list_python_files()
        if action == "search":
            return self.coding_assistant.search(value)
        if action == "read":
            return self.coding_assistant.read_file(value)
        return f"Unknown coding action: {action}"

    def self_debug_status(self):
        """Run a lightweight diagnostic sweep for the local system and UI layers."""
        checks = []
        checks.append(f"voice_stack: {'ready' if sd is not None and whisper is not None and np is not None else 'degraded'}")
        checks.append(f"router: {self._router_init_status}")
        checks.append(f"canvas: {self.main_canvas.winfo_exists()} | waveform: {self.waveform_canvas.winfo_exists()} | matrix: {self.particle_canvas.winfo_exists()}")
        checks.append(f"voice: {'online' if self.voice_running else 'idle'} | audio_level: {self.audio_level:.2f}")
        self.log_chat("system", "SELF-DIAGNOSTIC // " + " | ".join(checks))
        self.speak("Self-diagnostic complete. Systems stable.")

    def start_upgrade_pipeline(self):
        """Attempt local feature upgrades for the optional voice stack and helper modules."""
        if self.upgrade_running:
            self.log_chat("warning", "Upgrade pipeline already in progress.")
            return
        self.upgrade_running = True
        self.log_chat("system", "Launching local upgrade pipeline...")
        threading.Thread(target=self._upgrade_worker, daemon=True).start()

    def _upgrade_worker(self):
        packages = ["numpy", "openai-whisper", "sounddevice"]
        try:
            self.after(0, lambda: self.log_chat("system", f"Installing: {', '.join(packages)}"))
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "install", *packages],
                capture_output=True,
                text=True,
                check=False,
            )
            output = (proc.stdout or "") + (proc.stderr or "")
            if proc.returncode == 0:
                self.after(0, lambda: self.log_chat("jarvis", "Upgrade pipeline complete. Voice stack refreshed."))
                self.after(0, lambda: self.speak("Upgrade pipeline complete. Systems upgraded."))
            else:
                self.after(0, lambda: self.log_chat("error", f"Upgrade pipeline failed: {output[:500]}"))
        except Exception as exc:
            self.after(0, lambda: self.log_chat("error", f"Upgrade pipeline error: {exc}"))
        finally:
            self.after(0, lambda: setattr(self, "upgrade_running", False))

    # ============================================================
    # LOCAL VOICE ENGINE  (Whisper + sounddevice)
    # ============================================================
    def start_voice_commands(self):
        if self.voice_running:
            self.log_chat("jarvis", "Voice already online.")
            return
        if sd is None or whisper is None or np is None:
            self.voice_requested = False
            self.log_chat("warning", "Voice stack unavailable; booting in local-only mode. Install openai-whisper, sounddevice, and numpy for live voice support.")
            return
        self.voice_requested = True
        if self.voice_model is None:
            if not self.voice_loading:
                self.voice_loading = True
                self.log_chat("system", "Loading Whisper model (tiny)...")
                threading.Thread(target=self._load_voice_model, daemon=True).start()
            return

        self._begin_voice_capture()

    def _load_voice_model(self):
        if whisper is None:
            self.after(0, lambda: self._on_voice_model_error(RuntimeError("whisper is not installed")))
            return
        try:
            model = whisper.load_model("tiny")
            self.after(0, lambda: self._on_voice_model_ready(model))
        except Exception as exc:
            self.after(0, lambda: self._on_voice_model_error(exc))

    def _on_voice_model_ready(self, model):
        self.voice_model = model
        self.voice_loading = False
        if self.voice_requested:
            self._begin_voice_capture()

    def _on_voice_model_error(self, exc):
        self.voice_loading = False
        self.voice_requested = False
        self.log_chat("error", f"Whisper load failed: {exc}")

    def _begin_voice_capture(self):
        if sd is None or whisper is None or np is None:
            self.voice_requested = False
            self.log_chat("warning", "Voice capture unavailable on this machine.")
            return
        if self.voice_running or not self.voice_requested or self.voice_model is None:
            return

        self.voice_running = True
        self.start_voice_waveform()
        self._voice_reactivity()
        threading.Thread(target=self._voice_loop, daemon=True).start()
        self.log_chat("jarvis", "Voice command system online.")
        self.speak("Voice command system online.")

    def stop_voice_commands(self):
        self.voice_requested = False
        self.voice_running = False
        self.audio_level = 0.0
        self.main_canvas.delete("voice_reactive")
        self.stop_voice_waveform()
        self.log_chat("jarvis", "Voice command system offline.")

    def speak(self, text: str):
        """Speak through Windows SAPI with a cleaner, Jarvis-like voice profile."""
        if not self.voice_output_enabled or not text:
            return
        threading.Thread(target=self._speak_worker, args=(text,), daemon=True).start()

    def _speak_worker(self, text: str):
        preferred = [
            "Microsoft Zira Desktop",
            "Microsoft David Desktop",
            "Microsoft Mark Desktop",
            "Microsoft Aria Desktop",
            "Microsoft Jenny Desktop",
            "Microsoft Hazel Desktop",
        ]
        voice_choice = preferred[0] if preferred else ""

        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$speaker.Rate = -2; $speaker.Volume = 90; "
            "$speaker.SelectVoice('Microsoft David Desktop'); "
            f"$speaker.Speak({text!r})"
        )
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        try:
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-EncodedCommand", encoded],
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            self.msg_queue.put(("error", f"Voice output error: {exc}"))

    def _voice_loop(self):
        """Continuous voice capture with wake-word detection and intent classification.
        
        - Captures 4-second audio windows at 16kHz
        - Skips silent frames (RMS < threshold)
        - Checks for wake-word "jarvis"
        - Transcribes with Whisper (tiny model)
        - Routes commands through ai_interpret()
        """
        if sd is None or np is None or whisper is None:
            self.after(0, lambda: self.log_chat("warning", "Voice loop skipped: audio stack is unavailable."))
            self.voice_running = False
            return

        sample_rate = 16_000
        duration    = 4  # seconds per capture window
        wake_word_detected = False
        consecutive_silences = 0

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
                self.after(0, lambda level=min(rms * 12, 1.0): self.set_audio_level(level))
                if rms < VOICE_SILENCE_THRESHOLD:
                    consecutive_silences += 1
                    if consecutive_silences > 5:  # Reset after 5 silent windows
                        wake_word_detected = False
                        consecutive_silences = 0
                    continue
                else:
                    consecutive_silences = 0

                # Transcribe audio with Whisper
                result = self.voice_model.transcribe(audio_np, fp16=False)
                text   = result.get("text", "").strip()

                if text:
                    # Log transcription via sync hook
                    self.after(0, lambda t=text: self.on_voice_transcribed(t))
                    
                    # Check for wake-word
                    text_lower = text.lower()
                    if WAKE_WORD in text_lower:
                        wake_word_detected = True
                        # Extract remainder after wake-word
                        cleaned = text_lower.replace(WAKE_WORD, "").strip()
                        if cleaned:
                            # Process the remainder as command
                            cmd = self.ai_interpret(cleaned)
                            self.after(0, lambda c=cmd, t=cleaned: self.process_command(c, original=t))
                        else:
                            # Just "jarvis" → wait for next utterance
                            self.log_chat("jarvis", "Listening…")
                    elif wake_word_detected:
                        # In wake-word mode, process next utterance
                        cmd = self.ai_interpret(text)
                        self.after(0, lambda c=cmd, t=text: self.process_command(c, original=t))
                        wake_word_detected = False  # Reset for next wake-word

            except Exception as exc:
                self.after(0, lambda: self.set_audio_level(0.0))
                self.msg_queue.put(("error", f"Voice error: {exc}"))

    def set_audio_level(self, level: float):
        self.audio_level = max(0.0, min(level, 1.0))

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
    # CINEMATIC BOOT SEQUENCE
    # ============================================================
    def cinematic_boot(self):
        """Primary boot animation sequence."""
        if self.cinematic_active:
            return

        self.cinematic_active = True
        self.current_status = "BOOTING"
        self.lbl_status.config(text="● BOOTING", fg="#FFAA00")

        # Reset phases
        self.core_phase = 0
        self.grid_pulse_phase = 0
        self.blueprint_phase = 0

        # Enable all animation engines
        self.auto_run_animations()

        # Start sequence
        self.after(100, self._cinematic_step_1)

    def _cinematic_step_1(self):
        """Fade-in + sync beam pulse."""
        self.sync_beam_canvas.delete("all")

        # Simple beam pulse
        for i in range(6):
            self.sync_beam_canvas.create_line(
                0, 20, 800, 20,
                fill="#00FFFF",
                width=1 + i,
                stipple="gray50",
                tags="beam"
            )

        self.after(300, self._cinematic_step_2)

    def _cinematic_step_2(self):
        """Blueprint grid reveal."""
        self.blueprint_canvas.delete("all")

        # Draw grid
        for x in range(0, 800, 40):
            self.blueprint_canvas.create_line(
                x, 0, x, 200,
                fill="#0a3a4a",
                width=1,
                tags="grid"
            )
        for y in range(0, 200, 40):
            self.blueprint_canvas.create_line(
                0, y, 800, y,
                fill="#0a3a4a",
                width=1,
                tags="grid"
            )

        self.blueprint_scanning = True
        self.after(400, self._cinematic_step_3)

    def _cinematic_step_3(self):
        """Particle engine activation."""
        self.particle_canvas.place(x=10, y=40)
        self.particle_running = True

        self.after(400, self._cinematic_step_4)

    def _cinematic_step_4(self):
        """Waveform engine activation."""
        self.waveform_running = True

        self.after(400, self._cinematic_step_5)

    def _cinematic_step_5(self):
        """Final sync + ONLINE state."""
        self.current_status = "ONLINE"
        self.lbl_status.config(text="● ONLINE", fg="#00FF00")

        self.blueprint_scanning = False
        self.grid_pulse_running = False

        self.cinematic_active = False
        self.log_chat("jarvis", "HUD online and fully operational.")
        self.control_panel.refresh()

    def animate_sonar_grid(self):
        # This is now handled by animate_particles grid overlay
        # Removed to prevent animation conflict
        pass

    # ============================================================
    # HOLOGRAPHIC CORE
    # ============================================================
    def start_holographic_core(self):
        self.core_running = True
        self.core_phase = 0
        self.animate_holographic_core()

    def animate_holographic_core(self):
        # Core canvas removed from new layout
        # Animation continues but renders nothing
        if not self.core_running:
            return
        self.core_phase += 1
        self.after(40, self.animate_holographic_core)

    # ============================================================
    # HOLOGRAPHIC MATRIX COLOR MODES
    # ============================================================
    def _matrix_colors(self):
        """Return color palette based on current matrix mode."""
        mode = str(self.matrix_mode).lower()

        if mode == "quantum":
            return {
                "ring":    "#00ccff",
                "particle":"#33ddff",
                "bar":     "#00aaff",
                "core":    "#33ffff",
                "inner":   "#00bbff",
                "grid":    "#003344",
                "dust":    "#44ddff",
            }

        if mode == "stealth":
            return {
                "ring":    "#331144",
                "particle":"#552266",
                "bar":     "#442255",
                "core":    "#663377",
                "inner":   "#442255",
                "grid":    "#220022",
                "dust":    "#553366",
            }

        if mode == "overclock":
            return {
                "ring":    "#ff0099",
                "particle":"#ff33cc",
                "bar":     "#ff66cc",
                "core":    "#ffffff",
                "inner":   "#ff33aa",
                "grid":    "#440022",
                "dust":    "#ff55cc",
            }

        # DEFAULT MODE (purple / blue neon)
        return {
            "ring":    "#bb00ff",
            "particle":"#cc33ff",
            "bar":     "#8833ff",
            "core":    "#ff33ff",
            "inner":   "#aa00ff",
            "grid":    "#330044",
            "dust":    "#9933ff",
        }

    # ============================================================
    # HOLOGRAPHIC MATRIX ENGINE — FULL UNIFIED ANIMATION
    # ============================================================
    def animate_matrix_holographic(self):
        """High-density holographic matrix animation with color modes."""
        level = min(max(self.audio_level, 0.0), 1.0)
        colors = self._matrix_colors()

        # Clear previous frame
        self.main_canvas.delete("holo")

        cx, cy = 640, 150

        # ============================================================
        # 1. Concentric Rings (reactive pulse)
        # ============================================================
        base_radius = 60 + int(level * 90)
        for i in range(12):
            r = base_radius + (i * 18)
            self.main_canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline=colors["ring"],
                width=3,
                tags="holo"
            )

        # ============================================================
        # 2. Particle Halo (orbiting particles)
        # ============================================================
        particle_count = 140
        for i in range(particle_count):
            angle = (self.waveform_phase / 14.0) + (i * 0.045)
            radius = base_radius + 180 + int(level * 70)

            px = cx + radius * math.cos(angle)
            py = cy + radius * math.sin(angle)

            self.main_canvas.create_oval(
                px - 2, py - 2, px + 2, py + 2,
                fill=colors["particle"],
                outline="",
                tags="holo"
            )

        # ============================================================
        # 3. Vertical Light Bars (audio spectrum)
        # ============================================================
        bar_x = 240
        bar_y = 40
        bar_width = 10
        bar_spacing = 6
        bar_count = 32

        for i in range(bar_count):
            height = 30 + int(level * 180) + int(math.sin(self.waveform_phase/10 + i)*60)
            x1 = bar_x + i * (bar_width + bar_spacing)
            y1 = bar_y + (200 - height)
            x2 = x1 + bar_width
            y2 = bar_y + 200

            self.main_canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=colors["bar"],
                outline="",
                tags="holo"
            )

        # ============================================================
        # 4. Energy Core (glowing pulse)
        # ============================================================
        pulse = 30 + int(level * 70)

        # Outer core
        self.main_canvas.create_oval(
            cx - pulse, cy - pulse, cx + pulse, cy + pulse,
            outline=colors["core"],
            width=4,
            tags="holo"
        )

        # Inner glow
        self.main_canvas.create_oval(
            cx - pulse//2, cy - pulse//2,
            cx + pulse//2, cy + pulse//2,
            outline=colors["inner"],
            width=3,
            tags="holo"
        )

        # ============================================================
        # 5. Holographic Grid Distortion
        # ============================================================
        for x in range(0, 1280, 60):
            offset = int(math.sin(self.waveform_phase/18 + x/120) * 12 * level)
            self.main_canvas.create_line(
                x, 0 + offset,
                x, 300 - offset,
                fill=colors["grid"],
                width=1,
                tags="holo"
            )

        # ============================================================
        # 6. Floating Holographic Dust
        # ============================================================
        for i in range(40):
            dx = (i * 32 + self.waveform_phase * 2) % 1280
            dy = 40 + int(math.sin(self.waveform_phase/12 + i)*120)
            self.main_canvas.create_oval(
                dx - 2, dy - 2, dx + 2, dy + 2,
                fill=colors["dust"],
                outline="",
                tags="holo"
            )

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
        self.main_canvas.delete("matrix_overlay")

    def start_premium_showcase(self):
        self.particle_running = True
        self.premium_phase = 0
        if not self.main_canvas.find_withtag("matrix_overlay"):
            self.animate_particles()

    def animate_particles(self):
        if not self.particle_running:
            return
        # draw particles here

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
        self.blueprint_canvas.delete("all")

        # Dim engineering grid: background scan layer for 800x200 canvas
        for x in range(0, 800, 30):
            self.blueprint_canvas.create_line(x, 0, x, 200, fill="#123245", width=1)
        for y in range(0, 200, 30):
            self.blueprint_canvas.create_line(0, y, 800, y, fill="#123245", width=1)

        # Simulated STL / G-code scan sweep: soft and technical, not a bright foreground block.
        scan_x = self.blueprint_phase * 3
        self.blueprint_canvas.create_rectangle(scan_x, 0, scan_x + 30, 200, fill="#12e4ff", outline="", stipple="gray50")
        self.blueprint_canvas.create_rectangle(scan_x + 120, 20, scan_x + 150, 180, fill="#0bdfff", outline="", stipple="gray25")

        # Add a subtle silhouette / contour suggestion for 3D object scanning.
        anchor = 120 + 50 * math.sin(self.blueprint_phase / 18.0)
        self.blueprint_canvas.create_oval(anchor - 30, 55, anchor + 30, 145, outline="#00f7ff", width=1)
        self.blueprint_canvas.create_line(anchor, 55, anchor, 145, fill="#00f7ff", width=1)

        self.blueprint_canvas.create_rectangle(20, 20, 780, 180, outline="#0ad8ff", width=1)
        if self.blueprint_phase == 199:
            self.blueprint_scanning = False

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
        for x in range(0, w, 6):
            phase = (self.waveform_phase / 5.0) + (x / 16.0)
            amplitude = 12 + (28 * self.audio_level)
            y = h / 2 + amplitude * math.sin(phase)
            self.waveform_canvas.create_rectangle(
                x, h / 2, x + 4, y,
                fill="#00FFAA", outline=""
            )
            self.waveform_canvas.create_rectangle(
                x, h / 2, x + 4, h / 2 - abs(y - h / 2),
                fill="#00FFAA", outline=""
            )

    # ============================================================
    # DAEMON PULSE
    # ============================================================
    def start_daemon_pulse(self):
        self.daemon_running = True
        self.daemon_phase   = 0
        if self.daemon_stop_job:
            self.after_cancel(self.daemon_stop_job)
        self.daemon_stop_job = self.after(4000, self.stop_daemon_pulse)
        self.animate_daemon_pulse()

    def stop_daemon_pulse(self):
        self.daemon_running = False
        self.daemon_stop_job = None
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

    # ============================================================
    # SYNC BEAM
    # ============================================================
    def start_sync_beam(self):
        self.sync_beam_canvas.delete("all")
        self.sync_beam_canvas.create_rectangle(0, 0, 800, 40, fill="#00FFAA", outline="")
        self.after(500, lambda: self.sync_beam_canvas.delete("all"))

    # ============================================================
    # GRID PULSE OVERLAY
    # ============================================================
    def animate_grid_pulse(self):
        """Render pulsing grid overlay effect."""
        if not self.grid_pulse_running:
            return
        # Placeholder: grid pulse animation
        pass

    # ============================================================
    # PREMIUM MODE ANIMATION
    # ============================================================
    def animate_premium(self):
        """Render premium showcase particle effects."""
        if not self.premium_running:
            return
        # Placeholder: premium animation rendering
        pass

    # ============================================================
    # UNIFIED ADAPTIVE MATRIX ENGINE (Enhanced Full Replacement)
    # ============================================================
    def animate_matrix_unified(self):
        """Unified adaptive matrix animation driven by waveform amplitude."""
        level = min(max(self.audio_level, 0.0), 1.0)

        # Clear previous frame
        self.main_canvas.delete("matrix_unified")

        cx, cy = 640, 150

        # ============================================================
        # 1. Concentric Rings (reactive pulse)
        # ============================================================
        base_radius = 40 + int(level * 80)
        for i in range(10):
            r = base_radius + (i * 20)
            color = f"#{int(120 + level*135):02x}00ff"
            self.main_canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline=color,
                width=2,
                tags="matrix_unified"
            )

        # ============================================================
        # 2. Particle Field (orbiting dots)
        # ============================================================
        particle_count = 100
        for i in range(particle_count):
            angle = (self.waveform_phase / 12.0) + (i * 0.07)
            radius = base_radius + 150 + int(level * 60)
            px = cx + radius * math.cos(angle)
            py = cy + radius * math.sin(angle)
            self.main_canvas.create_oval(
                px - 3, py - 3, px + 3, py + 3,
                fill="#aa00ff",
                outline="",
                tags="matrix_unified"
            )

        # ============================================================
        # 3. Vertical Bars (audio spectrum)
        # ============================================================
        bar_x = 240
        bar_y = 40
        bar_width = 12
        bar_spacing = 8
        bar_count = 28

        for i in range(bar_count):
            height = 20 + int(level * 160) + int(math.sin(self.waveform_phase/8 + i)*50)
            x1 = bar_x + i * (bar_width + bar_spacing)
            y1 = bar_y + (200 - height)
            x2 = x1 + bar_width
            y2 = bar_y + 200

            color = f"#{int(50 + level*205):02x}{int(100 + level*155):02x}ff"
            self.main_canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=color,
                outline="",
                tags="matrix_unified"
            )

        # ============================================================
        # 4. Central Pulse (heartbeat)
        # ============================================================
        pulse = 20 + int(level * 60)
        self.main_canvas.create_oval(
            cx - pulse, cy - pulse, cx + pulse, cy + pulse,
            outline="#ff00ff",
            width=3,
            tags="matrix_unified"
        )

        # ============================================================
        # 5. Matrix Grid Distortion (subtle)
        # ============================================================
        for x in range(0, 1280, 80):
            offset = int(math.sin(self.waveform_phase/15 + x/100) * 10 * level)
            self.main_canvas.create_line(
                x, 0 + offset,
                x, 300 - offset,
                fill="#220033",
                width=1,
                tags="matrix_unified"
            )

    # ============================================================
    # COMBINED MODE — RUN ALL FEATURES TOGETHER
    # ============================================================
    def activate_combined_mode(self):
        """Enable ALL HUD engines simultaneously."""
        self.log_chat("jarvis", "Activating combined mode: all engines online.")

        # Status
        self.current_status = "COMBINED"
        self.lbl_status.config(text="● COMBINED MODE", fg="#00FFFF")

        # Turn on all animation engines
        self.particle_running      = True
        self.waveform_running      = True
        self.blueprint_scanning    = True
        self.daemon_running        = True
        self.grid_pulse_running    = True
        self.premium_running       = True

        # Reset phases for clean sync
        self.particle_phase        = 0
        self.waveform_phase        = 0
        self.daemon_phase          = 0
        self.blueprint_phase       = 0
        self.grid_pulse_phase      = 0
        self.premium_phase         = 0

        # Ensure canvases are visible
        self.particle_canvas.place(x=10, y=40)
        self.waveform_canvas.place(x=10, y=250)
        self.blueprint_canvas.place(x=240, y=40)
        self.sync_beam_canvas.place(x=240, y=10)

        # Lift canvases in correct order
        self.main_canvas.lift()
        self.blueprint_canvas.lift()
        self.particle_canvas.lift()
        self.waveform_canvas.lift()
        self.sync_beam_canvas.lift()

        # Start voice reactivity if voice is active
        if self.voice_running:
            self._voice_reactivity()

        # Log
        self.log_chat("jarvis", "All systems running concurrently.")

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
