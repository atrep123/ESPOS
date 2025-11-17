#!/usr/bin/env python3
from __future__ import annotations
"""
ESP32 UI Simulator - Python Version
Runs without requiring C compiler
"""

import os
import sys
import time
import platform
import argparse
import threading
import socket
import json
import queue
import atexit
import re
from typing import Tuple, Any, List, Dict, Optional, TypedDict, Literal, Union, Callable, Set, cast, TYPE_CHECKING, Iterable, Mapping
from datetime import datetime
from dataclasses import dataclass

pygame: Any
try:
    import pygame  # type: ignore
except Exception:
    pygame = None  # type: ignore

if TYPE_CHECKING:
    import pygame  # type: ignore  # pragma: no cover

class RPCEvent(TypedDict):
    type: Literal['rpc']
    data: Dict[str, Any]


class UARTEvent(TypedDict):
    type: Literal['uart']
    line: str


Event = Union[RPCEvent, UARTEvent]

# --- ANSI helpers ---
ANSI_ESC = "\033["

def _is_ansi_at(s: str, i: int) -> bool:
    return i < len(s) and s[i] == "\033" and i + 1 < len(s) and s[i+1] == '['

def _next_after_ansi(s: str, i: int) -> int:
    j = i + 2
    while j < len(s):
        if s[j].isalpha():
            return j + 1
        j += 1
    return len(s)

def _first_diff_visual(prev: str, curr: str) -> Tuple[int, int]:
    """Return (prev_idx, curr_idx) string indices at the first differing visible column.
    Skips ANSI CSI sequences (e.g., \x1b[...m). If no diff, returns (len(prev), len(curr))."""
    ip = ic = 0
    while ip < len(prev) and ic < len(curr):
        if _is_ansi_at(prev, ip):
            ip = _next_after_ansi(prev, ip)
            continue
        if _is_ansi_at(curr, ic):
            ic = _next_after_ansi(curr, ic)
            continue
        if ip >= len(prev) or ic >= len(curr):
            break
        if prev[ip] != curr[ic]:
            return (ip, ic)
        ip += 1
        ic += 1
    return (len(prev), len(curr))

def _col_of_index(s: str, idx: int) -> int:
    """Return visible column number (0-based) for a given string index, skipping ANSI CSI."""
    col = 0
    i = 0
    while i < len(s) and i < idx:
        if _is_ansi_at(s, i):
            i = _next_after_ansi(s, i)
            continue
        col += 1
        i += 1
    return col

# ANSI color codes
class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

@dataclass
class UIState:
    bg: int = 0x0821  # rgb565(8, 8, 8)
    t: int = 0
    btnA: bool = False
    btnB: bool = False
    btnC: bool = False
    scene: int = 0  # 0=HOME, 1=SETTINGS, 2=CUSTOM

@dataclass
class RenderContext:
    state: UIState
    frame_num: int
    fps: float
    width: int
    height: int
    use_unicode: bool
    use_color: bool

# --- Shared state snapshot for RPC get_state ---
_snapshot_lock = threading.Lock()
_current_state_snapshot: Dict[str, Any] = {}


def _update_state_snapshot(state: UIState, frame: int, fps: float,
                           event_queue_size: int, render_time_ms: float,
                           input_src: str) -> None:
    """Update global state snapshot used by RPC get_state."""
    global _current_state_snapshot
    snap: Dict[str, Any] = {
        "scene": int(state.scene),
        "bg_color": int(state.bg),
        "buttons": {
            "A": bool(state.btnA),
            "B": bool(state.btnB),
            "C": bool(state.btnC),
        },
        "fps": float(fps),
        "frame_count": int(frame),
        "event_queue_size": int(event_queue_size),
        "render_time_ms": float(render_time_ms),
        "custom": {"input_src": input_src},
    }
    with _snapshot_lock:
        _current_state_snapshot = snap


def get_state_snapshot() -> Dict[str, Any]:
    """Return a shallow copy of the latest state snapshot for RPC/inspector."""
    with _snapshot_lock:
        return dict(_current_state_snapshot)
    compute_ms: float = 0.0
    sleep_ms: float = 0.0
    util: float = 0.0
    input_src: str = ""

class Widget:
    def render(self, ctx: RenderContext) -> List[str]:
        return []

class TitleBarWidget(Widget):
    def render(self, ctx: RenderContext) -> List[str]:
        use_unicode = ctx.use_unicode
        use_color = ctx.use_color
        width = ctx.width
        if use_unicode:
            tl,tr,hv,vt = '╔','╗','═','║'
        else:
            tl,tr,hv,vt = '+','+','-','|'
        bold = Color.BOLD if use_color else ''
        cyan = Color.CYAN if use_color else ''
        reset = Color.RESET if use_color else ''
        lines: List[str] = []
        lines.append(f"{bold}{cyan}{tl}{hv * width}{tr}{reset}")
        title = " ESP32 UI SIMULATOR"
        vis_len = len(title)  # plain text, no ANSI
        padding = max(0, width - vis_len)
        lines.append(f"{bold}{cyan}{vt}{reset}{bold}{title}{' ' * padding}{cyan}{vt}{reset}")
        return lines

class DividerWidget(Widget):
    def render(self, ctx: RenderContext) -> List[str]:
        use_unicode = ctx.use_unicode
        use_color = ctx.use_color
        width = ctx.width
        if use_unicode:
            crossL,crossR,hv = '╠','╣','═'
        else:
            crossL,crossR,hv = '+','+','-'
        cyan = Color.CYAN if use_color else ''
        reset = Color.RESET if use_color else ''
        return [f"{cyan}{crossL}{hv * width}{crossR}{reset}"]

class SceneStatusWidget(Widget):
    def render(self, ctx: RenderContext) -> List[str]:
        use_unicode = ctx.use_unicode
        use_color = ctx.use_color
        width = ctx.width
        state = ctx.state
        scene_names = ["HOME", "SETTINGS", "CUSTOM"]
        scene_name = scene_names[state.scene % 3]
        if use_unicode:
            sep = '│'
        else:
            sep = '|'
        bold = Color.BOLD if use_color else ''
        cyan = Color.CYAN if use_color else ''
        yellow = Color.YELLOW if use_color else ''
        green = Color.GREEN if use_color else ''
        reset = Color.RESET if use_color else ''
        line = (
            f"{cyan}║{reset} Scene: {bold}{yellow}{scene_name:<10}{reset} {sep} "
            f"Tick: {bold}{state.t:6d}{reset} {sep} "
            f"FPS: {bold}{green}{ctx.fps:5.1f}{reset}"
        )
        vis_len = _col_of_index(line, len(line))
        padding = max(0, width - vis_len + 1)  # +1 for leading border
        return [f"{line}{' ' * padding}{cyan}║{reset}"]

