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
            ("BLUEPRINT SCAN", "jarvis scan blueprint", self.CYAN),
            ("DAEMON PULSE", "jarvis pulse daemon", self.RED),
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
            ("SEARCH", "router:search"),
            ("PRINTER", "router:printer status"),
            ("STEAM", "router:steam"),
            ("STATUS", "jarvis status"),
        )):
            self._button(tools, text, lambda value=command: self.run(value)).grid(
                row=0, column=index, padx=3, sticky="ew"
            )
            tools.grid_columnconfigure(index, weight=1)

    def run_custom(self):
        command = self.command_var.get().strip()
        if command:
            self.command_var.set("")
            self.run(command)

    def run(self, command):
        self.hud.process_command(command, original=command)
        self.refresh()

    def refresh(self):
        if not self.winfo_exists():
            return
        self.status_var.set(self.hud.current_status)
        self.mode_var.set(self.hud.matrix_mode)
        self.voice_var.set("ACTIVE" if self.hud.voice_running else "IDLE")
        self.router_var.set(self.hud._router_init_status.upper())
        self.after(500, self.refresh)
