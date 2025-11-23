#!/usr/bin/env python3
"""Quick visual test - direct run without pytest"""

import os
import sys
import time

# Force non-headless
os.environ["ESP32OS_HEADLESS"] = "0"

print(f"Python: {sys.executable}")
print(f"ESP32OS_HEADLESS: {os.environ.get('ESP32OS_HEADLESS')}")

try:
    import mss
    import pyautogui
    from PIL import Image

    print("[OK] All imports successful")
except ImportError as e:
    print(f"[FAIL] Import error: {e}")
    sys.exit(1)

# Try to launch ui_designer_pro.py
import subprocess

print("\nLaunching ui_designer_pro.py...")
proc = subprocess.Popen(
    [sys.executable, "ui_designer_pro.py"],
    env=os.environ.copy(),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

print(f"Process PID: {proc.pid}")
time.sleep(3)

if proc.poll() is None:
    print("[OK] Process is running")

    # Take screenshot
    print("Taking screenshot...")
    with mss.mss() as sct:
        screenshot = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        img.save("quick_test_screenshot.png")
        print(f"[OK] Screenshot saved: quick_test_screenshot.png ({img.size})")

    # Cleanup
    proc.terminate()
    proc.wait(timeout=5)
    print("[OK] Process terminated")
else:
    stderr = proc.stderr.read() if proc.stderr else b""
    print(f"[FAIL] Process died. Stderr: {stderr.decode('utf-8', errors='ignore')}")
    sys.exit(1)

print("\n[SUCCESS] Visual UI test works!")