class ColorInfoWidget(Widget):
    def render(self, ctx: RenderContext) -> List[str]:
        use_color = ctx.use_color
        width = ctx.width
        state = ctx.state
        cyan = Color.CYAN if use_color else ''
        bold = Color.BOLD if use_color else ''
        reset = Color.RESET if use_color else ''
        r,g,b = rgb565_to_rgb(state.bg)
        core = f" BG Color: {bold}RGB({r:3d},{g:3d},{b:3d}){reset} 0x{state.bg:04X}"
        vis_len = _col_of_index(core, len(core))
        padding = max(0, width - vis_len)
        return [f"{cyan}║{reset}{core}{' ' * padding}{cyan}║{reset}"]

class DisplayWidget(Widget):
    def render(self, ctx: RenderContext) -> List[str]:
        state = ctx.state
        use_color = ctx.use_color
        use_unicode = ctx.use_unicode
        width = ctx.width
        height = ctx.height
        cyan = Color.CYAN if use_color else ''
        reset = Color.RESET if use_color else ''
        bold = Color.BOLD if use_color else ''
        black = Color.BLACK if use_color else ''
        bg_color = get_ansi_color(state.bg) if use_color else ''
        scene_names = ["HOME", "SETTINGS", "CUSTOM"]
        scene_name = scene_names[state.scene % 3]
        lines: List[str] = []
        for y in range(height):
            line = f"{cyan}║{reset}{bg_color}"
            if y == 2:
                text = f"  {scene_name}  "
                line += f"{bold}{black}{text}{reset}{bg_color}"
                line += ' ' * (width - len(scene_name) - 4)
            elif y == 5:
                bar_width = width - 4
                filled = state.t % bar_width
                lb, rb = '[', ']'
                full = '█' if use_unicode else '#'
                empty = '░' if use_unicode else '.'
                line += f"{black}  {lb}{reset}{bg_color}"
                line += (f"{bold}{black}{full}{reset}{bg_color}" * filled)
                line += (f"{Color.DIM if use_color else ''}{black}{empty}{reset}{bg_color}" * (bar_width - filled))
                line += f"{black}{rb}{reset}{bg_color} "
            elif y == 8:
                status = f"  Frame: {ctx.frame_num}"
                line += f"{black}{status}{reset}{bg_color}"
                line += ' ' * (width - len(status))
            else:
                line += ' ' * width
            line += f"{reset}{cyan}║{reset}"
            lines.append(line)
        return lines

class ButtonsWidget(Widget):
    def render(self, ctx: RenderContext) -> List[str]:
        use_color = ctx.use_color
        use_unicode = ctx.use_unicode
        width = ctx.width
        state = ctx.state
        cyan = Color.CYAN if use_color else ''
        reset = Color.RESET if use_color else ''
        dim = Color.DIM if use_color else ''
        green = Color.GREEN if use_color else ''
        bold = Color.BOLD if use_color else ''
        dot_full = '●' if use_unicode else '*'
        dot_empty = '○' if use_unicode else '-'
        btn_a = f"{green}[{dot_full}]{reset}" if state.btnA else f"{dim}[{dot_empty}]{reset}"
        btn_b = f"{green}[{dot_full}]{reset}" if state.btnB else f"{dim}[{dot_empty}]{reset}"
        btn_c = f"{green}[{dot_full}]{reset}" if state.btnC else f"{dim}[{dot_empty}]{reset}"
        core = f" Buttons: A:{bold}{btn_a}  B:{bold}{btn_b}  C:{bold}{btn_c}"
        vis_len = _col_of_index(core, len(core))
        padding = max(0, width - vis_len)
        return [f"{cyan}║{reset}{core}{' ' * padding}{cyan}║{reset}"]

class HelpWidget(Widget):
    def render(self, ctx: RenderContext) -> List[str]:
        use_color = ctx.use_color
        width = ctx.width
        cyan = Color.CYAN if use_color else ''
        reset = Color.RESET if use_color else ''
        dim = Color.DIM if use_color else ''
        lines: List[str] = []
        line1 = f"{cyan}║{reset}{dim} Controls: [A] Button A  [B] Button B  [C] Button C  [Q] Quit"
        vis1 = _col_of_index(line1, len(line1))
        lines.append(f"{line1}{' ' * max(0, width - vis1 + 1)}{reset}{cyan}║{reset}")
        line2 = f"{cyan}║{dim}           [R] Red  [G] Green  [Y] Yellow  [W] White  [K] Black"
        vis2 = _col_of_index(line2, len(line2))
        lines.append(f"{line2}{' ' * max(0, width - vis2 + 1)}{reset}{cyan}║{reset}")
        return lines

class TimingFooterWidget(Widget):
    def render(self, ctx: RenderContext) -> List[str]:
        use_color = ctx.use_color
        width = ctx.width
        cyan = Color.CYAN if use_color else ''
        reset = Color.RESET if use_color else ''
        cm = f"{ctx.compute_ms:4.1f}ms"
        sm = f"{ctx.sleep_ms:4.1f}ms"
        up = f"{ctx.util*100:3.0f}%"
        status = f" compute {cm}  sleep {sm}  util {up}"
        line = f"{cyan}║{reset} Status:{status}"
        vis_len = _col_of_index(line, len(line))
        pad = max(0, width - vis_len + 1)
        return [f"{line}{' ' * pad}{cyan}║{reset}"]

class BottomBorderWidget(Widget):
    def render(self, ctx: RenderContext) -> List[str]:
        use_unicode = ctx.use_unicode
        use_color = ctx.use_color
        width = ctx.width
        if use_unicode:
            bl,br,hv = '╚','╝','═'
        else:
            bl,br,hv = '+','+','-'
        cyan = Color.CYAN if use_color else ''
        reset = Color.RESET if use_color else ''
        return [f"{cyan}{bl}{hv * width}{br}{reset}"]

