#!/usr/bin/env python3
"""
Demo script to show visual UI testing capabilities
Run this to see automated UI testing in action
"""
import os
import sys
import time

# Ensure we're not in headless mode
os.environ['ESP32OS_HEADLESS'] = '0'

print("=" * 60)
print("ESP32OS Visual UI Testing Demo")
print("=" * 60)
print()
print("This demo will show automated UI testing using:")
print("  1. PyAutoGUI - Mouse and keyboard automation")
print("  2. PyWinAuto - Windows UI Automation")
print("  3. MSS - Fast screenshot capture")
print()
print("Prerequisites:")
print("  - Install: pip install -r requirements-dev.txt")
print("  - Graphical display must be available")
print("  - Do not move mouse during tests")
print()

input("Press Enter to start demo...")

print("\n" + "=" * 60)
print("Running Visual UI Tests")
print("=" * 60 + "\n")

# Run the tests
import subprocess

# Test 1: PyAutoGUI tests
print("\n[1/2] Running PyAutoGUI Tests...")
print("-" * 60)
result1 = subprocess.run(
    [sys.executable, '-m', 'pytest', 'test_visual_ui_real.py', '-v', '-s', '--tb=short'],
    capture_output=False
)

# Test 2: PyWinAuto tests  
print("\n[2/2] Running PyWinAuto Tests...")
print("-" * 60)
result2 = subprocess.run(
    [sys.executable, '-m', 'pytest', 'test_visual_ui_advanced.py', '-v', '-s', '--tb=short'],
    capture_output=False
)

# Summary
print("\n" + "=" * 60)
print("Demo Complete!")
print("=" * 60)
print(f"\nPyAutoGUI Tests: {'PASSED' if result1.returncode == 0 else 'FAILED'}")
print(f"PyWinAuto Tests: {'PASSED' if result2.returncode == 0 else 'FAILED'}")
print("\nGenerated screenshots:")
print("  - test_ui_launch.png")
print("  - test_ui_widget_create.png")
print("  - test_ui_drag_drop.png")
print("  - test_ui_menu.png")
print("  - test_ui_export.png")
print("\nCheck these files to see what the automated tests did!")
