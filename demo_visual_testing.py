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
print("  1. PyAutoGUI - Mouse and keyboard automation")
print("  2. PyWinAuto - Window detection and safe clicking")
print("  3. MSS - Fast screenshot capture")
print()
print("Prerequisites:")
print("  - Install: pip install -r requirements-dev.txt")
print("  - Graphical display must be available")
print()
print("NOTE: Tests use WINDOW DETECTION for safe clicking.")
print("      Mouse will move only within detected application window.")
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

# Run all visual UI tests with window detection
print("\nRunning Visual UI Tests (with window detection)...")
print("-" * 60)
result1 = subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        "test_visual_ui_real.py",
        "-v",
        "-s",
        "--tb=short",
        "-p",
        "no:conftest",
    ],
    capture_output=False,
    env=test_env,
)

# Summary
print("\n" + "=" * 60)
print("Demo Complete!")
print("=" * 60)
print(f"\nVisual UI Tests: {'PASSED' if result1.returncode == 0 else 'FAILED'}")
print("\nTests performed:")
print("  ✓ Application launch and screenshot")
print("  ✓ Widget creation (window-relative clicking)")
print("  ✓ Drag & drop (window-relative coordinates)")
print("  ✓ Keyboard shortcuts (Ctrl+S, Ctrl+Z, Ctrl+Y)")
print("  ✓ Menu navigation (safe clicking)")
print("  ✓ Export functionality (Ctrl+E)")
print("\nGenerated screenshots:")
print("  - test_ui_launch.png")
print("  - test_ui_widget_create.png")
print("  - test_ui_drag_drop.png")
print("  - test_ui_menu.png")
print("  - test_ui_export.png")
print("\nAll tests use WINDOW DETECTION for safe interaction!")
print("Check screenshots to see what the tests captured.")
