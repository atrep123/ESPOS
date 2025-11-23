#!/usr/bin/env python3
"""
Real Visual UI Tests using PyAutoGUI
Tests actual Tkinter GUI interaction (not headless)
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import pytest


# Function to check if we should skip visual tests
def should_skip_visual():
    """Check at runtime if visual tests should be skipped"""
    return os.environ.get("ESP32OS_HEADLESS", "0") == "1"


try:
    import mss
    import pyautogui
    from PIL import Image

    VISUAL_TEST_AVAILABLE = True
except ImportError:
    VISUAL_TEST_AVAILABLE = False


class UIDesignerApp:
    """Helper class to launch and control UI Designer application"""

    def __init__(self, width: int = 800, height: int = 600):
        self.process: Optional[subprocess.Popen] = None
        self.width = width
        self.height = height
        self.window_title = "ESP32OS UI Designer"

    def launch(self, design_file: Optional[str] = None) -> bool:
        """Launch the UI Designer application"""
        # Set environment to disable headless mode
        env = os.environ.copy()
        env["ESP32OS_HEADLESS"] = "0"

        # Build command
        cmd = [sys.executable, "ui_designer_pro.py"]
        if design_file:
            cmd.extend(["--json", design_file])

        try:
            self.process = subprocess.Popen(
                cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            # Wait for window to appear (longer for slower systems)
            time.sleep(3.5)

            if not self.is_running():
                stderr = self.process.stderr.read() if self.process.stderr else b""
                print(f"Process not running. Stderr: {stderr.decode('utf-8', errors='ignore')}")
                return False
            return True
        except Exception as e:
            print(f"Failed to launch: {e}")
            return False

    def is_running(self) -> bool:
        """Check if application is running"""
        return self.process is not None and self.process.poll() is None

    def close(self):
        """Close the application"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

    def screenshot(self, region: Optional[tuple] = None):
        """Take screenshot of application window"""
        with mss.mss() as sct:
            if region:
                monitor = {
                    "top": region[1],
                    "left": region[0],
                    "width": region[2],
                    "height": region[3],
                }
            else:
                monitor = sct.monitors[1]  # Primary monitor

            screenshot = sct.grab(monitor)
            return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

    def find_window_position(self) -> Optional[tuple]:
        """Find window position using pyautogui (basic detection)"""
        # Note: This is a placeholder - real implementation would need
        # image templates or window enumeration via Win32 API
        # For now, assume top-left area of screen
        return None  # Caller should use fallback coordinates


@pytest.fixture(autouse=True)
def skip_if_headless():
    """Auto-skip visual tests in headless mode (evaluated at runtime)"""
    if os.environ.get("ESP32OS_HEADLESS", "0") == "1":
        pytest.skip("Visual UI tests require display - skipped in headless mode")
    if not VISUAL_TEST_AVAILABLE:
        pytest.skip("pyautogui/mss not installed")


@pytest.fixture
def ui_app():
    """Fixture to provide UI Designer app instance"""
    app = UIDesignerApp()
    yield app
    app.close()


@pytest.mark.timeout(30)
def test_ui_designer_launches(ui_app):
    """Test that UI Designer application launches successfully"""
    assert ui_app.launch(), "UI Designer should launch"
    assert ui_app.is_running(), "UI Designer should be running"

    # Take screenshot to verify it launched
    screenshot = ui_app.screenshot()
    assert screenshot.size[0] > 0, "Should capture screenshot"

    # Save screenshot for verification
    screenshot.save("test_ui_launch.png")


@pytest.mark.skip(reason="Mouse movement test - disabled to prevent interference with user")
@pytest.mark.timeout(60)
def test_ui_designer_creates_widget(ui_app):
    """Test creating a widget through UI interaction

    DISABLED: This test moves the mouse and may interfere with user work.
    Re-enable only when running in isolated test environment.
    """
    pass


@pytest.mark.skip(reason="Mouse movement test - disabled to prevent interference with user")
@pytest.mark.timeout(45)
def test_ui_designer_drag_drop(ui_app):
    """Test drag and drop functionality

    DISABLED: This test moves the mouse and may interfere with user work.
    """
    pass


@pytest.mark.timeout(30)
def test_ui_designer_keyboard_shortcuts(ui_app):
    """Test keyboard shortcuts"""
    assert ui_app.launch(), "Should launch"
    time.sleep(2)

    # Test Ctrl+S (save)
    pyautogui.hotkey("ctrl", "s")
    time.sleep(0.5)

    # Test Ctrl+Z (undo)
    pyautogui.hotkey("ctrl", "z")
    time.sleep(0.5)

    # Test Ctrl+Y (redo)
    pyautogui.hotkey("ctrl", "y")
    time.sleep(0.5)

    # Verify app is still running after shortcuts
    assert ui_app.is_running(), "App should still be running"


@pytest.mark.skip(reason="Mouse movement test - disabled to prevent interference with user")
@pytest.mark.timeout(40)
def test_ui_designer_menu_navigation(ui_app):
    """Test menu navigation

    DISABLED: This test moves the mouse and may interfere with user work.
    """
    pass


@pytest.mark.timeout(50)
def test_ui_designer_export_functionality(ui_app):
    """Test export functionality through UI"""
    test_file = Path("test_export_design.json")

    # Create simple design
    design = {
        "width": 128,
        "height": 64,
        "widgets": [
            {
                "type": "label",
                "id": "lbl1",
                "x": 10,
                "y": 10,
                "width": 50,
                "height": 20,
                "text": "Test Label",
            }
        ],
    }

    with open(test_file, "w") as f:
        json.dump(design, f)

    try:
        assert ui_app.launch(str(test_file)), "Should launch"
        time.sleep(2)

        # Trigger export (Ctrl+E or File menu)
        pyautogui.hotkey("ctrl", "e")
        time.sleep(1)

        # Take screenshot
        screenshot = ui_app.screenshot()
        screenshot.save("test_ui_export.png")

    finally:
        if test_file.exists():
            test_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
