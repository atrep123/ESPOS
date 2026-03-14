"""Tests for cyberpunk_designer/constants.py — snap, hex_to_rgb, color_to_rgb."""

from cyberpunk_designer.constants import (
    GRID,
    NAMED_COLORS,
    color_to_rgb,
    hex_to_rgb,
    snap,
)

# ── snap ───────────────────────────────────────────────────────────────


def test_snap_exact_multiple():
    assert snap(16) == 16


def test_snap_rounds_up():
    assert snap(13, 8) == 16


def test_snap_rounds_down():
    assert snap(11, 8) == 8


def test_snap_zero():
    assert snap(0) == 0


def test_snap_negative():
    assert snap(-3, 8) == 0


def test_snap_custom_grid():
    assert snap(7, 4) == 8


def test_snap_uses_default_grid():
    assert snap(GRID) == GRID


# ── hex_to_rgb ────────────────────────────────────────────────────────


def test_hex_valid():
    assert hex_to_rgb("#ff0000") == (255, 0, 0)


def test_hex_lowercase():
    assert hex_to_rgb("#aabbcc") == (0xAA, 0xBB, 0xCC)


def test_hex_uppercase():
    assert hex_to_rgb("#AABBCC") == (0xAA, 0xBB, 0xCC)


def test_hex_black():
    assert hex_to_rgb("#000000") == (0, 0, 0)


def test_hex_white():
    assert hex_to_rgb("#ffffff") == (255, 255, 255)


def test_hex_invalid_returns_white():
    assert hex_to_rgb("notacolor") == (255, 255, 255)


def test_hex_empty_returns_white():
    assert hex_to_rgb("") == (255, 255, 255)


def test_hex_short_returns_white():
    assert hex_to_rgb("#fff") == (255, 255, 255)


def test_hex_no_hash_returns_white():
    assert hex_to_rgb("ff0000") == (255, 255, 255)


def test_hex_with_leading_space():
    assert hex_to_rgb("  #aabbcc") == (0xAA, 0xBB, 0xCC)


# ── color_to_rgb ──────────────────────────────────────────────────────


def test_color_named_black():
    assert color_to_rgb("black") == (0, 0, 0)


def test_color_named_white():
    assert color_to_rgb("white") == (255, 255, 255)


def test_color_named_red():
    assert color_to_rgb("red") == (255, 0, 0)


def test_color_named_case_insensitive():
    assert color_to_rgb("BLACK") == (0, 0, 0)
    assert color_to_rgb("Red") == (255, 0, 0)


def test_color_named_gray_vs_grey():
    assert color_to_rgb("gray") == (128, 128, 128)
    assert color_to_rgb("grey") == (128, 128, 128)


def test_color_all_named_colors():
    for name, expected in NAMED_COLORS.items():
        assert color_to_rgb(name) == expected, f"failed for {name}"


def test_color_hex():
    assert color_to_rgb("#ff0000") == (255, 0, 0)


def test_color_0x_format():
    assert color_to_rgb("0xFF0000") == (255, 0, 0)


def test_color_0x_lowercase():
    assert color_to_rgb("0x00ff00") == (0, 255, 0)


def test_color_empty_uses_default():
    assert color_to_rgb("") == (255, 255, 255)


def test_color_empty_custom_default():
    assert color_to_rgb("", default=(10, 20, 30)) == (10, 20, 30)


def test_color_none_uses_default():
    assert color_to_rgb(None) == (255, 255, 255)


def test_color_invalid_uses_default():
    assert color_to_rgb("chartreuse") == (255, 255, 255)


def test_color_invalid_custom_default():
    assert color_to_rgb("neon", default=(5, 5, 5)) == (5, 5, 5)


def test_color_0x_too_short_uses_default():
    assert color_to_rgb("0xFFF") == (255, 255, 255)


def test_color_integer_input():
    # non-string values get str()'d
    assert color_to_rgb(123) == (255, 255, 255)