class HUDWidget(Widget):
    """Mini HUD with FPS and timings"""
    def render(self, ctx: RenderContext) -> List[str]:
        use_color = ctx.use_color
        yellow = Color.YELLOW if use_color else ''
        reset = Color.RESET if use_color else ''
        src = ctx.input_src or 'kbd'
        msg = f" HUD  FPS:{ctx.fps:5.1f}  compute:{ctx.compute_ms:4.1f}ms  sleep:{ctx.sleep_ms:4.1f}ms  util:{ctx.util*100:3.0f}%  in:{src} "
        line = f"{yellow}{msg:{' '}<{ctx.width+2}}{reset}"
        return [line]

# --- Simple file logger ---
def log_error(message: str) -> None:
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "simulator.log")
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f"[{ts}] ERROR: {message}\n")
    except Exception:
        pass

# --- RPC server (TCP, line-delimited JSON) ---

def _rpc_client_loop(conn: socket.socket, addr: Tuple[str, int], evq: queue.Queue[Event]) -> None:
    try:
        with conn:
            buf = b""
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    decoded = ""
                    try:
                        decoded = line.decode('utf-8', errors='ignore')
                        msg = json.loads(decoded)

                        # JSON-RPC get_state support (for StateInspector):
                        # {"jsonrpc":"2.0","method":"get_state","id":1}
                        if isinstance(msg, dict) and str(msg.get("method", "")).lower() == "get_state":
                            response = {
                                "jsonrpc": "2.0",
                                "id": msg.get("id"),
                                "result": get_state_snapshot(),
                            }
                            try:
                                conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
                            except Exception as send_err:
                                log_error(f"RPC get_state send failed: {send_err}")
                            continue

                        # Expected shapes for command-style RPC:
                        # {"method":"set_bg","rgb":[r,g,b]} or {"rgb565":4660}
                        # {"method":"btn","id":"A|B|C","pressed":true}
                        # {"method":"scene","value":0}
                        evq.put({"type":"rpc","data":msg})
                    except Exception as e:
                        log_error(f"Bad RPC JSON: {decoded!r} err: {e}")
    except Exception as e:
        log_error(f"RPC client loop error: {e}")


def start_rpc_server(port: int, evq: queue.Queue[Event]) -> Optional[threading.Thread]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        sock.listen(5)
    except Exception as e:
        log_error(f"RPC bind {port} failed: {e}")
        return None

    def _server(s: socket.socket) -> None:
        try:
            while True:
                conn, addr = s.accept()
                t = threading.Thread(target=_rpc_client_loop, args=(conn, addr, evq), daemon=True)
                t.start()
        except Exception as e:
            log_error(f"RPC server error: {e}")
        finally:
            try:
                s.close()
            except Exception:
                pass

    th = threading.Thread(target=_server, args=(sock,), daemon=True)
    th.start()
    return th


def apply_rpc_message(state: UIState, msg: Dict[str, Any]) -> None:
    meth = str(msg.get("method", "")).lower()
    if meth == "set_bg":
        rgb_val = msg.get("rgb")
        if isinstance(rgb_val, (list, tuple)):
            rgb_seq = cast(Iterable[int | float | str], rgb_val)
            rgb_list: List[int] = [int(v) for v in rgb_seq]
            if len(rgb_list) == 3:
                r_int, g_int, b_int = rgb_list
                state.bg = rgb565(r_int, g_int, b_int)
        elif "rgb565" in msg:
            try:
                state.bg = int(msg["rgb565"]) & 0xFFFF
            except Exception:
                pass
    elif meth == "btn":
        bid = str(msg.get("id", "")).upper()
        pressed = bool(msg.get("pressed", False))
        if bid == 'A':
            state.btnA = pressed
            if pressed:
                state.scene = (state.scene + 1) % 3
        elif bid == 'B':
            state.btnB = pressed
        elif bid == 'C':
            state.btnC = pressed
    elif meth == "scene":
        try:
            v = int(msg.get("value", 0))
            state.scene = max(0, min(2, v))
        except Exception:
            pass

# --- UART-like text server (parity with firmware: "set_bg <hex>") ---

def _uart_client_loop(conn: socket.socket, addr: Tuple[str, int], evq: queue.Queue[Event]) -> None:
    try:
        with conn:
            buf = b""
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip().decode('utf-8', errors='ignore')
                    if not line:
                        continue
                    evq.put({"type":"uart","line": line})
    except Exception as e:
        log_error(f"UART client loop error: {e}")


def start_uart_server(port: int, evq: queue.Queue[Event]) -> Optional[threading.Thread]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        sock.listen(5)
    except Exception as e:
        log_error(f"UART bind {port} failed: {e}")
        return None

    def _server(s: socket.socket) -> None:
        try:
            while True:
                conn, addr = s.accept()
                t = threading.Thread(target=_uart_client_loop, args=(conn, addr, evq), daemon=True)
                t.start()
        except Exception as e:
            log_error(f"UART server error: {e}")
        finally:
            try:
                s.close()
            except Exception:
                pass

    th = threading.Thread(target=_server, args=(sock,), daemon=True)
    th.start()
    return th

# --- Optional COM-port bridge (pyserial) ---

def _com_bridge_loop(port_name: str, baud: int, evq: queue.Queue[Event]) -> None:
    try:
        import serial  # type: ignore
    except Exception as e:
        log_error(f"pyserial not available for COM bridge: {e}")
        return
    try:
        ser = serial.Serial(port=port_name, baudrate=baud, timeout=0.1)
    except Exception as e:
        log_error(f"COM open failed for {port_name} @ {baud}: {e}")
        return
    try:
        with ser:
            while True:
                try:
                    line = ser.readline()
                    if not line:
                        continue
                    sline = line.decode('utf-8', errors='ignore').strip()
                    if sline:
                        evq.put({"type":"uart", "line": sline})
                except Exception as ie:
                    log_error(f"COM read error: {ie}")
                    time.sleep(0.2)
    except Exception as e:
        log_error(f"COM loop error: {e}")

