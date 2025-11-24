#!/usr/bin/env python3
"""ESP32 OS Workspace - Unified UI Designer & Simulator.

Unified launcher for UI Designer and Simulator processes with a dark theme,
recent project management, restart/stop controls and basic settings.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, List, TypedDict


class WorkspaceConfig(TypedDict, total=False):
    last_project: str
    designer_width: int
    designer_height: int
    simulator_port: int
    auto_start_simulator: bool
    recent_projects: List[str]


class ESP32Workspace:
    """Main workspace window with Designer and Simulator"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ESP32 OS Workspace")
        self.root.geometry("1400x800")

        # Dark theme colors
        self.colors = {
            "bg": "#1e1e1e",
            "bg_dark": "#252525",
            "bg_light": "#2d2d2d",
            "fg": "#cccccc",
            "fg_bright": "#ffffff",
            "accent": "#007acc",
            "accent_hover": "#1e8ad6",
            "border": "#3e3e3e",
            "success": "#4ec9b0",
            "warning": "#dcdcaa",
        }

        # Apply dark theme
        self.root.configure(bg=self.colors["bg"])

        # Configure ttk dark theme
        style = ttk.Style()
        style.theme_use("clam")

        # Configure colors for all widgets
        style.configure(".", background=self.colors["bg"], foreground=self.colors["fg"])
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["fg"])
        style.configure(
            "TButton",
            background=self.colors["bg_light"],
            foreground=self.colors["fg_bright"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["bg_light"],
            darkcolor=self.colors["bg_dark"],
        )
        style.map(
            "TButton",
            background=[
                ("active", self.colors["accent_hover"]),
                ("pressed", self.colors["accent"]),
            ],
            foreground=[("active", self.colors["fg_bright"])],
        )

        style.configure(
            "TLabelframe",
            background=self.colors["bg"],
            foreground=self.colors["fg"],
            bordercolor=self.colors["border"],
        )
        style.configure(
            "TLabelframe.Label", background=self.colors["bg"], foreground=self.colors["accent"]
        )

        # Processes
        self.designer_process = None
        self.simulator_process = None

        # Config
        self.config_file = Path.home() / ".esp32os_workspace.json"
        self.config: WorkspaceConfig = self.load_config()

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        # Initialize tooltips after UI setup
        try:
            Tooltips(self)
        except Exception:
            pass  # Tooltips are non-critical

    def load_config(self) -> WorkspaceConfig:
        """Load workspace configuration (best-effort)."""
        if self.config_file.exists():
            try:
                raw = json.loads(self.config_file.read_text())
                if isinstance(raw, dict):
                    return raw  # type: ignore[return-value]
            except Exception:
                pass
        return WorkspaceConfig(
            last_project="",
            designer_width=128,
            designer_height=64,
            simulator_port=8765,
            auto_start_simulator=True,
            recent_projects=[],
        )

    def save_config(self) -> None:
        """Persist workspace configuration to disk."""
        try:
            self.config_file.write_text(json.dumps(self.config, indent=2))
        except Exception:
            pass

    def setup_ui(self):
        """Setup main UI"""
        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Label(toolbar, text="ESP32 OS Workspace", font=("Arial", 14, "bold")).pack(
            side=tk.LEFT, padx=10
        )

        # Toolbar buttons (stored for tooltips)
        self.btn_designer = ttk.Button(toolbar, text="🎨 UI Designer", command=self.start_designer)
        self.btn_designer.pack(side=tk.LEFT, padx=5)
        self.btn_sim = ttk.Button(toolbar, text="📱 Simulátor", command=self.start_simulator)
        self.btn_sim.pack(side=tk.LEFT, padx=5)
        self.btn_both = ttk.Button(toolbar, text="🔗 Oba", command=self.start_both)
        self.btn_both.pack(side=tk.LEFT, padx=5)
        self.btn_restart = ttk.Button(toolbar, text="🔄 Restart", command=self.restart_processes)
        self.btn_restart.pack(side=tk.LEFT, padx=5)
        self.btn_stop = ttk.Button(toolbar, text="⏹ Stop", command=self.stop_processes)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Button(toolbar, text="📂 Otevřít projekt", command=self.open_project).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(toolbar, text="💾 Uložit", command=self.save_project).pack(side=tk.LEFT, padx=5)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        ttk.Button(toolbar, text="⚙️ Nastavení", command=self.show_settings).pack(
            side=tk.LEFT, padx=5
        )

        # Status bar
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ttk.Label(self.status_bar, text="Připraven", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)

        # Main content area
        content = ttk.Frame(self.root)
        content.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Quick actions panel
        quick_panel = ttk.LabelFrame(content, text="Rychlé akce", padding=10)
        quick_panel.pack(fill=tk.BOTH, expand=True)

        # Recent projects
        ttk.Label(quick_panel, text="Poslední projekty:", font=("Arial", 10, "bold")).pack(
            anchor=tk.W, pady=(0, 5)
        )

        self.recent_list = tk.Listbox(
            quick_panel,
            height=8,
            bg=self.colors["bg_dark"],
            fg=self.colors["fg"],
            selectbackground=self.colors["accent"],
            selectforeground=self.colors["fg_bright"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
            borderwidth=0,
        )
        self.recent_list.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.recent_list.bind("<Double-Button-1>", lambda e: self.open_recent())

        # Populate recent projects
        recent = self.config.get("recent_projects", []) or []
        for project in recent[-10:]:  # Last 10 projects
            if Path(project).exists():
                self.recent_list.insert(tk.END, project)

        # Quick start buttons
        btn_frame = ttk.Frame(quick_panel)
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame, text="Nový projekt (128x64)", command=lambda: self.new_project(128, 64)
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            btn_frame, text="Nový projekt (320x240)", command=lambda: self.new_project(320, 240)
        ).pack(fill=tk.X, pady=2)

        # Info panel
        info_frame = ttk.LabelFrame(content, text="Nápověda", padding=10)
        info_frame.pack(fill=tk.X, pady=(5, 0))

        help_text = """💡 Jak začít:
1. Klikni na "Nový projekt" nebo "Otevřít projekt"
2. Klikni na "🔗 Oba" pro spuštění Designeru i Simulátoru
3. V Designeru vytvoř UI, změny se zobrazí v Simulátoru

⌨️ Klávesové zkratky:
• Ctrl+S: Uložit projekt
• Ctrl+O: Otevřít projekt
• F5: Refresh simulátoru
"""
        help_label = tk.Text(
            info_frame,
            height=10,
            wrap=tk.WORD,
            bg=self.colors["bg_dark"],
            fg=self.colors["fg"],
            font=("Consolas", 9),
            relief=tk.FLAT,
            padx=10,
            pady=10,
            highlightthickness=0,
        )
        help_label.insert("1.0", help_text)
        help_label.config(state=tk.DISABLED)
        help_label.pack(fill=tk.BOTH, expand=True)

    def update_status(self, message: str) -> None:
        """Update status bar message (safe no-op if label missing)."""
        try:
            self.status_label.config(text=message)
            self.root.update_idletasks()
        except Exception:
            pass

    def start_designer(self, auto_start: bool | None = None):
        """Start UI Designer (optionally auto-start simulator based on settings)."""
        if auto_start is None:
            auto_start = bool(self.config.get("auto_start_simulator", True))
        if self.designer_process and self.designer_process.poll() is None:
            messagebox.showinfo("Info", "UI Designer už běží")
            return

        try:
            cmd = [sys.executable, "ui_designer_pro.py"]
            last_project = self.config.get("last_project")
            if isinstance(last_project, str) and last_project:
                cmd.extend(["--load", last_project])

            self.designer_process = subprocess.Popen(cmd, cwd=os.getcwd())
            self.update_status("UI Designer spuštěn")
            if auto_start:
                # Small delay to let Designer spin up before attaching simulator
                self.root.after(800, self.start_simulator)
        except Exception as e:
            messagebox.showerror("Chyba", f"Nelze spustit Designer: {e}")

    def start_simulator(self):
        """Start Simulator"""
        if self.simulator_process and self.simulator_process.poll() is None:
            messagebox.showinfo("Info", "Simulátor už běží")
            return

        try:
            port = self.config.get("simulator_port", 8765)
            cmd = [sys.executable, "scripts/sim_run.py", "--rpc-port", str(port)]

            self.simulator_process = subprocess.Popen(cmd, cwd=os.getcwd())
            self.update_status(f"Simulátor spuštěn na portu {port}")
        except Exception as e:
            messagebox.showerror("Chyba", f"Nelze spustit Simulátor: {e}")

    def start_both(self):
        """Start both Designer and Simulator"""
        self.start_designer(auto_start=False)
        self.root.after(1000, self.start_simulator)  # Wait 1s before starting simulator
        self.update_status("Designer a Simulátor spuštěny")

    def stop_processes(self):
        """Gracefully stop running processes"""
        stopped = []
        for name, proc in (
            ("Designer", self.designer_process),
            ("Simulátor", self.simulator_process),
        ):
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                stopped.append(name)
        if stopped:
            self.update_status(f"Ukončeno: {', '.join(stopped)}")
        else:
            self.update_status("Nic neběží")

    def restart_processes(self):
        """Restart both Designer and Simulator."""
        self.stop_processes()
        # Short delay not strictly needed; processes are terminated synchronously
        self.start_both()

    def new_project(self, width: int, height: int) -> None:
        """Create new project"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON soubory", "*.json"), ("Všechny soubory", "*.*")],
            title="Nový projekt",
        )

        if not filename:
            return

        # Create empty scene
        scene_data = {"width": width, "height": height, "widgets": [], "version": "1.0"}

        try:
            Path(filename).write_text(json.dumps(scene_data, indent=2))
            self.config["last_project"] = filename
            self.add_to_recent(filename)
            self.save_config()
            self.update_status(f"Projekt vytvořen: {filename}")

            # Start designer with new project
            self.start_designer()
        except Exception as e:
            messagebox.showerror("Chyba", f"Nelze vytvořit projekt: {e}")

    def open_project(self):
        """Open existing project"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON soubory", "*.json"), ("Všechny soubory", "*.*")],
            title="Otevřít projekt",
        )

        if not filename:
            return

        self.config["last_project"] = filename
        self.add_to_recent(filename)
        self.save_config()
        self.update_status(f"Projekt otevřen: {filename}")

        self.start_designer()

    def open_recent(self):
        """Open recently used project"""
        sel = self.recent_list.curselection()
        if not sel:
            return
        try:
            idx = int(sel[0])
        except Exception:
            return
        filename = self.recent_list.get(idx)
        if isinstance(filename, str) and filename and Path(filename).exists():
            self.config["last_project"] = filename
            self.save_config()
            self.start_designer()
        else:
            messagebox.showerror("Chyba", f"Soubor nenalezen: {filename}")

    def save_project(self):
        """Save current project"""
        if not self.config.get("last_project"):
            messagebox.showinfo("Info", "Žádný otevřený projekt")
            return

        # Designer should handle saving
        self.update_status("Uloženo (Designer se postará o uložení)")

    def add_to_recent(self, filename: str) -> None:
        """Add project to recent list"""
        recent = self.config.get("recent_projects", []) or []
        if filename in recent:
            recent.remove(filename)
        recent.append(filename)
        self.config["recent_projects"] = recent[-10:]  # Keep last 10

        # Update UI
        self.recent_list.delete(0, tk.END)
        for project in self.config["recent_projects"]:
            if Path(project).exists():
                self.recent_list.insert(tk.END, project)

    def show_settings(self):
        """Show settings dialog"""
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Nastavení")
        settings_win.geometry("400x300")
        settings_win.transient(self.root)
        settings_win.configure(bg=self.colors["bg"])

        ttk.Label(settings_win, text="Nastavení Workspace", font=("Arial", 12, "bold")).pack(
            pady=10
        )

        frame = ttk.Frame(settings_win, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Designer resolution
        ttk.Label(frame, text="Designer rozlišení:").grid(row=0, column=0, sticky=tk.W, pady=5)

        res_frame = ttk.Frame(frame)
        res_frame.grid(row=0, column=1, sticky=tk.W, pady=5)

        width_var = tk.IntVar(value=self.config.get("designer_width", 128))
        height_var = tk.IntVar(value=self.config.get("designer_height", 64))

        ttk.Entry(res_frame, textvariable=width_var, width=8).pack(side=tk.LEFT)
        ttk.Label(res_frame, text=" x ").pack(side=tk.LEFT)
        ttk.Entry(res_frame, textvariable=height_var, width=8).pack(side=tk.LEFT)

        # Simulator port
        ttk.Label(frame, text="Simulátor port:").grid(row=1, column=0, sticky=tk.W, pady=5)
        port_var = tk.IntVar(value=self.config.get("simulator_port", 8765))
        ttk.Entry(frame, textvariable=port_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)

        # Auto-start simulator
        auto_start = tk.BooleanVar(value=self.config.get("auto_start_simulator", True))
        ttk.Checkbutton(
            frame, text="Automaticky spustit simulátor s Designerem", variable=auto_start
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=10)

        def save_settings():
            self.config["designer_width"] = width_var.get()
            self.config["designer_height"] = height_var.get()
            self.config["simulator_port"] = port_var.get()
            self.config["auto_start_simulator"] = auto_start.get()
            self.save_config()
            settings_win.destroy()
            messagebox.showinfo("Info", "Nastavení uloženo")

        ttk.Button(frame, text="Uložit", command=save_settings).grid(
            row=3, column=0, columnspan=2, pady=20
        )

    def on_close(self):
        """Handle window close"""
        # Gracefully stop child processes (with wait/kill fallback)
        try:
            self.stop_processes()
        except Exception:
            pass

        self.save_config()
        self.root.destroy()

    def run(self):
        """Run workspace"""
        self.root.mainloop()


class Tooltips:
    """Attach simple hover tooltips to primary toolbar buttons (no dynamic widget attrs)."""

    def __init__(self, ws: ESP32Workspace):
        self._tips: dict[tk.Widget, tk.Toplevel] = {}
        self._add(ws.btn_designer, "Spustí UI Designer")
        self._add(ws.btn_sim, "Spustí Simulátor")
        self._add(ws.btn_both, "Spustí oba procesy")
        self._add(ws.btn_restart, "Restartuje Designer + Simulátor")
        self._add(ws.btn_stop, "Ukončí běžící procesy")

    def _add(self, widget: ttk.Button, text: str) -> None:
        def show(_e: Any = None):
            if widget in self._tips:
                return
            try:
                x = widget.winfo_rootx() + 12
                y = widget.winfo_rooty() + widget.winfo_height() + 4
            except Exception:
                return
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{x}+{y}")
            lbl = tk.Label(
                tip,
                text=text,
                bg="#2d2d2d",
                fg="#cccccc",
                bd=1,
                relief=tk.SOLID,
                padx=6,
                pady=2,
                font=("Consolas", 9),
            )
            lbl.pack()
            self._tips[widget] = tip

        def hide(_e: Any = None):
            tip = self._tips.pop(widget, None)
            if tip:
                try:
                    tip.destroy()
                except Exception:
                    pass

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)


def main():
    """Main entry point"""
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    app = ESP32Workspace()
    app.run()


if __name__ == "__main__":
    main()
