"""Tests for cyberpunk_designer/font6x8.py — pure utility functions."""

from cyberpunk_designer.font6x8 import (
    _GLYPH_QMARK,
    _GLYPHS,
    CHAR_H,
    CHAR_W,
    _glyph_for_char,
    _row5,
)

# ── constants ──────────────────────────────────────────────────────────


def test_char_w():
    assert CHAR_W == 6


def test_char_h():
    assert CHAR_H == 8


# ── _row5 ──────────────────────────────────────────────────────────────


def test_row5_zero():
    assert _row5(0) == 0


def test_row5_all_set():
    # 0x1F = 0b11111 → shifted left by 1 → 0b111110 = 0x3E
    assert _row5(0x1F) == 0x3E


def test_row5_single_bit():
    # bit 0 → shifted → bit 1
    assert _row5(0x01) == 0x02


def test_row5_masks_upper_bits():
    # 0xFF & 0x1F = 0x1F → 0x3E
    assert _row5(0xFF) == 0x3E


def test_row5_middle_bits():
    # 0x0A = 0b01010 → 0b010100 = 0x14
    assert _row5(0x0A) == 0x14


def test_row5_high_bit():
    # 0x10 = 0b10000 → 0b100000 = 0x20
    assert _row5(0x10) == 0x20


# ── _glyph_for_char ───────────────────────────────────────────────────


def test_glyph_uppercase_A():
    g = _glyph_for_char("A")
    assert g == _GLYPHS["A"]
    assert len(g) == 8


def test_glyph_lowercase_maps_to_upper():
    assert _glyph_for_char("a") == _GLYPHS["A"]
    assert _glyph_for_char("z") == _GLYPHS["Z"]
    assert _glyph_for_char("m") == _GLYPHS["M"]


def test_glyph_digit():
    assert _glyph_for_char("0") == _GLYPHS["0"]
    assert _glyph_for_char("9") == _GLYPHS["9"]


def test_glyph_space():
    assert _glyph_for_char(" ") == _GLYPHS[" "]
    # space is all zeros
    assert all(row == 0 for row in _glyph_for_char(" "))


def test_glyph_special_chars():
    for ch in ".:_-/%?+<>!=(),#*":
        g = _glyph_for_char(ch)
        assert g == _GLYPHS[ch], f"mismatch for {ch!r}"
        assert len(g) == 8


def test_glyph_unknown_returns_qmark():
    assert _glyph_for_char("@") == _GLYPH_QMARK
    assert _glyph_for_char("~") == _GLYPH_QMARK
    assert _glyph_for_char("€") == _GLYPH_QMARK


def test_glyph_empty_string_returns_qmark():
    assert _glyph_for_char("") == _GLYPH_QMARK


def test_glyph_multichar_uses_first():
    # only first character matters
    assert _glyph_for_char("AB") == _GLYPHS["A"]


def test_all_glyph_tuples_are_length_8():
    for ch, glyph in _GLYPHS.items():
        assert len(glyph) == 8, f"glyph for {ch!r} has len {len(glyph)}"


def test_all_glyph_rows_are_6bit():
    """Each row should use at most 6 bits (bit5..bit0)."""
    for ch, glyph in _GLYPHS.items():
        for i, row in enumerate(glyph):
            assert row & ~0x3F == 0, (
                f"glyph {ch!r} row {i}: 0x{row:02x} uses bits above 5"
            )