def start_com_bridge(port_name: str, baud: int, evq: queue.Queue[Event]) -> Optional[threading.Thread]:
    try:
        import serial  # type: ignore
    except Exception:
        print("pyserial not installed. Install with: pip install pyserial", file=sys.stderr)
        return None
    th = threading.Thread(target=_com_bridge_loop, args=(port_name, baud, evq), daemon=True)
    th.start()
    return th

# --- WebSocket server for remote UI viewing ---

def start_websocket_server(port: int, frame_callback: Callable[[], Dict[str, Any]]) -> Optional[threading.Thread]:
    """Start WebSocket server for remote UI streaming (requires websockets library)"""
    try:
        import asyncio
        import websockets  # type: ignore
    except Exception:
        print("websockets not installed. Install with: pip install websockets", file=sys.stderr)
        return None
    
    clients: Set[Any] = set()
    
    async def handler(websocket: Any, path: str) -> None:
        clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            clients.discard(websocket)
    
    async def broadcast_frames():
        while True:
            await asyncio.sleep(0.033)  # ~30 FPS broadcast
            frame_data = frame_callback()
            if frame_data and clients:
                message = json.dumps(frame_data)
                await asyncio.gather(*[client.send(message) for client in clients], return_exceptions=True)
    
    async def main_server():
        async with websockets.serve(handler, "127.0.0.1", port):  # type: ignore[arg-type]
            await broadcast_frames()
    
    def run_loop():
        asyncio.run(main_server())
    
    th = threading.Thread(target=run_loop, daemon=True)
    th.start()
    return th

# --- Metrics export to CSV ---

class MetricsRecorder:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data: List[Dict[str, Any]] = []
    
    def record(self, frame: int, fps: float, compute_ms: float, sleep_ms: float, util: float):
        self.data.append({
            'frame': frame,
            'fps': fps,
            'compute_ms': compute_ms,
            'sleep_ms': sleep_ms,
            'util': util,
            'timestamp': time.time()
        })
    
    def export(self):
        try:
            import csv
            with open(self.filepath, 'w', newline='', encoding='utf-8') as f:
                if self.data:
                    writer = csv.DictWriter(f, fieldnames=self.data[0].keys())
                    writer.writeheader()
                    writer.writerows(self.data)
        except Exception as e:
            log_error(f"Failed to export metrics: {e}")

# --- Session recording and playback ---

class SessionRecorder:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.events: List[Dict[str, Any]] = []
        self.start_time = time.time()
    
    def record_event(self, event_type: str, data: Mapping[str, Any] | Event):
        elapsed_ms = int((time.time() - self.start_time) * 1000)
        self.events.append({
            'at_ms': elapsed_ms,
            'type': event_type,
            'data': data
        })
    
    def save(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.events, f, indent=2)
        except Exception as e:
            log_error(f"Failed to save recording: {e}")

def load_playback(filepath: str) -> List[Dict[str, Any]]:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            events_raw = json.load(f)
            events: List[Dict[str, Any]] = cast(List[Dict[str, Any]], events_raw if isinstance(events_raw, list) else [])
            events.sort(key=lambda e: int(e.get('at_ms', 0)))
            return events
    except Exception as e:
        log_error(f"Failed to load playback: {e}")
        return []

def rgb565(r: int, g: int, b: int) -> int:
    """Convert RGB888 to RGB565"""
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def rgb565_to_rgb(color: int) -> Tuple[int, int, int]:
    """Convert RGB565 to RGB888"""
    r = ((color >> 11) & 0x1F) << 3
    g = ((color >> 5) & 0x3F) << 2
    b = (color & 0x1F) << 3
    return r, g, b

def get_ansi_color(rgb565_color: int) -> str:
    """Map RGB565 to closest ANSI background color"""
    r, g, b = rgb565_to_rgb(rgb565_color)
    avg = (r + g + b) // 3
    
    if avg < 32:
        return Color.BG_BLACK
    if r > 200 and g < 100 and b < 100:
        return Color.BG_RED
    if r < 100 and g > 200 and b < 100:
        return Color.BG_GREEN
    if r > 200 and g > 200 and b < 100:
        return Color.BG_YELLOW
    if r < 100 and g < 100 and b > 200:
        return Color.BG_BLUE
    if r > 200 and g < 100 and b > 200:
        return Color.BG_MAGENTA
    if r < 100 and g > 200 and b > 200:
        return Color.BG_CYAN
    if avg > 180:
        return Color.BG_WHITE
    
    return Color.BG_BLACK

def clear_screen() -> None:
    """Clear terminal screen"""
    # Use faster direct escape without flush
    sys.stdout.write("\033[2J\033[H")

def enable_ansi_colors() -> None:
    """Enable ANSI colors on Windows using SetConsoleMode; no-op elsewhere."""
    if platform.system() == 'Windows':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            STD_OUTPUT_HANDLE = -11
            handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            mode = ctypes.c_uint()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                DISABLE_NEWLINE_AUTO_RETURN = 0x0008
                new_mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING | DISABLE_NEWLINE_AUTO_RETURN
                kernel32.SetConsoleMode(handle, new_mode)
        except Exception:
            # Fallback: best-effort no-op
            pass

def get_key_nonblocking() -> Optional[str]:
    """Get keyboard input without blocking (platform-specific)"""
    if platform.system() == 'Windows':
        import msvcrt
        if msvcrt.kbhit():
            return msvcrt.getch().decode('utf-8', errors='ignore').lower()
    else:
        import select
        import termios  # type: ignore
        import tty  # type: ignore
        
        old_settings = termios.tcgetattr(sys.stdin)  # type: ignore[attr-defined]
        try:
            tty.setcbreak(sys.stdin.fileno())  # type: ignore[attr-defined]
            if select.select([sys.stdin], [], [], 0)[0]:
                return sys.stdin.read(1).lower()
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)  # type: ignore[attr-defined]
    return None

