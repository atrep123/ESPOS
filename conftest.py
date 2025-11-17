#!/usr/bin/env python3
"""
Pytest configuration for ESP32OS tests

This module is loaded before any test runs, so we can configure
the environment early to prevent Tk-related issues.
"""

import os

# Force headless mode for ALL tests to prevent Tk initialization issues in CI/parallel runs
# This MUST be set before any test imports ui_designer_preview
os.environ["ESP32OS_HEADLESS"] = "1"

