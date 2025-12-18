"""Centralized constants used across the UI Designer codebase."""

from pathlib import Path

# Grid sizing presets (pixels)
GRID_SIZE_SMALL = 4  #: Small grid size for fine alignments.
GRID_SIZE_MEDIUM = 8  #: Default grid size for most layouts.
GRID_SIZE_LARGE = 16  #: Large grid size for coarse alignments.

# Widget sizing defaults
DEFAULT_WIDGET_WIDTH = 10  #: Default widget width when unspecified.
DEFAULT_WIDGET_HEIGHT = 10  #: Default widget height when unspecified.
DEFAULT_WIDGET_SIZE = 10  #: Legacy default; kept for compatibility.
MIN_WIDGET_SIZE = 1  #: Minimum allowable widget dimension.
MAX_WIDGET_SIZE = 1000  #: Maximum allowable widget dimension for safety.

# Filesystem layout
ESP32_CONFIG_DIR = ".esp32os"  #: Name of the user config directory.
BACKUP_DIR_NAME = "designer_backups"  #: Name of the backups subdirectory.
ESP32OS_DIR = Path.home() / ESP32_CONFIG_DIR  #: Root directory for user data.
BACKUP_DIR = ESP32OS_DIR / BACKUP_DIR_NAME  #: Backup directory for autosaves.

__all__ = [
    "GRID_SIZE_SMALL",
    "GRID_SIZE_MEDIUM",
    "GRID_SIZE_LARGE",
    "DEFAULT_WIDGET_WIDTH",
    "DEFAULT_WIDGET_HEIGHT",
    "DEFAULT_WIDGET_SIZE",
    "MIN_WIDGET_SIZE",
    "MAX_WIDGET_SIZE",
    "ESP32_CONFIG_DIR",
    "BACKUP_DIR_NAME",
    "ESP32OS_DIR",
    "BACKUP_DIR",
]
