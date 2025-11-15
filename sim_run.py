#!/usr/bin/env python3
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
from typing import Tuple, Any, List, Dict, Optional, TypedDict, Literal, Union
from datetime import datetime
from dataclasses import dataclass

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
    compute_ms: float = 0.0
    sleep_ms: float = 0.0
    util: float = 0.0

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
        use_unicode = ctx.use_unicode
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

def _rpc_client_loop(conn: socket.socket, addr: Tuple[str, int], evq: "queue.Queue[Dict[str, Any]]") -> None:
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
                    try:
                        decoded = line.decode('utf-8', errors='ignore')
                        msg = json.loads(decoded)
                        # Expected shapes:
                        # {"method":"set_bg","rgb":[r,g,b]} or {"rgb565":4660}
                        # {"method":"btn","id":"A|B|C","pressed":true}
                        # {"method":"scene","value":0}
                        evq.put({"type":"rpc","data":msg})
                    except Exception as e:
                        log_error(f"Bad RPC JSON: {decoded!r} err: {e}")
    except Exception as e:
        log_error(f"RPC client loop error: {e}")


def start_rpc_server(port: int, evq: "queue.Queue[Dict[str, Any]]") -> Optional[threading.Thread]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        sock.listen(5)
    except Exception as e:
        log_error(f"RPC bind {port} failed: {e}")
        return None

    def _server(s):
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
        if "rgb" in msg and isinstance(msg["rgb"], (list, tuple)) and len(msg["rgb"]) == 3:
            r, g, b = msg["rgb"]
            state.bg = rgb565(int(r), int(g), int(b))
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

def _uart_client_loop(conn: socket.socket, addr: Tuple[str, int], evq: "queue.Queue[Dict[str, Any]]") -> None:
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


def start_uart_server(port: int, evq: "queue.Queue[Dict[str, Any]]") -> Optional[threading.Thread]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        sock.listen(5)
    except Exception as e:
        log_error(f"UART bind {port} failed: {e}")
        return None

    def _server(s):
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

def _com_bridge_loop(port_name: str, baud: int, evq: "queue.Queue[Dict[str, Any]]") -> None:
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

def start_com_bridge(port_name: str, baud: int, evq: "queue.Queue[Dict[str, Any]]") -> Optional[threading.Thread]:
    try:
        import serial  # type: ignore
    except Exception:
        print("pyserial not installed. Install with: pip install pyserial", file=sys.stderr)
        return None
    th = threading.Thread(target=_com_bridge_loop, args=(port_name, baud, evq), daemon=True)
    th.start()
    return th

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
        import termios
        import tty
        
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            if select.select([sys.stdin], [], [], 0)[0]:
                return sys.stdin.read(1).lower()
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    return None

def render_frame(state: UIState, frame_num: int, fps: float, width: int = 100, height: int = 24,
                 use_unicode: bool = True, use_color: bool = True,
                 compute_ms: float = 0.0, sleep_ms: float = 0.0, util: float = 0.0) -> List[str]:
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
    )
    widgets = [
        TitleBarWidget(),
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
    output = []
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
    args = parser.parse_args()

    # Event queue and servers (bind before announcing)
    class RPCEvent(TypedDict):
        type: Literal['rpc']
        data: Dict[str, Any]

    class UARTEvent(TypedDict):
        type: Literal['uart']
        line: str

    Event = Union[RPCEvent, UARTEvent]

    evq: "queue.Queue[Event]" = queue.Queue()
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

    state = UIState()
    frame = 0
    running = True
    auto_demo = False
    
    start_time = time.time()
    last_frame_time = start_time
    fps = 0.0
    
    # Write ports discovery file for tools (deleted on exit)
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        ports_path = os.path.join(base, "sim_ports.json")
        ports_info = {
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

    # Print startup info briefly, then clear and start rendering
    print(f"{Color.BOLD}{Color.GREEN}\n=== ESP32 UI SIMULATOR STARTED ==={Color.RESET}")
    if rpc_th is not None:
        print(f"{Color.DIM}RPC: 127.0.0.1:{args.rpc_port}{Color.RESET}")
    if uart_th is not None:
        print(f"{Color.DIM}UART: 127.0.0.1:{args.uart_port}{Color.RESET}")
    if com_th is not None:
        print(f"{Color.DIM}COM: {args.com_port} @ {args.baud}{Color.RESET}")
    print(f"{Color.DIM}Press Q to quit, D for demo{Color.RESET}")
    time.sleep(0.8)
    
    try:
        # Ensure terminal scrolled to bottom, then clear and hide cursor
        print("\n" * 5)  # Push any content up
        sys.stdout.write("\033[2J\033[H\033[?25l")
        sys.stdout.flush()

        prev_lines: List[str] = []

        # Load script if provided
        script_events = []
        next_event_idx = 0
        run_start = time.time()
        if args.script:
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
                if key == 'q':
                    running = False
                elif key == 'a':
                    state.btnA = not state.btnA
                    if state.btnA:
                        state.scene = (state.scene + 1) % 3
                elif key == 'b':
                    state.btnB = not state.btnB
                elif key == 'c':
                    state.btnC = not state.btnC
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
            
            # Apply queued events (RPC/ UART)
            try:
                while True:
                    ev = evq.get_nowait()
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

            # Scripted events
            if script_events:
                elapsed_ms = int((time.time() - run_start) * 1000)
                while next_event_idx < len(script_events) and int(script_events[next_event_idx].get('at_ms', 0)) <= elapsed_ms:
                    apply_rpc_message(state, script_events[next_event_idx])
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
            
            # Render frame using previous timing metrics
            lines = render_frame(state, frame, fps, width=args.width, height=args.height,
                                 use_unicode=(not args.no_unicode), use_color=(not args.no_color),
                                 compute_ms=compute_ms_prev, sleep_ms=sleep_ms_prev, util=util_prev)

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
            # Update only footer line with new metrics next loop; no second full render here
    
    except KeyboardInterrupt:
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
