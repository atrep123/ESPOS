#!/usr/bin/env python3
"""
Pytest configuration for ESP32OS tests

This module is loaded before any test runs, so we can configure
the environment early to prevent Tk-related issues.
"""

import os

import pytest

# Prevent third-party pytest plugins from being auto-discovered in constrained environments.
os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
# Ensure UTF-8 output to avoid Windows cp1250 console issues
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Set headless mode by default for tests (can be overridden by setting ESP32OS_HEADLESS=0)
# This prevents Tk initialization issues in CI/parallel runs
# Visual UI tests can override this by explicitly setting ESP32OS_HEADLESS=0 before pytest runs
os.environ.setdefault("ESP32OS_HEADLESS", "1")


@pytest.fixture
def headless_preview():
    """Create a headless VisualPreviewWindow for testing"""
    from ui_designer import UIDesigner
    from ui_designer_preview import VisualPreviewWindow

    designer = UIDesigner(width=128, height=64)
    preview = VisualPreviewWindow(designer)
    return preview


def _tk_available() -> bool:
    """Return True if tkinter can be imported and a Tk root can be instantiated."""
    try:
        import tkinter as _tk  # noqa: F401

        # Some environments import but fail on Tk() creation; probe safely
        try:
            root = _tk.Tk()
            root.withdraw()
            root.destroy()
            return True
        except Exception:
            return False
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    """Skip Tk GUI tests automatically when Tk cannot initialize (CI/headless).

    This prevents TclError failures on environments without a GUI backend.
    """
    if _tk_available():
        return
    skip_tk = pytest.mark.skip(reason="Tk not available in this environment")
    for item in items:
        # Skip tests in known Tk-heavy modules
        path = str(item.fspath)
        if any(name in path for name in ["test_preferences_dialog.py", "test_modern_ui.py"]):
            item.add_marker(skip_tk)
