#!/usr/bin/env python3
"""
Pytest configuration for ESP32OS tests

This module is loaded before any test runs, so we can configure
the environment early to prevent Tk-related issues.
"""

import os

import pytest

# Force headless mode for ALL tests to prevent Tk initialization issues in CI/parallel runs
# This MUST be set before any test imports ui_designer_preview
os.environ["ESP32OS_HEADLESS"] = "1"


@pytest.fixture
def headless_preview():
	"""Create a headless VisualPreviewWindow for testing"""
	from ui_designer import UIDesigner
	from ui_designer_preview import VisualPreviewWindow
    
	designer = UIDesigner(width=128, height=64)
	preview = VisualPreviewWindow(designer)
	return preview

