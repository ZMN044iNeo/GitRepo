import tkinter as tk
import queue
import threading
import math
import re
import importlib
import base64
import subprocess
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
        self.geometry("1280x720")
        self.configure(bg="#020b12")
        self.attributes("-alpha", 0.96)
        try:
            self.attributes("-transparentcolor", "#020b12")
        except Exception:
            pass

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
        self.grid_pulse_phase  = 0
        self.premium_phase     = 0

        # Voice state
        self.voice_running = False
        self.voice_model   = None
        self.voice_loading = False
        self.voice_requested = False
        self.voice_output_enabled = True
        self.audio_level = 0.0
        self.coding_assistant = JarvisCodingAssistant(Path(__file__).parent)

        # Cinematic state
        self.core_running = False
        self.core_phase = 0
        self.daemon_stop_job = None
        self.upgrade_running = False

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
        self.control_panel = JarvisControlPanel(self)

        # ============================
        # SCHEDULE STARTUP
        # ============================
        self.after(100, self.cinematic_boot)
        self.after(500, self._sync_ready)
        self.after(100, self._poll_queue)
        self.after(200, self._show_in_foreground)
        self.after(400, self.control_panel.show_in_foreground)

    def _show_in_foreground(self):
        """Ensure a windowless shortcut launch is visible to the user."""
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(150, lambda: self.attributes("-topmost", False))
        self.focus_force()

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
        self.lbl_telemetry_1.pack(pady=10)

        self.lbl_status = tk.Label(
            self,
            text="● BOOTING",
            fg="#FFAA00",
            bg="#020b12",
            font=("Consolas", 16),
        )
        self.lbl_status.pack(pady=10)

        # ---- canvases ----
        self.main_canvas = tk.Canvas(
            self, width=1280, height=300, bg="#020b12", highlightthickness=0
        )
        self.main_canvas.pack(fill="x")
        self.main_canvas.configure(highlightthickness=0)

        self.blueprint_canvas = tk.Canvas(
            self.main_canvas, width=800, height=200, bg="#020b12", highlightthickness=0
        )
        self.blueprint_canvas.place(x=240, y=40)

        self.core_canvas = tk.Canvas(
            self.main_canvas, width=320, height=200, bg="#020b12", highlightthickness=0
        )
        self.core_canvas.place(x=480, y=40)

        self.particle_canvas = tk.Canvas(
            self.main_canvas, width=240, height=200, bg="#020b12", highlightthickness=0
        )
        self.particle_canvas.place(x=10, y=40)

        self.waveform_canvas = tk.Canvas(
            self.main_canvas, width=240, height=90, bg="#020b12", highlightthickness=0
        )
        self.waveform_canvas.place(x=500, y=210)

        self.sync_beam_canvas = tk.Canvas(
            self.main_canvas, width=800, height=40, bg="#020b12", highlightthickness=0
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
            insertbackground="#00FF00",
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
            self.log_chat("warning", "Voice stack unavailable; booting in local-only mode.")
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
    # CINEMATIC BOOT
    # ============================================================
    def cinematic_boot(self):
        self.log_chat("system", "JARVIS HUD V4.0 initializing…")
        self.log_chat("system", f"Router: {self._router_init_status}")
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
        self.main_canvas.delete("cinematic_grid")
        self.grid_pulse_phase = 0
        for x in range(0, 1280, 40):
            self.main_canvas.create_line(x, 0, x, 300, fill="#0a1a2a", width=1, tags="cinematic_grid")
        for y in range(0, 300, 40):
            self.main_canvas.create_line(0, y, 1280, y, fill="#0a1a2a", width=1, tags="cinematic_grid")

        self.sync_beam_canvas.create_rectangle(
            0, 0, 800, 40, fill="#00FFFF", outline="", tags="sync_flash"
        )

        def fade_flash(step=0):
            if step > 20:
                self.sync_beam_canvas.delete("sync_flash")
                self.start_holographic_core()
                self.animate_sonar_grid()
                return
            alpha = max(0, 255 - step * 12)
            self.sync_beam_canvas.itemconfig(
                "sync_flash", fill=f"#{alpha:02x}{alpha:02x}{alpha:02x}"
            )
            self.after(40, lambda: fade_flash(step + 1))

        fade_flash()

    def animate_sonar_grid(self):
        if not self.particle_running:
            return
        self.grid_pulse_phase = (self.grid_pulse_phase + 1) % 100
        for item in self.main_canvas.find_withtag("cinematic_grid"):
            self.main_canvas.itemconfig(item, fill="#12273a")

        pulse = 0.5 + (math.sin(self.grid_pulse_phase / 8.0) + 1) / 2
        for x in range(0, 1280, 40):
            for y in range(0, 300, 40):
                target = self.main_canvas.find_overlapping(x - 5, y - 5, x + 5, y + 5)
                if not target:
                    continue
                for item in target:
                    if self.main_canvas.gettags(item) and "cinematic_grid" in self.main_canvas.gettags(item):
                        alpha = int(20 + 30 * pulse)
                        self.main_canvas.itemconfig(item, fill=f"#{alpha:02x}{alpha + 15:02x}{alpha + 30:02x}")

        self.after(80, self.animate_sonar_grid)

    # ============================================================
    # HOLOGRAPHIC CORE
    # ============================================================
    def start_holographic_core(self):
        self.core_running = True
        self.core_phase = 0
        self.animate_holographic_core()

    def animate_holographic_core(self):
        if not self.core_running:
            return

        self.core_canvas.delete("all")
        cx, cy = 160, 100
        color = {
            "QUANTUM": "#cc55ff",
            "STEALTH": "#809199",
            "OVERCLOCK": "#ff4d4d",
        }.get(self.matrix_mode, "#00e5ff")
        phase = self.core_phase / 12.0
        pulse = 10 + int(4 * math.sin(phase * 1.5))

        for radius, start, extent in ((74, 20, 135), (58, 190, 115), (42, 70, 150)):
            offset = (self.core_phase * (1 if radius != 58 else -1)) % 360
            self.core_canvas.create_arc(
                cx - radius, cy - radius, cx + radius, cy + radius,
                start=start + offset, extent=extent, style="arc", outline=color, width=2,
            )

        for index in range(8):
            angle = phase + index * math.pi / 4
            radius = 66
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            self.core_canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline="")

        self.core_canvas.create_oval(cx - pulse, cy - pulse, cx + pulse, cy + pulse, outline=color, width=3)
        self.core_canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="#ffffff", outline="")
        self.core_canvas.create_text(cx, 178, text="ARC CORE // ACTIVE", fill=color, font=("Consolas", 10, "bold"))
        self.core_phase += 1
        self.after(40, self.animate_holographic_core)

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

        self.main_canvas.delete("matrix_overlay")
        self.particle_canvas.delete("all")

        cx, cy = 640, 150
        color = "#cc66ff" if self.matrix_mode == "QUANTUM" else "#00e5ff"
        pulse = 0.5 + (math.sin(self.particle_phase / 8.0) + 1) / 2
        self.premium_phase += 1

        for ring in (50, 90, 130, 170, 210):
            r = ring + 12 * math.sin(self.premium_phase / 12.0)
            self.main_canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline=color, width=2, tags="matrix_overlay", stipple="gray50"
            )

        for i in range(60):
            angle = (self.particle_phase / 12.0) + (i / 7.0)
            radius = 70 + 55 * math.sin(i / 4.0 + self.particle_phase / 20.0)
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle * 1.3)
            self.main_canvas.create_oval(
                x - 2, y - 2, x + 2, y + 2,
                fill=color, outline="", tags="matrix_overlay"
            )

        for i in range(16):
            angle = (self.particle_phase / 6.0) + (i * math.pi / 8)
            x = cx + 200 * math.cos(angle)
            y = cy + 100 * math.sin(angle)
            self.main_canvas.create_line(
                cx, cy, x, y, fill=color, width=1, tags="matrix_overlay"
            )

        self.main_canvas.create_oval(
            cx - 34 - 4 * pulse, cy - 34 - 4 * pulse,
            cx + 34 + 4 * pulse, cy + 34 + 4 * pulse,
            outline=color, width=3, tags="matrix_overlay"
        )

        self.main_canvas.create_text(
            cx, cy + 90,
            text="4D DATA REACTIVE MATRIX",
            fill=color,
            font=("Consolas", 10, "bold"),
            tags="matrix_overlay"
        )

        self.waveform_canvas.delete("all")
        w, h = 240, 90
        active_level = 0.35 + self.audio_level * 0.65
        for x in range(0, w, 4):
            phase = (self.particle_phase / 8.0) + (x / 18.0)
            amp = 8 + (20 * active_level) * math.sin(phase)
            y = h / 2 + amp
            self.waveform_canvas.create_line(x, h / 2, x, y, fill="#00d9ff", width=2)

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
            amplitude = 8 + (32 * self.audio_level)
            y = h / 2 + amplitude * math.sin(phase)
            self.waveform_canvas.create_line(x, h / 2, x, y, fill="#00FFAA")
        self.waveform_phase += 1
        self.after(40, self.animate_waveform)

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
