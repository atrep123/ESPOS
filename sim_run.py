#!/usr/bin/env python3
"""
ESP32 UI Simulator - Python Version
Runs without requiring C compiler
"""

import os
import sys
import time
import platform
from dataclasses import dataclass

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

def rgb565(r, g, b):
    """Convert RGB888 to RGB565"""
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def rgb565_to_rgb(color):
    """Convert RGB565 to RGB888"""
    r = ((color >> 11) & 0x1F) << 3
    g = ((color >> 5) & 0x3F) << 2
    b = (color & 0x1F) << 3
    return r, g, b

def get_ansi_color(rgb565_color):
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

def clear_screen():
    """Clear terminal screen"""
    # Use faster direct escape without flush
    sys.stdout.write("\033[2J\033[H")

def enable_ansi_colors():
    """Enable ANSI colors on Windows"""
    if platform.system() == 'Windows':
        os.system('')  # Enable ANSI escape sequences

def get_key_nonblocking():
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

def render_frame(state, frame_num, fps):
    """Render one frame of the simulator"""
    width = 64
    height = 16
    
    # Build entire frame in memory first, then write once
    output = []
    output.append(f"\033[2J\033[H")  # Clear and home
    
    # Title bar
    output.append(f"{Color.BOLD}{Color.CYAN}╔{'═' * width}╗{Color.RESET}\n")
    output.append(f"{Color.BOLD}{Color.CYAN}║{Color.RESET}{Color.BOLD} ESP32 UI SIMULATOR{' ' * (width - 19)}{Color.CYAN}║{Color.RESET}\n")
    output.append(f"{Color.CYAN}╠{'═' * width}╣{Color.RESET}\n")
    
    # Status line
    scene_names = ["HOME", "SETTINGS", "CUSTOM"]
    scene_name = scene_names[state.scene % 3]
    r, g, b = rgb565_to_rgb(state.bg)
    
    output.append(f"{Color.CYAN}║{Color.RESET} Scene: {Color.BOLD}{Color.YELLOW}{scene_name:<10}{Color.RESET} │ "
          f"Tick: {Color.BOLD}{state.t:6d}{Color.RESET} │ "
          f"FPS: {Color.BOLD}{Color.GREEN}{fps:5.1f}{Color.RESET}{' ' * (width - 46)}{Color.CYAN}║{Color.RESET}\n")
    
    # Color info
    output.append(f"{Color.CYAN}║{Color.RESET} BG Color: {Color.BOLD}RGB({r:3d},{g:3d},{b:3d}){Color.RESET} 0x{state.bg:04X}"
          f"{' ' * (width - 35)}{Color.CYAN}║{Color.RESET}\n")
    
    output.append(f"{Color.CYAN}╠{'═' * width}╣{Color.RESET}\n")
    
    # Display simulation
    bg_color = get_ansi_color(state.bg)
    
    for y in range(height):
        line = f"{Color.CYAN}║{Color.RESET}{bg_color}"
        
        # Draw UI elements
        if y == 2:
            # Title on display
            line += f"{Color.BOLD}{Color.BLACK}  {scene_name}  {Color.RESET}{bg_color}"
            line += ' ' * (width - len(scene_name) - 4)
        elif y == 5:
            # Progress bar
            bar_width = width - 4
            filled = state.t % bar_width
            line += f"{Color.BLACK}  [{Color.RESET}{bg_color}"
            line += f"{Color.BOLD}{Color.BLACK}█{Color.RESET}{bg_color}" * filled
            line += f"{Color.DIM}{Color.BLACK}░{Color.RESET}{bg_color}" * (bar_width - filled)
            line += f"{Color.BLACK}]{Color.RESET}{bg_color} "
        elif y == 8:
            # Status text
            status = f"  Frame: {frame_num}"
            line += f"{Color.BLACK}{status}{Color.RESET}{bg_color}"
            line += ' ' * (width - len(status))
        else:
            # Empty display area
            line += ' ' * width
        
        line += f"{Color.RESET}{Color.CYAN}║{Color.RESET}\n"
        output.append(line)
    
    output.append(f"{Color.CYAN}╠{'═' * width}╣{Color.RESET}\n")
    
    # Button status
    btn_a = f"{Color.GREEN}[●]{Color.RESET}" if state.btnA else f"{Color.DIM}[○]{Color.RESET}"
    btn_b = f"{Color.GREEN}[●]{Color.RESET}" if state.btnB else f"{Color.DIM}[○]{Color.RESET}"
    btn_c = f"{Color.GREEN}[●]{Color.RESET}" if state.btnC else f"{Color.DIM}[○]{Color.RESET}"
    
    output.append(f"{Color.CYAN}║{Color.RESET} Buttons: A:{Color.BOLD}{btn_a}  "
          f"B:{Color.BOLD}{btn_b}  C:{Color.BOLD}{btn_c}{' ' * (width - 36)}{Color.CYAN}║{Color.RESET}\n")
    
    output.append(f"{Color.CYAN}╠{'═' * width}╣{Color.RESET}\n")
    
    # Help text
    output.append(f"{Color.CYAN}║{Color.RESET}{Color.DIM} Controls: [A] Button A  [B] Button B  [C] Button C  [Q] Quit"
          f"{' ' * (width - 60)}{Color.RESET}{Color.CYAN}║{Color.RESET}\n")
    output.append(f"{Color.CYAN}║{Color.DIM}           [R] Red  [G] Green  [Y] Yellow  [W] White  [K] Black"
          f"{' ' * (width - 62)}{Color.RESET}{Color.CYAN}║{Color.RESET}\n")
    
    output.append(f"{Color.CYAN}╚{'═' * width}╝{Color.RESET}\n")
    
    # Write everything at once
    sys.stdout.write(''.join(output))
    sys.stdout.flush()

def main():
    """Main simulator loop"""
    enable_ansi_colors()
    
    state = UIState()
    frame = 0
    running = True
    auto_demo = False
    
    start_time = time.time()
    last_frame_time = start_time
    fps = 0.0
    
    print(f"{Color.BOLD}{Color.GREEN}\n=== ESP32 UI SIMULATOR STARTED ==={Color.RESET}")
    print(f"{Color.DIM}Press keys to interact or wait for auto demo...\n{Color.RESET}")
    time.sleep(1)
    
    try:
        while running:
            current_time = time.time()
            elapsed = current_time - last_frame_time
            
            if elapsed > 0:
                fps = 1.0 / elapsed
            last_frame_time = current_time
            
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
            
            render_frame(state, frame, fps)
            frame += 1
            
            time.sleep(0.005)  # ~200 FPS target
    
    except KeyboardInterrupt:
        pass
    
    clear_screen()
    print(f"{Color.BOLD}{Color.YELLOW}\n=== SIMULATOR STOPPED ==={Color.RESET}")
    print(f"Total frames: {frame}")
    print(f"Total time: {time.time() - start_time:.2f} seconds")
    print(f"{Color.DIM}Goodbye!\n{Color.RESET}")

if __name__ == '__main__':
    main()
