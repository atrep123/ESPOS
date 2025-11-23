#!/usr/bin/env python3
"""
Simple unified launcher for ESP32OS tools.
- UI Designer (Pro)
- Simulator
- Exporter (C)
- Web mode (backend + frontend)
- Open docs
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import traceback
import webbrowser
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path.home() / ".esp32os" / "config.json"
LOG_PATH = Path.home() / ".esp32os" / "launcher.log"
from tools.common_logging import setup_logging  # noqa: E402
from tools.common_config import load_config as load_cfg, save_config as save_cfg  # noqa: E402

logger = setup_logging("launcher")
try:
    import tkinter as tk  # type: ignore
    from tkinter import ttk  # type: ignore
    from tkinter import messagebox  # type: ignore
except Exception:
    tk = None  # type: ignore
    ttk = None  # type: ignore
    messagebox = None  # type: ignore


DEFAULT_CONFIG: Dict[str, object] = {
    "designer_script": "ui_designer_pro.py",
    "simulator_script": "sim_run.py",
    "web_backend_script": "web_designer_backend_server.py",
    "web_frontend_path": "web_designer_frontend/dist/index.html",
    "web_backend_port": 8000,
    "web_frontend_port": 8001,
    "sim_args": [],
    "designer_args": [],
    "exporter_args": [],
}

# Async/automation mode is enabled via this env flag (used by UI smoke tests).
AUTOMATION_ASYNC = os.getenv("ESP32OS_LAUNCHER_ASYNC") == "1"


def _log_to_file(message: str) -> None:
    """Append launcher messages to a file for troubleshooting silent exits."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.write_text(
            (LOG_PATH.read_text(encoding="utf-8", errors="ignore") if LOG_PATH.exists() else "")
            + message
            + "\n",
            encoding="utf-8",
        )
    except Exception:
        pass


def load_config() -> Dict[str, object]:
    cfg = load_cfg(CONFIG_PATH, DEFAULT_CONFIG)
    return cfg


def save_config(cfg: Dict[str, object]) -> None:
    try:
        save_cfg(CONFIG_PATH, cfg)
        logger.info("Config saved to %s", CONFIG_PATH)
    except Exception as exc:
        logger.error("Failed to save config: %s", exc)


