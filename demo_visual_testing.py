#!/usr/bin/env python3
"""
Demo script to show visual UI testing capabilities
Run this to see automated UI testing in action
"""

import os
import sys

# Ensure we're not in headless mode - MUST be set before any imports
os.environ["ESP32OS_HEADLESS"] = "0"

print("=" * 60)
print("ESP32OS Visual UI Testing Demo")
print("=" * 60)
print()
print("This demo will show automated UI testing using:")
print("  1. PyAutoGUI - Screenshot capture and process management")
print("  2. MSS - Fast screenshot capture")
print("  3. Keyboard shortcuts (non-invasive)")
print()
print("Prerequisites:")
print("  - Install: pip install -r requirements-dev.txt")
print("  - Graphical display must be available")
print()
print("NOTE: Mouse movement tests are disabled to prevent")
print("      interference with your work. Only safe tests run.")
print()

input("Press Enter to start demo...")

print("\n" + "=" * 60)
print("Running Visual UI Tests")
print("=" * 60 + "\n")

# Run the tests
import subprocess

# IMPORTANT: Pass ESP32OS_HEADLESS=0 to subprocess environment
test_env = os.environ.copy()
test_env["ESP32OS_HEADLESS"] = "0"

# Run only safe tests (no mouse movement)
print("\nRunning Safe Visual UI Tests...")
print("-" * 60)
result1 = subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        "test_visual_ui_real.py::test_ui_designer_launches",
        "test_visual_ui_real.py::test_ui_designer_keyboard_shortcuts",
        "test_visual_ui_real.py::test_ui_designer_export_functionality",
        "-v",
        "-s",
        "--tb=short",
        "-p",
        "no:conftest",
    ],
    capture_output=False,
    env=test_env,
)

result2 = None  # PyWinAuto tests disabled (don't work with Tkinter)

# Summary
print("\n" + "=" * 60)
print("Demo Complete!")
print("=" * 60)
print(f"\nSafe Visual Tests: {'PASSED' if result1.returncode == 0 else 'FAILED'}")
print("\nTests performed:")
print("  ✓ Application launch and screenshot")
print("  ✓ Keyboard shortcuts (Ctrl+S, Ctrl+Z, Ctrl+Y)")
print("  ✓ Export functionality (Ctrl+E)")
print("\nGenerated screenshots:")
print("  - test_ui_launch.png")
print("  - test_ui_export.png")
print("\nNote: Mouse movement tests disabled to prevent interference.")
print("      Run with pytest -m visual to include all tests.")