def render_frame(state: UIState, frame_num: int, fps: float, width: int = 100, height: int = 24,
                 use_unicode: bool = True, use_color: bool = True,
                 compute_ms: float = 0.0, sleep_ms: float = 0.0, util: float = 0.0,
                 hud: bool = False,
                 input_src: str = "") -> List[str]:
    """Render one frame using widget composition and return list of ANSI lines."""
    ctx = RenderContext(
        state=state,
        frame_num=frame_num,
        fps=fps,
        width=width,
        height=height,
        use_unicode=use_unicode,
        use_color=use_color,
        compute_ms=compute_ms,
        sleep_ms=sleep_ms,
        util=util,
        input_src=input_src,
    )
    widgets: List[Widget] = [
        TitleBarWidget(),
    ]
    if hud:
        widgets.append(HUDWidget())
    widgets += [
        DividerWidget(),
        SceneStatusWidget(),
        ColorInfoWidget(),
        DividerWidget(),
        DisplayWidget(),
        DividerWidget(),
        ButtonsWidget(),
        TimingFooterWidget(),
        DividerWidget(),
        HelpWidget(),
        BottomBorderWidget(),
    ]
    output: List[str] = []
    for w in widgets:
        output.extend(w.render(ctx))
    return output

def _find_footer_index(lines: List[str]) -> int:
    """Find the index of the status footer line by content; return -1 if not found."""
    try:
        for i in range(len(lines) - 1, -1, -1):
            if " Status:" in lines[i]:
                return i
    except Exception:
        pass
    return -1

_RESET_RE = re.compile(r'(?:\x1b\[0m)+')
_REDUNDANT_RE = re.compile(r'\x1b\[0m(\x1b\[[0-9;]*m)')

def optimize_ansi(line: str) -> str:
    """Prune redundant ANSI reset sequences for efficiency without altering appearance."""
    # Collapse multiple consecutive resets
    line = _RESET_RE.sub('\x1b[0m', line)
    # Remove a reset immediately followed by a style/color change
    line = _REDUNDANT_RE.sub(r'\1', line)
    return line

