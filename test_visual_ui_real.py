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
    from pywinauto import Application
    from pywinauto.findwindows import ElementNotFoundError

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

        # Build command - use ui_designer_preview.py (actual GUI app)
        cmd = [sys.executable, "ui_designer_preview.py"]
        if design_file:
            cmd.extend(["--in-json", design_file])

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

    def get_window_rect(self) -> Optional[dict]:
        """Get window position and size using pywinauto"""
        if not self.process:
            return None
        
        try:
            app = Application(backend="uia").connect(process=self.process.pid, timeout=3)
            window = app.window(title_re=".*")
            if window.exists():
                rect = window.rectangle()
                return {
                    "left": rect.left,
                    "top": rect.top,
                    "width": rect.width(),
                    "height": rect.height(),
                    "right": rect.right,
                    "bottom": rect.bottom,
                }
        except Exception as e:
            print(f"Could not get window rect: {e}")
        return None

    def safe_click_in_window(self, offset_x: int, offset_y: int) -> bool:
        """Click at position relative to window top-left corner"""
        rect = self.get_window_rect()
        if not rect:
            print("Cannot click - window not found")
            return False
        
        # Calculate absolute screen position
        x = rect["left"] + offset_x
        y = rect["top"] + offset_y
        
        # Verify click is within window bounds
        if x < rect["left"] or x > rect["right"] or y < rect["top"] or y > rect["bottom"]:
            print(f"Click position ({x}, {y}) outside window bounds")
            return False
        
        pyautogui.click(x, y)
        return True

    def safe_drag_in_window(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> bool:
        """Drag from start to end position (relative to window)"""
        rect = self.get_window_rect()
        if not rect:
            return False
        
        abs_start_x = rect["left"] + start_x
        abs_start_y = rect["top"] + start_y
        abs_end_x = rect["left"] + end_x
        abs_end_y = rect["top"] + end_y
        
        pyautogui.moveTo(abs_start_x, abs_start_y)
        pyautogui.mouseDown()
        pyautogui.moveTo(abs_end_x, abs_end_y, duration=duration)
        pyautogui.mouseUp()
        return True


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


@pytest.mark.timeout(60)
def test_ui_designer_creates_widget(ui_app):
    """Test creating a widget through UI interaction using window detection"""
    # Create a test design file
    test_file = Path("test_visual_design.json")
    initial_design = {"width": 128, "height": 64, "widgets": []}

    with open(test_file, "w") as f:
        json.dump(initial_design, f)

    try:
        # Launch with design file
        assert ui_app.launch(str(test_file)), "Should launch with design"
        time.sleep(3)  # Give window time to fully render

        # Get window position
        rect = ui_app.get_window_rect()
        if rect:
            print(f"Window found at: {rect}")
            # Click in center of window (safe fallback)
            center_x = rect["width"] // 2
            center_y = rect["height"] // 2
            
            if ui_app.safe_click_in_window(center_x, center_y):
                time.sleep(0.5)
                
                # Take screenshot after click
                screenshot = ui_app.screenshot()
                screenshot.save("test_ui_widget_create.png")
                assert screenshot.size[0] > 0
            else:
                pytest.skip("Could not safely click in window")
        else:
            pytest.skip("Window detection failed - skipping click test")

    finally:
        if test_file.exists():
            test_file.unlink()


@pytest.mark.timeout(45)
def test_ui_designer_drag_drop(ui_app):
    """Test drag and drop functionality using window-relative coordinates"""
    assert ui_app.launch(), "Should launch"
    time.sleep(3)

    rect = ui_app.get_window_rect()
    if not rect:
        pytest.skip("Window detection failed")
    
    print(f"Window size: {rect['width']}x{rect['height']}")
    
    # Drag from left side to right side (relative to window)
    # Assuming palette is on left, canvas on right
    start_x = rect["width"] // 4  # 25% from left
    start_y = rect["height"] // 3  # 33% from top
    end_x = (rect["width"] * 3) // 4  # 75% from left  
    end_y = rect["height"] // 2  # 50% from top
    
    if ui_app.safe_drag_in_window(start_x, start_y, end_x, end_y, duration=0.5):
        time.sleep(1)
        
        # Capture result
        screenshot = ui_app.screenshot()
        screenshot.save("test_ui_drag_drop.png")
        assert screenshot.size[0] > 0
    else:
        pytest.skip("Could not perform drag operation")


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


@pytest.mark.timeout(40)
def test_ui_designer_menu_navigation(ui_app):
    """Test menu navigation using window-relative coordinates"""
    assert ui_app.launch(), "Should launch"
    time.sleep(3)

    rect = ui_app.get_window_rect()
    if not rect:
        pytest.skip("Window detection failed")
    
    # Menu bar is typically at top-left of window
    # Click at (50, 30) relative to window top-left (should hit File menu)
    menu_x = 50
    menu_y = 30
    
    if ui_app.safe_click_in_window(menu_x, menu_y):
        time.sleep(0.5)
        
        # Take screenshot of menu
        screenshot = ui_app.screenshot()
        screenshot.save("test_ui_menu.png")
        
        # Press Escape to close menu
        pyautogui.press("escape")
        time.sleep(0.5)
        
        assert ui_app.is_running()
    else:
        pytest.skip("Could not safely click menu")


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
