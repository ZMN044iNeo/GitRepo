import tkinter as tk


class JarvisControlPanel(tk.Toplevel):
    """Native control surface for the Jarvis HUD."""

    BACKGROUND = "#05080b"
    PANEL = "#0c141b"
    BORDER = "#1f6470"
    CYAN = "#00e5ff"
    GREEN = "#42f56c"
    AMBER = "#ffb000"
    RED = "#ff5c5c"
    MUTED = "#9bb4bd"

    def __init__(self, hud):
        super().__init__(hud)
        self.hud = hud
        self.title("JARVIS Control Surface")
        self.geometry("500x650")
        self.minsize(420, 560)
        self.configure(bg=self.BACKGROUND)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        self.status_var = tk.StringVar()
        self.mode_var = tk.StringVar()
        self.voice_var = tk.StringVar()
        self.router_var = tk.StringVar()
        self.command_var = tk.StringVar()

        self._build_ui()
        self.refresh()

    def _section(self, parent, title):
        frame = tk.LabelFrame(
            parent,
            text=f"  {title}  ",
            fg=self.CYAN,
            bg=self.PANEL,
            bd=1,
            relief="solid",
            font=("Consolas", 10, "bold"),
            padx=10,
            pady=10,
        )
        frame.pack(fill="x", padx=16, pady=(0, 12))
        return frame

    def _button(self, parent, text, command, color=None):
        return tk.Button(
            parent,
            text=text,
            command=command,
            fg=color or self.CYAN,
            bg="#101d25",
            activeforeground="#ffffff",
            activebackground="#1b3844",
            bd=1,
            relief="solid",
            font=("Consolas", 10, "bold"),
            padx=8,
            pady=8,
            cursor="hand2",
        )

    def _build_ui(self):
        header = tk.Frame(self, bg=self.BACKGROUND)
        header.pack(fill="x", padx=16, pady=(16, 12))
        tk.Label(
            header,
            text="JARVIS CONTROL SURFACE",
            fg=self.CYAN,
            bg=self.BACKGROUND,
            font=("Consolas", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="LOCAL DESKTOP INTERFACE",
            fg=self.MUTED,
            bg=self.BACKGROUND,
            font=("Consolas", 9),
        ).pack(anchor="w", pady=(3, 0))

        telemetry = self._section(self, "SYSTEM TELEMETRY")
        for label, variable in (
            ("STATUS", self.status_var),
            ("MATRIX", self.mode_var),
            ("VOICE", self.voice_var),
            ("ROUTER", self.router_var),
        ):
            row = tk.Frame(telemetry, bg=self.PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, width=10, anchor="w", fg=self.MUTED, bg=self.PANEL, font=("Consolas", 10)).pack(side="left")
            tk.Label(row, textvariable=variable, anchor="e", fg=self.GREEN, bg=self.PANEL, font=("Consolas", 10, "bold")).pack(side="right")

        matrix = self._section(self, "MATRIX MODE")
        for column, (text, command, color) in enumerate((
            ("DEFAULT", "jarvis matrix default", self.CYAN),
            ("QUANTUM", "jarvis matrix quantum", "#d07cff"),
            ("STEALTH", "jarvis matrix stealth", self.MUTED),
            ("OVERCLOCK", "jarvis matrix overclock", self.RED),
        )):
            self._button(matrix, text, lambda value=command: self.run(value), color).grid(row=0, column=column, padx=3, sticky="ew")
            matrix.grid_columnconfigure(column, weight=1)

        controls = self._section(self, "AUDIO AND VISUAL")
        actions = (
            ("VOICE ON", "jarvis voice on", self.GREEN),
            ("VOICE OFF", "jarvis voice off", self.AMBER),
            ("TEST SPEECH", "jarvis voice test", self.GREEN),
            ("SPEECH OFF", "jarvis voice output off", self.AMBER),
            ("BLUEPRINT SCAN", "jarvis scan blueprint", self.CYAN),
            ("DAEMON PULSE", "jarvis pulse daemon", self.RED),
            ("CINEMATIC REPLAY", "jarvis cinematic replay", self.CYAN),
            ("SYNC BEAM", "jarvis sync", self.CYAN),
            ("CALM SYSTEM", "jarvis calm", self.AMBER),
        )
        for index, (text, command, color) in enumerate(actions):
            self._button(controls, text, lambda value=command: self.run(value), color).grid(
                row=index // 2, column=index % 2, padx=3, pady=3, sticky="ew"
            )
        controls.grid_columnconfigure(0, weight=1)
        controls.grid_columnconfigure(1, weight=1)

        command_frame = self._section(self, "COMMAND")
        entry = tk.Entry(
            command_frame,
            textvariable=self.command_var,
            fg=self.CYAN,
            bg="#020405",
            insertbackground=self.CYAN,
            bd=1,
            relief="solid",
            font=("Consolas", 11),
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        entry.bind("<Return>", lambda _event: self.run_custom())
        self._button(command_frame, "RUN", self.run_custom, self.GREEN).pack(side="right")

        tools = self._section(self, "TOOLS")
        for index, (text, command) in enumerate((
            ("CODE ASSISTANT", "open_coding"),
            ("SEARCH", "router:search"),
            ("PRINTER", "router:printer status"),
            ("STEAM", "router:steam"),
            ("STATUS", "jarvis status"),
        )):
            action = self.open_coding_assistant if command == "open_coding" else lambda value=command: self.run(value)
            self._button(tools, text, action).grid(
                row=0, column=index, padx=3, sticky="ew"
            )
            tools.grid_columnconfigure(index, weight=1)

    def open_coding_assistant(self):
        if hasattr(self, "coding_window") and self.coding_window.winfo_exists():
            self.coding_window.show_in_foreground()
            return
        self.coding_window = JarvisCodingWindow(self, self.hud)

    def run_custom(self):
        command = self.command_var.get().strip()
        if command:
            self.command_var.set("")
            self.run(command)

    def run(self, command):
        self.hud.process_command(command, original=command)
        self.refresh()

    def show_in_foreground(self):
        """Restore and raise the panel after the main HUD completes startup."""
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(150, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def refresh(self):
        if not self.winfo_exists():
            return
        self.status_var.set(self.hud.current_status)
        self.mode_var.set(self.hud.matrix_mode)
        self.voice_var.set("ACTIVE" if self.hud.voice_running else "IDLE")
        self.router_var.set(self.hud._router_init_status.upper())
        self.after(500, self.refresh)


class JarvisCodingWindow(tk.Toplevel):
    """Native, read-only coding workspace controls."""

    def __init__(self, parent, hud):
        super().__init__(parent)
        self.hud = hud
        self.title("JARVIS Coding Assistant")
        self.geometry("760x620")
        self.minsize(600, 480)
        self.configure(bg=JarvisControlPanel.BACKGROUND)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        self.query_var = tk.StringVar()
        self._build_ui()
        self.show_in_foreground()
        self.run_action("status")

    def _button(self, parent, text, command):
        return tk.Button(
            parent,
            text=text,
            command=command,
            fg=JarvisControlPanel.CYAN,
            bg="#101d25",
            activeforeground="#ffffff",
            activebackground="#1b3844",
            bd=1,
            relief="solid",
            font=("Consolas", 10, "bold"),
            padx=8,
            pady=8,
            cursor="hand2",
        )

    def _build_ui(self):
        tk.Label(
            self,
            text="JARVIS CODING ASSISTANT",
            fg=JarvisControlPanel.CYAN,
            bg=JarvisControlPanel.BACKGROUND,
            font=("Consolas", 16, "bold"),
        ).pack(anchor="w", padx=16, pady=(16, 2))
        tk.Label(
            self,
            text="LOCAL READ-ONLY WORKSPACE TOOLS // E:\\Users\\pharo\\Desktop\\GitRepo",
            fg=JarvisControlPanel.MUTED,
            bg=JarvisControlPanel.BACKGROUND,
            font=("Consolas", 9),
        ).pack(anchor="w", padx=16, pady=(0, 14))

        actions = tk.Frame(self, bg=JarvisControlPanel.BACKGROUND)
        actions.pack(fill="x", padx=16, pady=(0, 10))
        for index, (label, action) in enumerate((
            ("PROJECT STATUS", "status"),
            ("VALIDATE PYTHON", "validate"),
            ("LIST PYTHON FILES", "list"),
        )):
            self._button(actions, label, lambda value=action: self.run_action(value)).grid(
                row=0, column=index, padx=3, sticky="ew"
            )
            actions.grid_columnconfigure(index, weight=1)

        search = tk.Frame(self, bg=JarvisControlPanel.BACKGROUND)
        search.pack(fill="x", padx=16, pady=(0, 10))
        entry = tk.Entry(
            search,
            textvariable=self.query_var,
            fg=JarvisControlPanel.CYAN,
            bg="#020405",
            insertbackground=JarvisControlPanel.CYAN,
            font=("Consolas", 11),
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        entry.bind("<Return>", lambda _event: self.run_action("search"))
        self._button(search, "FIND", lambda: self.run_action("search")).pack(side="left", padx=(0, 6))
        self._button(search, "READ FILE", lambda: self.run_action("read")).pack(side="left")

        self.output = tk.Text(
            self,
            fg="#a9ffbc",
            bg="#020405",
            insertbackground=JarvisControlPanel.CYAN,
            bd=1,
            relief="solid",
            wrap="none",
            font=("Consolas", 10),
            state="disabled",
        )
        self.output.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def run_action(self, action):
        query = self.query_var.get().strip()
        command = f"code:{action}"
        if action in ("search", "read"):
            command = f"{command}:{query}"
        result = self.hud.run_coding_command(command)
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", result)
        self.output.config(state="disabled")
        self.hud.log_console(f"[CODE] {action}: completed")

    def show_in_foreground(self):
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(150, lambda: self.attributes("-topmost", False))
        self.focus_force()