def run_command(desc: str, cmd: list[str], cwd: Optional[Path] = None, async_mode: Optional[bool] = None) -> None:
    async_mode = AUTOMATION_ASYNC if async_mode is None else async_mode
    logger.info("Starting %s (%s): %s", desc, "async" if async_mode else "sync", " ".join(cmd))
    _log_to_file(f"[run] {desc}: {' '.join(cmd)} (async={async_mode})")
    try:
        if async_mode:
            proc = subprocess.Popen(cmd, cwd=cwd or ROOT)
            _log_to_file(f"[popen] {desc} pid={proc.pid}")
            return
        subprocess.run(cmd, cwd=cwd or ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        logger.error("%s exited with %s", desc, exc.returncode)
        _log_to_file(f"[error] {desc} exit={exc.returncode}")
    except FileNotFoundError:
        logger.error("Command not found: %s", cmd[0])
        _log_to_file(f"[error] command not found: {cmd[0]}")
    except Exception as exc:  # defensive catch for frozen exe
        logger.error("Unexpected failure running %s: %s", desc, exc)
        _log_to_file(f"[error] {desc} unexpected: {exc}")


def start_designer(cfg: Dict[str, object]) -> None:
    script = cfg.get("designer_script", DEFAULT_CONFIG["designer_script"])
    args = list(cfg.get("designer_args", []))
    run_command("UI Designer", [sys.executable, str(ROOT / script), *map(str, args)], async_mode=AUTOMATION_ASYNC)


def start_simulator(cfg: Dict[str, object]) -> None:
    script = cfg.get("simulator_script", DEFAULT_CONFIG["simulator_script"])
    args = list(cfg.get("sim_args", []))
    if AUTOMATION_ASYNC and not args:
        frames = os.getenv("ESP32OS_AUTOMATION_SIM_FRAMES", "30")
        try:
            int(frames)
        except Exception:
            frames = "30"
        args = ["--auto-size", "--max-frames", str(frames)]
    run_command("Simulator", [sys.executable, str(ROOT / script), *map(str, args)], async_mode=AUTOMATION_ASYNC)


def run_exporter(cfg: Dict[str, object]) -> None:
    script = "ui_export_c.py"
    args = list(cfg.get("exporter_args", []))
    run_command("Exporter", [sys.executable, str(ROOT / script), *map(str, args)], async_mode=AUTOMATION_ASYNC)


_web_process: Dict[str, Optional[subprocess.Popen]] = {"backend": None, "frontend": None}


def _check_port_open(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _wait_for_port(port: int, timeout: float = 5.0) -> bool:
    import time
    start = time.time()
    while time.time() - start < timeout:
        if _check_port_open(port):
            return True
        time.sleep(0.2)
    return False


def _ws_ping(port: int) -> bool:
    """Attempt a websocket handshake/ping to verify backend health."""
    try:
        import asyncio
        import websockets  # type: ignore
    except Exception:
        return False

    async def _ping() -> bool:
        try:
            url = f"ws://127.0.0.1:{port}/ws/projects/ping"
            async with websockets.connect(url) as ws:  # type: ignore
                await ws.send("ping")
                await ws.recv()
            return True
        except Exception:
            return False

    try:
        return asyncio.run(_ping())
    except Exception:
        return False


def start_web_mode(cfg: Dict[str, object]) -> None:
    backend = cfg.get("web_backend_script", DEFAULT_CONFIG["web_backend_script"])
    frontend = cfg.get("web_frontend_path", DEFAULT_CONFIG["web_frontend_path"])
    backend_port = int(cfg.get("web_backend_port", DEFAULT_CONFIG["web_backend_port"]))
    frontend_port = int(cfg.get("web_frontend_port", DEFAULT_CONFIG["web_frontend_port"]))
    backend_cmd = [sys.executable, str(ROOT / backend)]
    if _check_port_open(backend_port):
        logger.warning("Backend port %s already in use; aborting start.", backend_port)
        return
    logger.info("Starting web backend on port %s...", backend_port)
    try:
        _web_process["backend"] = subprocess.Popen(backend_cmd, cwd=ROOT, env={**os.environ, "PORT": str(backend_port)})
        logger.info("Backend started (pid=%s).", _web_process["backend"].pid if _web_process["backend"] else "?")
    except Exception as exc:
        logger.error("Failed to start backend: %s", exc)
        return
    if not _wait_for_port(backend_port):
        logger.warning("Backend did not open port %s within timeout.", backend_port)
    # Serve frontend via simple HTTP server for consistent CORS
    try:
        front_dir = (ROOT / str(frontend)).parent
        if front_dir.exists():
            if _check_port_open(frontend_port):
                logger.warning("Frontend port %s already in use; skipping server start.", frontend_port)
            else:
                _web_process["frontend"] = subprocess.Popen([sys.executable, "-m", "http.server", str(frontend_port)], cwd=front_dir)
                logger.info("Frontend server started (pid=%s) at http://127.0.0.1:%s/index.html", _web_process["frontend"].pid if _web_process["frontend"] else "?", frontend_port)
            _wait_for_port(frontend_port)
            webbrowser.open(f"http://127.0.0.1:{frontend_port}/index.html")
        else:
            logger.warning("Frontend path not found: %s", front_dir)
    except Exception as exc:
        logger.warning("Could not start frontend server: %s", exc)


def web_status(cfg: Dict[str, object]) -> str:
    backend_port = int(cfg.get("web_backend_port", DEFAULT_CONFIG["web_backend_port"]))
    frontend_port = int(cfg.get("web_frontend_port", DEFAULT_CONFIG["web_frontend_port"]))
    backend_up = _check_port_open(backend_port)
    backend_ws = _ws_ping(backend_port) if backend_up else False
    frontend_up = _check_port_open(frontend_port)
    backend_pid = _web_process["backend"].pid if _web_process["backend"] and _web_process["backend"].poll() is None else "stopped"
    frontend_pid = _web_process["frontend"].pid if _web_process["frontend"] and _web_process["frontend"].poll() is None else "stopped"
    return (
        f"Backend: port {backend_port} {'OPEN' if backend_up else 'closed'}, ws={'ok' if backend_ws else 'no'}, pid={backend_pid}\n"
        f"Frontend: port {frontend_port} {'OPEN' if frontend_up else 'closed'}, pid={frontend_pid}"
    )


def reset_config() -> Dict[str, object]:
    """Restore config to defaults and save."""
    cfg = DEFAULT_CONFIG.copy()
    save_config(cfg)
    logger.info("Config reset to defaults at %s", CONFIG_PATH)
    return cfg


def edit_config(cfg: Dict[str, object]) -> None:
    """Open config in user's editor; fallback to path print."""
    try:
        save_config(cfg)
    except Exception:
        pass
    editor_cmd = None
    if sys.platform.startswith("win"):
        editor_cmd = ["notepad", str(CONFIG_PATH)]
    else:
        editor_env = os.getenv("EDITOR")
        if editor_env:
            editor_cmd = [editor_env, str(CONFIG_PATH)]
        elif sys.platform == "darwin":
            editor_cmd = ["open", str(CONFIG_PATH)]
        else:
            editor_cmd = ["xdg-open", str(CONFIG_PATH)]
    try:
        subprocess.Popen(editor_cmd)
        logger.info("Opening config with %s", " ".join(editor_cmd))
    except Exception as exc:
        logger.warning("Could not open editor: %s. Edit manually at %s", exc, CONFIG_PATH)


def open_frontend(cfg: Dict[str, object]) -> None:
    try:
        port = int(cfg.get("web_frontend_port", DEFAULT_CONFIG["web_frontend_port"]))
        url = f"http://127.0.0.1:{port}/index.html"
        webbrowser.open(url)
        logger.info("Opening frontend %s", url)
    except Exception as exc:
        logger.warning("Failed to open frontend: %s", exc)


def open_backend(cfg: Dict[str, object]) -> None:
    try:
        port = int(cfg.get("web_backend_port", DEFAULT_CONFIG["web_backend_port"]))
        url = f"ws://127.0.0.1:{port}/ws/projects/demo"
        webbrowser.open(url)
        logger.info("Attempted to open backend URL %s (browser may not support ws)", url)
    except Exception as exc:
        logger.warning("Failed to open backend URL: %s", exc)


def run_gui(cfg: Dict[str, object]) -> None:
    if tk is None or ttk is None:
        print("Tkinter not available; use CLI mode.")
        return
    root = tk.Tk()
    root.title("ESP32OS Launcher")
    root.geometry("420x420")
    status_var = tk.StringVar(value="Status pending...")
    auto_exit_ms = 0
    try:
        auto_exit_ms = int(os.getenv("ESP32OS_AUTOMATION_EXIT", "0"))
    except Exception:
        auto_exit_ms = 0

    def refresh_status():
        try:
            status_var.set(web_status(cfg))
        except Exception as exc:
            status_var.set(f"Status error: {exc}")
        root.after(2000, refresh_status)

    btns = [
        ("Alt+1  UI Designer", lambda: start_designer(cfg), "1"),
        ("Alt+2  Simulator", lambda: start_simulator(cfg), "2"),
        ("Alt+3  Export C assets", lambda: run_exporter(cfg), "3"),
        ("Alt+4  Start Web mode", lambda: start_web_mode(cfg), "4"),
        ("Alt+5  Stop Web mode", stop_web_mode, "5"),
        ("Alt+6  Open frontend", lambda: open_frontend(cfg), "6"),
        ("Alt+7  Open backend URL", lambda: open_backend(cfg), "7"),
        ("Alt+8  Edit config", lambda: edit_config(cfg), "8"),
        ("Alt+9  Reset config", lambda: reset_config(), "9"),
        ("Alt+0  Docs", open_docs, "0"),
        ("Alt+Q  Quit", root.destroy, "q"),
    ]
    for text, cmd, hotkey in btns:
        # Set a widget name for automation tools (no spaces, lowercase)
        widget_name = text.lower().replace(" ", "_").replace("-", "_")
        b = ttk.Button(root, text=text, command=cmd, width=32, name=widget_name, takefocus=True)
        b.pack(pady=3)
        try:
            root.bind_all(f"<Alt-{hotkey}>", lambda e, c=cmd: c())
        except Exception:
            pass
    try:
        root.bind_all("<Alt-F4>", lambda e: root.destroy())
    except Exception:
        pass

    tk.Label(root, text="Status (auto-refresh):").pack(pady=(6, 0))
    status_label = tk.Label(root, textvariable=status_var, justify="left", fg="gray20", wraplength=380)
    status_label.pack(pady=4)

    lbl = tk.Label(root, text=f"Config: {CONFIG_PATH}", fg="gray")
    lbl.pack(pady=6)
    try:
        root.focus_force()
    except Exception:
        pass
    if auto_exit_ms > 0:
        try:
            root.after(auto_exit_ms, root.destroy)
            logger.info("Automation exit scheduled after %sms", auto_exit_ms)
        except Exception:
            pass
    refresh_status()
    root.mainloop()


def stop_web_mode() -> None:
    for key in ["frontend", "backend"]:
        proc = _web_process.get(key)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                logger.info("Stopped web %s (pid=%s)", key, proc.pid)
            except Exception as exc:
                logger.warning("Failed to stop %s: %s", key, exc)
        _web_process[key] = None


def open_docs() -> None:
    docs = [ROOT / "README.md", ROOT / "QUICKSTART.md", ROOT / "SIMULATOR_README.md"]
    for doc in docs:
        if doc.exists():
            webbrowser.open(doc.as_uri())
            logger.info("Opened %s", doc)
            return
    logger.warning("No docs found to open.")


def print_menu() -> None:
    print("\n=== ESP32OS Launcher ===")
    print("1) UI Designer")
    print("2) Simulator")
    print("3) Export C assets")
    print("4) Web mode (start backend + frontend server)")
    print("5) Stop web mode")
    print("6) Open docs")
    print("p) Show ports/config/status")
    print("r) Reset config to defaults")
    print("e) Edit config in external editor")
    print("s) Save config")
    print("q) Quit")


def main() -> None:
    parser = argparse.ArgumentParser(description="ESP32OS launcher")
    parser.add_argument("--gui", action="store_true", help="Launch GUI menu (Tkinter)")
    args = parser.parse_args()
    cfg = load_config()

    if args.gui:
        if tk is None:
            print("Tkinter not available; falling back to CLI menu.")
        else:
            return run_gui(cfg)

    # If stdin is not interactive (e.g., windowed exe), auto-start designer instead of waiting for input().
    try:
        stdin_ok = sys.stdin is not None and sys.stdin.isatty()
    except Exception:
        stdin_ok = False
    if not stdin_ok:
        print("Non-interactive session detected; starting UI Designer...")
        _log_to_file("[info] stdin not interactive, auto-starting designer")
        start_designer(cfg)
        return

    while True:
        print_menu()
        try:
            choice = input("Select option: ").strip().lower()
        except (EOFError, RuntimeError):
            print("Input unavailable; exiting.")
            _log_to_file("[warn] input unavailable, exiting menu loop")
            break
        if choice == '1':
            start_designer(cfg)
        elif choice == '2':
            start_simulator(cfg)
        elif choice == '3':
            run_exporter(cfg)
        elif choice == '4':
            start_web_mode(cfg)
        elif choice == '5':
            stop_web_mode()
        elif choice == '6':
            open_docs()
        elif choice == 'p':
            print(f"Config: {cfg}")
            print(web_status(cfg))
        elif choice == 's':
            save_config(cfg)
        elif choice == 'r':
            cfg = reset_config()
        elif choice == 'e':
            edit_config(cfg)
        elif choice == 'q':
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # Make silent failures visible
        _log_to_file("[fatal] " + "".join(traceback.format_exception(exc)))
        try:
            if messagebox:
                messagebox.showerror("Launcher error", f"Failed to start: {exc}\nLog: {LOG_PATH}")
        except Exception:
            pass
