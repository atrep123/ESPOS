"""Tests for consistency between root constants.py and cyberpunk_designer/constants.py.

Ensures grid defaults, color utilities, and naming conventions are coherent
across the two constant modules.
"""

from __future__ import annotations

import constants as root_const
from cyberpunk_designer.constants import (
    GRID,
    PALETTE,
    color_to_rgb,
    hex_to_rgb,
    snap,
)

# ── Grid consistency ─────────────────────────────────────────────────


def test_designer_grid_matches_root_medium():
    """Designer GRID should equal root GRID_SIZE_MEDIUM (both are the default)."""
    assert GRID == root_const.GRID_SIZE_MEDIUM


def test_snap_with_default_grid():
    assert snap(0) == 0
    assert snap(3) == 0
    assert snap(5) == GRID  # 8
    assert snap(7) == GRID
    assert snap(8) == GRID


def test_snap_with_root_grid_small():
    g = root_const.GRID_SIZE_SMALL
    assert snap(0, g) == 0
    assert snap(3, g) == g
    assert snap(g, g) == g


def test_snap_with_root_grid_large():
    g = root_const.GRID_SIZE_LARGE
    assert snap(0, g) == 0
    assert snap(9, g) == g
    assert snap(g, g) == g


# ── Color utilities ──────────────────────────────────────────────────


def test_hex_to_rgb_valid():
    assert hex_to_rgb("#FF0000") == (255, 0, 0)
    assert hex_to_rgb("#00FF00") == (0, 255, 0)
    assert hex_to_rgb("#0000FF") == (0, 0, 255)
    assert hex_to_rgb("#000000") == (0, 0, 0)
    assert hex_to_rgb("#FFFFFF") == (255, 255, 255)


def test_hex_to_rgb_fallback():
    assert hex_to_rgb("invalid") == (255, 255, 255)
    assert hex_to_rgb("") == (255, 255, 255)
    assert hex_to_rgb("#FFF") == (255, 255, 255)  # too short


def test_color_to_rgb_named_colors():
    assert color_to_rgb("black") == (0, 0, 0)
    assert color_to_rgb("white") == (255, 255, 255)
    assert color_to_rgb("red") == (255, 0, 0)
    assert color_to_rgb("green") == (0, 255, 0)
    assert color_to_rgb("blue") == (0, 0, 255)


def test_color_to_rgb_case_insensitive():
    assert color_to_rgb("RED") == (255, 0, 0)
    assert color_to_rgb("Black") == (0, 0, 0)
    assert color_to_rgb("WHITE") == (255, 255, 255)


def test_color_to_rgb_hex():
    assert color_to_rgb("#FF0000") == (255, 0, 0)


def test_color_to_rgb_0x_format():
    assert color_to_rgb("0xFF0000") == (255, 0, 0)
    assert color_to_rgb("0x00FF00") == (0, 255, 0)
    assert color_to_rgb("0x0000FF") == (0, 0, 255)


def test_color_to_rgb_fallback_default():
    assert color_to_rgb("") == (255, 255, 255)
    assert color_to_rgb(None) == (255, 255, 255)
    assert color_to_rgb("unknown_name") == (255, 255, 255)


def test_color_to_rgb_custom_default():
    assert color_to_rgb("", default=(0, 0, 0)) == (0, 0, 0)


# ── PALETTE structure ────────────────────────────────────────────────


def test_palette_has_required_keys():
    required = {"bg", "panel", "text", "muted", "selection", "grid"}
    assert required.issubset(PALETTE.keys())


def test_palette_values_are_rgb_tuples():
    for key, val in PALETTE.items():
        assert isinstance(val, tuple), f"PALETTE[{key!r}] is not a tuple"
        assert len(val) == 3, f"PALETTE[{key!r}] has {len(val)} elements (expected 3)"
        assert all(0 <= c <= 255 for c in val), f"PALETTE[{key!r}] out of range"


# ── Widget size invariants ───────────────────────────────────────────


def test_min_less_than_max():
    assert root_const.MIN_WIDGET_SIZE < root_const.MAX_WIDGET_SIZE


def test_default_within_bounds():
    assert root_const.MIN_WIDGET_SIZE <= root_const.DEFAULT_WIDGET_SIZE
    assert root_const.DEFAULT_WIDGET_SIZE <= root_const.MAX_WIDGET_SIZE


def test_grid_sizes_ordered():
    assert root_const.GRID_SIZE_SMALL < root_const.GRID_SIZE_MEDIUM < root_const.GRID_SIZE_LARGE
