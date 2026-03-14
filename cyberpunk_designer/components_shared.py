"""Shared constants and helpers for component blueprint modules."""

from __future__ import annotations

# Neutral defaults (device-friendly; avoid neon/cyberpunk look).
NEON_FG = "#f5f5f5"
NEON_MAGENTA = "#e0e0e0"
PANEL_BG = "#101010"
PANEL2_BG = "#080808"
TEXT_FG = "#f0f0f0"

# Common layout dimensions used across widget blueprints.
LABEL_H = 16  # Standard label / single-line text height
PAD = 12  # Default component internal padding
PAD_SM = 4  # Small padding / gap between elements


def scene_size(sc: object, dw: int = 256, dh: int = 128) -> tuple[int, int]:
    """Extract (width, height) from a scene object with safe fallback."""
    try:
        return max(1, int(sc.width)), max(1, int(sc.height))  # type: ignore[union-attr]
    except (ValueError, TypeError, AttributeError):
        return dw, dh


def scene_width(sc: object, dw: int = 256) -> int:
    """Extract width from a scene object with safe fallback."""
    try:
        return max(1, int(sc.width))  # type: ignore[union-attr]
    except (ValueError, TypeError, AttributeError):
        return dw
