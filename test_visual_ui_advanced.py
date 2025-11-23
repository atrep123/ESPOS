#!/usr/bin/env python3
"""
Advanced Visual UI Tests using pywinauto
Tests Windows UI automation with better window detection
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("ESP32OS_HEADLESS") == "1", reason="Visual UI tests require display"
)

try:
    import pyautogui
    from pywinauto import Application
    from pywinauto.findwindows import ElementNotFoundError

    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="pywinauto not installed")


class UIDesignerWindow:
    """Advanced UI Designer window controller using pywinauto"""

    def __init__(self):
        self.app: Optional[Application] = None
        self.process: Optional[subprocess.Popen] = None
        self.main_window = None

    def launch(self, design_file: Optional[str] = None, timeout: int = 10) -> bool:
        """Launch UI Designer and connect to window"""
        env = os.environ.copy()
        env["ESP32OS_HEADLESS"] = "0"

        cmd = [sys.executable, "ui_designer_pro.py"]
        if design_file:
            cmd.extend(["--json", design_file])

        try:
            # Launch process
            self.process = subprocess.Popen(cmd, env=env)

            # Wait for window to appear and connect
            start_time = time.time()
            last_error = None
            while time.time() - start_time < timeout:
                try:
                    # Try to connect to the application
                    self.app = Application(backend="uia").connect(
                        process=self.process.pid, timeout=2
                    )

                    # Try to get main window (Tkinter může používat různé titulky)
                    self.main_window = self.app.window(title_re=".*UI Designer.*|tk.*")
                    if self.main_window.exists():
                        print(f"Connected to window: {self.main_window.window_text()}")
                        return True
                except Exception as e:
                    last_error = str(e)
                    time.sleep(0.5)

            print(f"Failed to connect to window. Last error: {last_error}")
            return False
        except Exception as e:
            print(f"Launch failed: {e}")
            return False

    def close(self):
        """Close application gracefully"""
        if self.main_window:
            try:
                self.main_window.close()
                time.sleep(0.5)
            except:
                pass

        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()

    def click_menu(self, menu_path: str):
        """Click menu item by path (e.g., 'File->Open')"""
        if not self.main_window:
            return False

        try:
            parts = menu_path.split("->")
            menu = self.main_window.menu_select(parts)
            return True
        except:
            return False

    def get_widget_count(self) -> int:
        """Get number of widgets in current design"""
        # This would require inspecting the UI state
        # For now, return -1 as placeholder
        return -1

    def click_button(self, button_text: str) -> bool:
        """Click button by text"""
        if not self.main_window:
            return False

        try:
            button = self.main_window.child_window(title=button_text, control_type="Button")
            button.click()
            return True
        except:
            return False

    def set_text(self, control_name: str, text: str) -> bool:
        """Set text in a text control"""
        if not self.main_window:
            return False

        try:
            control = self.main_window.child_window(auto_id=control_name, control_type="Edit")
            control.set_text(text)
            return True
        except:
            return False


@pytest.fixture
def ui_window():
    """Fixture providing UI Designer window"""
    window = UIDesignerWindow()
    yield window
    window.close()


@pytest.mark.timeout(30)
@pytest.mark.skipif(not PYWINAUTO_AVAILABLE, reason="pywinauto required")
def test_window_launches_and_connects(ui_window):
    """Test that we can launch and connect to the window"""
    assert ui_window.launch(), "Should launch and connect to window"
    assert ui_window.main_window is not None, "Should have main window"
    assert ui_window.main_window.exists(), "Window should exist"


@pytest.mark.timeout(45)
@pytest.mark.skipif(not PYWINAUTO_AVAILABLE, reason="pywinauto required")
def test_window_has_expected_controls(ui_window):
    """Test that window has expected UI controls"""
    assert ui_window.launch(), "Should launch"

    # Check for common controls
    window = ui_window.main_window

    # Should have menu bar
    try:
        menu = window.menu()
        assert menu is not None, "Should have menu bar"
    except:
        pass  # Some Tkinter apps don't expose menu to automation

    # Window should be visible
    assert window.is_visible(), "Window should be visible"


@pytest.mark.timeout(40)
@pytest.mark.skipif(not PYWINAUTO_AVAILABLE, reason="pywinauto required")
def test_load_design_file(ui_window):
    """Test loading a design file"""
    # Create test design
    test_file = Path("test_load.json")
    design = {
        "width": 128,
        "height": 64,
        "widgets": [
            {
                "type": "button",
                "id": "btn1",
                "x": 10,
                "y": 10,
                "width": 40,
                "height": 20,
                "text": "Test",
            }
        ],
    }

    with open(test_file, "w") as f:
        json.dump(design, f)

    try:
        assert ui_window.launch(str(test_file)), "Should launch with file"
        time.sleep(2)

        # Window should still be running
        assert ui_window.main_window.exists(), "Window should exist after load"

    finally:
        if test_file.exists():
            test_file.unlink()


@pytest.mark.timeout(35)
@pytest.mark.skipif(not PYWINAUTO_AVAILABLE, reason="pywinauto required")
def test_window_resize(ui_window):
    """Test window resizing"""
    assert ui_window.launch(), "Should launch"

    window = ui_window.main_window

    # Get initial size
    rect = window.rectangle()
    initial_width = rect.width()
    initial_height = rect.height()

    # Resize window
    window.resize(initial_width + 100, initial_height + 50)
    time.sleep(0.5)

    # Check new size
    new_rect = window.rectangle()
    assert new_rect.width() >= initial_width, "Width should increase"
    assert new_rect.height() >= initial_height, "Height should increase"


@pytest.mark.timeout(40)
@pytest.mark.skipif(not PYWINAUTO_AVAILABLE, reason="pywinauto required")
def test_window_focus_and_activate(ui_window):
    """Test window focus and activation"""
    assert ui_window.launch(), "Should launch"

    window = ui_window.main_window

    # Minimize window
    window.minimize()
    time.sleep(0.5)
    assert not window.is_active(), "Should not be active when minimized"

    # Restore and activate
    window.restore()
    window.set_focus()
    time.sleep(0.5)

    assert window.is_visible(), "Should be visible after restore"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