def main() -> None:
    """Main simulator loop"""
    enable_ansi_colors()
    
    parser = argparse.ArgumentParser(description='ESP32 UI Simulator')
    parser.add_argument('--fps', type=int, default=120, help='Target FPS')
    parser.add_argument('--width', type=int, default=100, help='Display width (characters)')
    parser.add_argument('--height', type=int, default=24, help='Display height (rows)')
    parser.add_argument('--no-color', action='store_true', help='Disable ANSI colors')
    parser.add_argument('--no-unicode', action='store_true', help='Disable Unicode border/elements')
    parser.add_argument('--rpc-port', type=int, default=0, help='Enable TCP RPC on given port (0=disabled)')
    parser.add_argument('--uart-port', type=int, default=0, help='Enable UART-like text TCP on given port (0=disabled)')
    parser.add_argument('--script', type=str, default='', help='Path to JSON event script')
    parser.add_argument('--com-port', type=str, default='', help='Enable COM-port bridge (e.g., COM3)')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate for COM bridge')
    parser.add_argument('--full-redraw-interval', type=int, default=300, help='Periodic full redraw interval (frames, 0=disable)')
    parser.add_argument('--no-diff', action='store_true', help='Disable substring diff rendering (debug full redraw)')
    parser.add_argument('--config', type=str, default='', help='Load configuration from JSON file')
    parser.add_argument('--export-metrics', type=str, default='', help='Export timing metrics to CSV file')
    parser.add_argument('--websocket-port', type=int, default=0, help='Enable WebSocket server for remote viewer (0=disabled)')
    parser.add_argument('--record', type=str, default='', help='Record session to file')
    parser.add_argument('--playback', type=str, default='', help='Playback recorded session from file')
    parser.add_argument('--auto-size', action='store_true', help='Auto-detect terminal size and adjust UI')
    parser.add_argument('--gamepad', action='store_true', help='Enable pygame-based gamepad input (maps buttons to A/B/C)')
    parser.add_argument('--input-overlay', action='store_true', help='Show small pygame window with clickable A/B/C buttons')
    args = parser.parse_args()

    # Detect optional pygame for input hints (no hard import)
    _has_pygame = pygame is not None
    if not _has_pygame:
        try:
            import importlib.util as _ils  # type: ignore
            _spec = _ils.find_spec('pygame')
            _has_pygame = _spec is not None
        except Exception:
            _has_pygame = False
    
    # Load config file if provided
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Override args with config values (args take precedence if explicitly set)
                for key, value in config.items():
                    attr_name = key.replace('-', '_')
                    if hasattr(args, attr_name) and getattr(args, attr_name) == parser.get_default(key.replace('_', '-')):
                        setattr(args, attr_name, value)
        except Exception as e:
            log_error(f"Failed to load config {args.config}: {e}")
    
    # Auto-detect terminal size if requested
    if args.auto_size:
        try:
            if platform.system() == 'Windows':
                import ctypes
                import ctypes.wintypes

                kernel32 = ctypes.windll.kernel32
                COORD = ctypes.wintypes._COORD  # type: ignore[attr-defined]
                WORD = ctypes.wintypes.WORD
                STD_OUTPUT_HANDLE = -11
                handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

                class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
                    _fields_ = [
                        ("dwSize", COORD),
                        ("dwCursorPosition", COORD),
                        ("wAttributes", WORD),
                        ("srWindow", ctypes.wintypes.SMALL_RECT),
                        ("dwMaximumWindowSize", COORD),
                    ]

                csbi = CONSOLE_SCREEN_BUFFER_INFO()
                if kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(csbi)):
                    term_width = csbi.srWindow.Right - csbi.srWindow.Left + 1
                    term_height = csbi.srWindow.Bottom - csbi.srWindow.Top + 1
                    # Leave margins for borders
                    args.width = max(40, min(term_width - 4, 120))
                    args.height = max(16, min(term_height - 6, 40))
            else:
                import shutil
                term_size = shutil.get_terminal_size((80, 24))
                args.width = max(40, min(term_size.columns - 4, 120))
                args.height = max(16, min(term_size.lines - 6, 40))
        except Exception as e:
            log_error(f"Auto-size detection failed: {e}")

    evq: queue.Queue[Event] = queue.Queue()
    rpc_th = None
    uart_th = None
    com_th = None
    if args.rpc_port > 0:
        rpc_th = start_rpc_server(args.rpc_port, evq)
        if rpc_th is None:
            msg = f"RPC port {args.rpc_port} is busy or cannot bind."
            log_error(msg)
            print(msg, file=sys.stderr)
            return
    if args.uart_port > 0:
        uart_th = start_uart_server(args.uart_port, evq)
        if uart_th is None:
            msg = f"UART-text port {args.uart_port} is busy or cannot bind."
            log_error(msg)
            print(msg, file=sys.stderr)
            return
    # Optional COM bridge
    if args.com_port:
        com_th = start_com_bridge(args.com_port, args.baud, evq)

    # Initialize optional features
    metrics_recorder = None
    if args.export_metrics:
        metrics_recorder = MetricsRecorder(args.export_metrics)
    
    session_recorder = None
    if args.record:
        session_recorder = SessionRecorder(args.record)
    
    playback_events: List[Dict[str, Any]] = []
    if args.playback:
        playback_events = load_playback(args.playback)
    
    ws_server = None
    current_frame_data: Dict[str, Any] = {}
    
    def get_frame_data():
        return current_frame_data.copy()
    
    if args.websocket_port > 0:
        ws_server = start_websocket_server(args.websocket_port, get_frame_data)
        if ws_server:
            print(f"{Color.DIM}WebSocket: 127.0.0.1:{args.websocket_port}{Color.RESET}")
        else:
            print(f"{Color.DIM}WebSocket disabled (install: pip install websockets){Color.RESET}")

    state = UIState()
    frame = 0
    running = True
    auto_demo = False
    hud_enabled = False
    
    start_time = time.time()
    last_frame_time = start_time
    fps = 0.0
    current_input_src = 'kbd'

    # Initialize state snapshot so RPC get_state has data immediately
    try:
        _update_state_snapshot(
            state=state,
            frame=frame,
            fps=fps,
            event_queue_size=evq.qsize(),
            render_time_ms=0.0,
            input_src=current_input_src,
        )
    except Exception:
        pass
    
    # Write ports discovery file for tools (deleted on exit)
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        ports_path = os.path.join(base, "sim_ports.json")
        ports_info: Dict[str, Optional[int]] = {
            "rpc_port": int(args.rpc_port) if args.rpc_port else None,
            "uart_port": int(args.uart_port) if args.uart_port else None,
            "com_port": args.com_port or None,
            "pid": os.getpid(),
            "ts": int(time.time())
        }
        with open(ports_path, 'w', encoding='utf-8') as f:
            json.dump(ports_info, f)

        def _cleanup_ports_file():
            try:
                if os.path.exists(ports_path):
                    os.remove(ports_path)
            except Exception:
                pass

        atexit.register(_cleanup_ports_file)
    except Exception as e:
        log_error(f"Failed to write sim_ports.json: {e}")

    # Optional input thread (pygame overlay / gamepad)
    input_state = {'A': False, 'B': False, 'C': False}
    input_source = {'src': 'kbd'}
    input_lock = threading.Lock()
    stop_input = threading.Event()

    def start_input_thread(enable_overlay: bool, enable_gamepad: bool):
        if pygame is None:
            print(f"{Color.DIM}Input: pygame not installed (pip install pygame) — skipping input overlay/gamepad{Color.RESET}")
            return None

        def _thread():
            try:
                pygame.init()
                screen = None
                btn_rects = {}
                if enable_overlay:
                    screen = pygame.display.set_mode((260, 110))
                    pygame.display.set_caption('ESP32OS Input Overlay')
                    font = pygame.font.SysFont(None, 24)
                    def _layout(w: int, h: int) -> Dict[str, Any]:
                        m, pad = 10, 10
                        bw, bh = 70, 60
                        ax = m; bx = m + bw + pad; cx = m + 2*(bw + pad)
                        y = (h - bh)//2
                        return {
                            'A': pygame.Rect(ax, y, bw, bh),
                            'B': pygame.Rect(bx, y, bw, bh),
                            'C': pygame.Rect(cx, y, bw, bh),
                        }
                    btn_rects = _layout(260, 110)
                # Gamepad
                have_gp = False
                try:
                    pygame.joystick.init()
                    if pygame.joystick.get_count() > 0:
                        gp = pygame.joystick.Joystick(0)
                        gp.init()
                        have_gp = True
                except Exception:
                    have_gp = False

                clock = pygame.time.Clock()
                running_local = True
                while running_local and not stop_input.is_set():
                    for event in pygame.event.get():
                        if event.type == getattr(pygame, 'QUIT', None):
                            running_local = False
                            break
                        if enable_overlay and screen is not None:
                            if event.type == getattr(pygame, 'MOUSEBUTTONDOWN', None):
                                pos = getattr(event, "pos", (0, 0))
                                x, y = int(pos[0]), int(pos[1])
                                for k, r in btn_rects.items():
                                    if r.collidepoint(x, y):
                                        with input_lock:
                                            input_state[k] = True
                                            input_source['src'] = 'overlay'
                            elif event.type == getattr(pygame, 'MOUSEBUTTONUP', None):
                                with input_lock:
                                    for k in input_state:
                                        input_state[k] = False
                        if enable_gamepad and have_gp:
                            if event.type == getattr(pygame, 'JOYBUTTONDOWN', None):
                                # Map 0,1,2 -> A,B,C
                                b = getattr(event, 'button', -1)
                                if b in (0,1,2):
                                    with input_lock:
                                        input_state['ABC'[b]] = True
                                        input_source['src'] = 'gamepad'
                            elif event.type == getattr(pygame, 'JOYBUTTONUP', None):
                                b = getattr(event, 'button', -1)
                                if b in (0,1,2):
                                    with input_lock:
                                        input_state['ABC'[b]] = False
                    if enable_overlay and screen is not None:
                        screen.fill((20,20,24))
                        for k, r in btn_rects.items():
                            with input_lock:
                                pressed = input_state[k]
                            col = (47,129,247) if pressed else (40,45,60)
                            pygame.draw.rect(screen, col, r, border_radius=8)
                            pygame.draw.rect(screen, (90,100,120), r, 2, border_radius=8)
                            # Label
                            try:
                                font = pygame.font.SysFont(None, 28)
                                img = font.render(k, True, (230,237,243))
                                screen.blit(img, (r.x + (r.w - img.get_width())//2, r.y + (r.h - img.get_height())//2))
                            except Exception:
                                pass
                        pygame.display.flip()
                    clock.tick(60)
            except Exception as e:
                try:
                    print(f"{Color.DIM}Input thread error: {e}{Color.RESET}")
                except Exception:
                    pass
            finally:
                try:
                    if pygame is not None:
                        pygame.quit()
                except Exception:
                    pass
        th = threading.Thread(target=_thread, daemon=True)
        th.start()
        return th

    input_th = None
    if args.gamepad or args.input_overlay:
        input_th = start_input_thread(args.input_overlay, args.gamepad)

    # Print startup info briefly, then clear and start rendering
    print(f"{Color.BOLD}{Color.GREEN}\n=== ESP32 UI SIMULATOR STARTED ==={Color.RESET}")
    if rpc_th is not None:
        print(f"{Color.DIM}RPC: 127.0.0.1:{args.rpc_port}{Color.RESET}")
    if uart_th is not None:
        print(f"{Color.DIM}UART: 127.0.0.1:{args.uart_port}{Color.RESET}")
    if com_th is not None:
        print(f"{Color.DIM}COM: {args.com_port} @ {args.baud}{Color.RESET}")
    if args.websocket_port:
        print(f"{Color.DIM}Remote Viewer: open web/remote_viewer.html?port={args.websocket_port}{Color.RESET}")
    controls = "Q quit | D demo | H HUD | M metrics CSV | E export HTML"
    if args.gamepad:
        controls += " | GAMEPAD 0/1/2 → A/B/C"
    if args.input_overlay:
        controls += " | Mouse overlay window for A/B/C"
    print(f"{Color.DIM}Controls: {controls}{Color.RESET}")
    if _has_pygame and not (args.gamepad or args.input_overlay):
        print(f"{Color.DIM}Tip: pygame detected — enable --gamepad or --input-overlay for A/B/C input{Color.RESET}")
    time.sleep(0.8)
    
    try:
        # Ensure terminal scrolled to bottom, then clear and hide cursor
        print("\n" * 5)  # Push any content up
        sys.stdout.write("\033[2J\033[H\033[?25l")
        sys.stdout.flush()

        prev_lines: List[str] = []

        # Load script if provided
        script_events: List[Dict[str, Any]] = []
        next_event_idx = 0
        run_start = time.time()
        
        # Prefer playback over script
        if playback_events:
            script_events = playback_events
        elif args.script:
            try:
                with open(args.script, 'r', encoding='utf-8') as f:
                    script_events = json.load(f) or []
                script_events.sort(key=lambda e: int(e.get('at_ms', 0)))
            except Exception as e:
                log_error(f"Failed to load script {args.script}: {e}")
                script_events = []

        # Metrics from previous frame used in footer of current frame
        compute_ms_prev = 0.0
        sleep_ms_prev = 0.0
        util_prev = 0.0
        footer_index_cached = None
        full_redraw = True  # force full redraw first frame
        FULL_REDRAW_INTERVAL = max(0, int(args.full_redraw_interval))
        diff_enabled = not args.no_diff

        while running:
            frame_start = time.time()
            elapsed = frame_start - last_frame_time
            if elapsed > 0:
                fps = (fps * 0.8) + (min(1.0 / elapsed, args.fps * 1.5) * 0.2)
            last_frame_time = frame_start
            state.t += 1
            
            # Check for keyboard input
            key = get_key_nonblocking()
            if key:
                if session_recorder:
                    session_recorder.record_event('key', {'key': key})
                if key == 'q':
                    running = False
                elif key == 'a':
                    state.btnA = not state.btnA
                    if state.btnA:
                        state.scene = (state.scene + 1) % 3
                    current_input_src = 'kbd'
                elif key == 'b':
                    state.btnB = not state.btnB
                    current_input_src = 'kbd'
                elif key == 'c':
                    state.btnC = not state.btnC
                    current_input_src = 'kbd'
                elif key == 'r':
                    state.bg = rgb565(255, 0, 0)
                elif key == 'g':
                    state.bg = rgb565(0, 255, 0)
                elif key == 'y':
                    state.bg = rgb565(255, 255, 0)
                elif key == 'w':
                    state.bg = rgb565(255, 255, 255)
                elif key == 'k':
                    state.bg = rgb565(0, 0, 0)
                elif key == 'd':
                    auto_demo = not auto_demo
                elif key == 'h':
                    hud_enabled = not hud_enabled
                elif key == 'm':
                    if not metrics_recorder:
                        base = os.path.dirname(os.path.abspath(__file__))
                        out_dir = os.path.join(base, 'examples')
                        os.makedirs(out_dir, exist_ok=True)
                        csv_path = os.path.join(out_dir, 'sim_metrics.csv')
                        metrics_recorder = MetricsRecorder(csv_path)
                        print(f"{Color.DIM}Metrics recording: ON → {csv_path}{Color.RESET}")
                    else:
                        metrics_recorder.export()
                        print(f"{Color.DIM}Metrics exported to {metrics_recorder.filepath}{Color.RESET}")
                elif key == 'e':
                    if metrics_recorder and metrics_recorder.data:
                        html_path = metrics_recorder.filepath.replace('.csv', '.html')
                        try:
                            with open(html_path, 'w', encoding='utf-8') as f:
                                f.write('<!DOCTYPE html><meta charset="utf-8"><title>Simulator Metrics</title>')
                                f.write('<style>body{font-family:Arial}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px}</style>')
                                f.write('<h1>Simulator Metrics</h1><table><tr><th>frame</th><th>fps</th><th>compute_ms</th><th>sleep_ms</th><th>util</th></tr>')
                                for row in metrics_recorder.data:
                                    f.write(f"<tr><td>{row['frame']}</td><td>{row['fps']:.1f}</td><td>{row['compute_ms']:.2f}</td><td>{row['sleep_ms']:.2f}</td><td>{row['util']:.2f}</td></tr>")
                                f.write('</table>')
                            print(f"{Color.DIM}HTML exported: {html_path}{Color.RESET}")
                        except Exception as _e:
                            print(f"{Color.DIM}HTML export failed: {_e}{Color.RESET}")
            
            # Apply queued events (RPC/ UART)
            try:
                while True:
                    ev = evq.get_nowait()
                    if session_recorder:
                        session_recorder.record_event('network', ev)
                    et = ev.get('type')
                    if et == 'rpc':
                        apply_rpc_message(state, ev.get('data', {}))
                    elif et == 'uart':
                        line = str(ev.get('line',''))
                        if line.startswith('set_bg '):
                            try:
                                val = int(line.split()[1], 16)
                                apply_rpc_message(state, {"method":"set_bg", "rgb565": val})
                            except Exception:
                                pass
            except queue.Empty:
                pass

            # Scripted/playback events
            if script_events:
                elapsed_ms = int((time.time() - run_start) * 1000)
                while next_event_idx < len(script_events) and int(script_events[next_event_idx].get('at_ms', 0)) <= elapsed_ms:
                    evt = script_events[next_event_idx]
                    evt_type = evt.get('type', '')
                    if evt_type == 'key':
                        # Simulate key press from playback
                        pass  # Would need to inject into state directly
                    elif evt_type == 'network':
                        evt_data = evt.get('data', {})
                        if evt_data.get('type') == 'rpc':
                            apply_rpc_message(state, evt_data.get('data', {}))
                    else:
                        # Legacy script format
                        apply_rpc_message(state, evt)
                    next_event_idx += 1

            # Auto demo
            if auto_demo:
                if frame == 30:
                    state.btnA = True
                    state.scene = 1
                if frame == 35:
                    state.btnA = False
                if frame == 50:
                    state.bg = rgb565(255, 0, 0)
                if frame == 80:
                    state.bg = rgb565(0, 160, 64)
                if frame == 110:
                    state.bg = rgb565(64, 128, 255)
                if frame == 140:
                    state.bg = rgb565(255, 192, 0)
                if frame == 170:
                    state.btnB = True
                if frame == 175:
                    state.btnB = False
                if frame >= 200:
                    frame = 0
                    state.scene = 0
                    state.bg = rgb565(8, 8, 8)
            
            # Apply input state from overlay/gamepad (if enabled)
            if input_th is not None:
                with input_lock:
                    state.btnA = bool(input_state['A'])
                    state.btnB = bool(input_state['B'])
                    state.btnC = bool(input_state['C'])
                    current_input_src = input_source.get('src', 'kbd')

            # Render frame using previous timing metrics
            lines = render_frame(state, frame, fps, width=args.width, height=args.height,
                                 use_unicode=(not args.no_unicode), use_color=(not args.no_color),
                                 compute_ms=compute_ms_prev, sleep_ms=sleep_ms_prev, util=util_prev,
                                 hud=hud_enabled,
                                 input_src=current_input_src)

            # Cache footer index once
            if footer_index_cached is None:
                footer_index_cached = _find_footer_index(lines)

            # Diff-based redraw (tail substring) or full redraw first frame
            for i, raw_line in enumerate(lines):
                line = optimize_ansi(raw_line)
                if full_redraw or not diff_enabled:
                    sys.stdout.write(f"\033[{i+1};1H")
                    sys.stdout.write(line)
                    continue
                changed = i >= len(prev_lines) or line != prev_lines[i]
                if not changed:
                    continue
                prev_line = prev_lines[i] if i < len(prev_lines) else ''
                if not prev_line:
                    sys.stdout.write(f"\033[{i+1};1H")
                    sys.stdout.write(line)
                    continue
                # Substring diff tail update
                _, curr_idx = _first_diff_visual(prev_line, line)
                col = _col_of_index(line, curr_idx)
                if col < 0 or col > len(line):
                    col = 0
                    curr_idx = 0
                sys.stdout.write(f"\033[{i+1};{col+1}H")
                sys.stdout.write(line[curr_idx:])
            prev_lines = lines
            sys.stdout.flush()
            if not diff_enabled:
                full_redraw = True
            elif FULL_REDRAW_INTERVAL > 0:
                full_redraw = (frame % FULL_REDRAW_INTERVAL == 0)
            else:
                full_redraw = False
            frame += 1

            # Timing for this frame
            frame_time = time.time() - frame_start
            target = 1.0 / max(1, args.fps)
            sleep_time = max(0.0, target - frame_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
            total = frame_time + sleep_time + 1e-6
            compute_ms_prev = frame_time * 1000.0
            sleep_ms_prev = sleep_time * 1000.0
            util_prev = frame_time / total
            
            # Record metrics
            if metrics_recorder:
                metrics_recorder.record(frame, fps, compute_ms_prev, sleep_ms_prev, util_prev)
            
            # Update WebSocket frame data
            if ws_server:
                current_frame_data = {
                    'frame': frame,
                    'fps': fps,
                    'scene': state.scene,
                    'bg': state.bg,
                    'btnA': state.btnA,
                    'btnB': state.btnB,
                    'btnC': state.btnC,
                    'tick': state.t,
                    'compute_ms': compute_ms_prev,
                    'sleep_ms': sleep_ms_prev,
                    'util': util_prev,
                    'input_src': current_input_src
                }

            # Update RPC state snapshot for get_state
            try:
                _update_state_snapshot(
                    state=state,
                    frame=frame,
                    fps=fps,
                    event_queue_size=evq.qsize(),
                    render_time_ms=compute_ms_prev,
                    input_src=current_input_src,
                )
            except Exception:
                # Snapshot is best-effort; never break render loop
                pass
            
            # Update only footer line with new metrics next loop; no second full render here
    
    except KeyboardInterrupt:
        pass
    
    # Save metrics and recording if enabled
    if metrics_recorder:
        metrics_recorder.export()
        print(f"{Color.DIM}Metrics exported to {args.export_metrics}{Color.RESET}")
    
    if session_recorder:
        session_recorder.save()
        print(f"{Color.DIM}Session recorded to {args.record}{Color.RESET}")
    
    # Stop input thread if any
    try:
        if input_th is not None:
            stop_input.set()
    except Exception:
        pass

    # Show cursor again and clear
    sys.stdout.write("\033[?25h\n")
    clear_screen()
    print(f"{Color.BOLD}{Color.YELLOW}\n=== SIMULATOR STOPPED ==={Color.RESET}")
    print(f"Total frames: {frame}")
    print(f"Total time: {time.time() - start_time:.2f} seconds")
    print(f"{Color.DIM}Goodbye!\n{Color.RESET}")

if __name__ == '__main__':
    main()
