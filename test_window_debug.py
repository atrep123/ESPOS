#!/usr/bin/env python3
"""Debug window detection"""

import os
import subprocess
import sys
import time

os.environ["ESP32OS_HEADLESS"] = "0"

print("Launching ui_designer_pro.py...")
proc = subprocess.Popen(
    [sys.executable, "ui_designer_pro.py"],
    env=os.environ.copy(),
)

print(f"Process PID: {proc.pid}")
time.sleep(3)

print("\nTrying to connect with pywinauto...")
try:
    from pywinauto import Application
    
    app = Application(backend="uia").connect(process=proc.pid, timeout=5)
    print(f"[OK] Connected to process {proc.pid}")
    
    # Try to find window
    windows = app.windows()
    print(f"Found {len(windows)} windows:")
    for i, win in enumerate(windows):
        try:
            print(f"  [{i}] Title: '{win.window_text()}', Class: '{win.class_name()}'")
            rect = win.rectangle()
            print(f"       Position: ({rect.left}, {rect.top}), Size: {rect.width()}x{rect.height()}")
        except Exception as e:
            print(f"  [{i}] Error reading window: {e}")
    
    # Try generic window match
    print("\nTrying to get main window...")
    try:
        main_win = app.window(title_re=".*")
        if main_win.exists():
            print(f"[OK] Main window found: '{main_win.window_text()}'")
            rect = main_win.rectangle()
            print(f"     Position: ({rect.left}, {rect.top}), Size: {rect.width()}x{rect.height()}")
        else:
            print("[FAIL] Main window not found")
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        
except Exception as e:
    print(f"[FAIL] PyWinAuto connection failed: {e}")

print("\nKeeping process alive for 5 seconds...")
time.sleep(5)

proc.terminate()
proc.wait(timeout=5)
print("Process terminated")
