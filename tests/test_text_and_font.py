"""Tests for cyberpunk_designer.text_metrics and cyberpunk_designer.font6x8."""

from cyberpunk_designer.font6x8 import CHAR_H, CHAR_W, _glyph_for_char, render_text
from cyberpunk_designer.text_metrics import (
    ellipsize_chars,
    inner_text_area_px,
    is_device_profile,
    text_truncates_in_widget,
    wrap_text_chars,
)
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# font6x8 — glyph lookup
# ---------------------------------------------------------------------------

def test_glyph_constants():
    assert CHAR_W == 6
    assert CHAR_H == 8


def test_glyph_uppercase():
    g = _glyph_for_char("A")
    assert len(g) == 8
    assert any(row != 0 for row in g), "A glyph should have lit pixels"


def test_glyph_lowercase_maps_to_upper():
    assert _glyph_for_char("a") == _glyph_for_char("A")
    assert _glyph_for_char("z") == _glyph_for_char("Z")


def test_glyph_digit():
    g = _glyph_for_char("0")
    assert len(g) == 8
    assert any(row != 0 for row in g)


def test_glyph_unsupported_returns_qmark():
    g_unknown = _glyph_for_char("é")
    g_qmark = _glyph_for_char("?")
    assert g_unknown == g_qmark


def test_glyph_empty_returns_qmark():
    assert _glyph_for_char("") == _glyph_for_char("?")


# ---------------------------------------------------------------------------
# font6x8 — render_text
# ---------------------------------------------------------------------------

def test_render_text_surface_size():
    surf = render_text("ABC", (255, 255, 255))
    assert surf.get_width() == 3 * CHAR_W
    assert surf.get_height() == CHAR_H


def test_render_text_has_pixels():
    surf = render_text("X", (255, 255, 255))
    has_white = False
    for x in range(surf.get_width()):
        for y in range(surf.get_height()):
            if surf.get_at((x, y))[:3] == (255, 255, 255):
                has_white = True
                break
    assert has_white, "render_text should produce visible pixels"


def test_render_text_empty():
    surf = render_text("", (255, 255, 255))
    assert surf.get_width() >= 1  # minimum 1px for empty


def test_render_text_with_shadow():
    surf = render_text("A", (255, 255, 255), shadow=(64, 64, 64))
    # Should have both white and shadow-color pixels
    colors = set()
    for x in range(surf.get_width()):
        for y in range(surf.get_height()):
            c = surf.get_at((x, y))[:3]
            if c != (0, 0, 0):
                colors.add(c)
    assert len(colors) >= 2, "shadow should produce additional colored pixels"


def test_render_text_caching():
    # Same text+color should return cached surface
    s1 = render_text("HI", (200, 200, 200))
    s2 = render_text("HI", (200, 200, 200))
    assert s1 is s2


# ---------------------------------------------------------------------------
# text_metrics — is_device_profile
# ---------------------------------------------------------------------------

def test_is_device_profile_oled():
    assert is_device_profile("oled_128x64") is True
    assert is_device_profile("oled_72x40") is True


def test_is_device_profile_esp32os():
    assert is_device_profile("esp32os_256x128_gray4") is True


def test_is_device_profile_tft():
    assert is_device_profile("tft_320x240") is False


def test_is_device_profile_none():
    assert is_device_profile(None) is False
    assert is_device_profile("") is False


# ---------------------------------------------------------------------------
# text_metrics — inner_text_area_px
# ---------------------------------------------------------------------------

def test_inner_text_area_label():
    w = WidgetConfig(type="label", x=0, y=0, width=40, height=14, border=True)
    iw, ih = inner_text_area_px(w)
    assert iw > 0
    assert ih > 0
    assert iw < 40
    assert ih < 14


def test_inner_text_area_no_border():
    w = WidgetConfig(type="label", x=0, y=0, width=40, height=14, border=False)
    iw_no, ih_no = inner_text_area_px(w)
    w2 = WidgetConfig(type="label", x=0, y=0, width=40, height=14, border=True)
    iw_yes, ih_yes = inner_text_area_px(w2)
    assert iw_no >= iw_yes, "no border should give more inner space"


def test_inner_text_area_checkbox():
    w = WidgetConfig(type="checkbox", x=0, y=0, width=60, height=14)
    iw, ih = inner_text_area_px(w)
    assert iw < 60, "checkbox reserves space for the check box"
    assert ih > 0


def test_inner_text_area_radiobutton():
    w = WidgetConfig(type="radiobutton", x=0, y=0, width=60, height=14)
    iw, ih = inner_text_area_px(w)
    assert iw < 60
    assert ih > 0


def test_inner_text_area_zero_dims():
    w = WidgetConfig(type="label", x=0, y=0, width=0, height=0)
    assert inner_text_area_px(w) == (0, 0)


# ---------------------------------------------------------------------------
# text_metrics — ellipsize_chars
# ---------------------------------------------------------------------------

def test_ellipsize_short_text():
    assert ellipsize_chars("HI", 10) == "HI"


def test_ellipsize_exact_fit():
    assert ellipsize_chars("ABCDE", 5) == "ABCDE"


def test_ellipsize_truncates():
    result = ellipsize_chars("ABCDEFGHIJ", 6)
    assert result.endswith("...")
    assert len(result) == 6


def test_ellipsize_empty():
    assert ellipsize_chars("", 5) == ""


# ---------------------------------------------------------------------------
# text_metrics — deep coverage
# ---------------------------------------------------------------------------


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=60, height=16, text="t")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def test_inner_text_area_checkbox_tiny():
    """Checkbox with height < 4 should clamp box to 2 (line 27)."""
    w = _w(type="checkbox", width=20, height=3)
    iw, ih = inner_text_area_px(w)
    assert iw >= 0
    assert ih >= 0


def test_wrap_truncated_push_after_truncation():
    """After truncation, further pushes are silently skipped (line 76)."""
    # max_lines=1 with long multi-para text → truncation early, more paras skipped
    lines, trunc = wrap_text_chars("First para\nSecond para\nThird", max_chars=10, max_lines=1)
    assert trunc
    assert len(lines) == 1


def test_wrap_multi_para_truncation_break():
    """Multi-paragraph text where truncation happens mid-way (line 84)."""
    lines, trunc = wrap_text_chars("AAA BBB\nCCC DDD\nEEE", max_chars=5, max_lines=2)
    assert trunc
    assert len(lines) <= 2


def test_wrap_truncated_no_ellipsis():
    """When truncated with no ellipsis, last line is clipped raw (line 114)."""
    lines, trunc = wrap_text_chars("AAAAAA BBBBB CCCCC", max_chars=6, max_lines=2, ellipsis="")
    assert trunc
    assert len(lines[-1]) <= 6


def test_text_truncates_invalid_overflow():
    """Invalid overflow value falls back to ellipsis (line 132)."""
    w = _w(text_overflow="GARBAGE")
    result = text_truncates_in_widget(w, "short")
    assert isinstance(result, bool)


def test_text_truncates_auto_multiline():
    """Auto overflow with multiline text exercises the wrap path (line 138)."""
    w = _w(text_overflow="auto", width=60, height=24)
    # Long text with newline triggers wrap in auto mode
    result = text_truncates_in_widget(w, "Line one\nLine two which is quite long")
    assert isinstance(result, bool)


def test_text_truncates_auto_long_flat():
    """Auto overflow with long flat text (exceeds max_chars) → wrap mode."""
    w = _w(text_overflow="auto", width=30, height=24)
    result = text_truncates_in_widget(w, "A" * 100)
    assert result is True


def test_text_truncates_with_max_lines():
    """Widget with max_lines constraint exercises lines 147-149."""
    w = _w(text_overflow="wrap", width=60, height=80, max_lines=2)
    result = text_truncates_in_widget(w, "AAA BBB CCC DDD EEE FFF GGG HHH III")
    assert result is True


def test_text_truncates_wrap_fits():
    """Wrap mode where text fits within lines."""
    w = _w(text_overflow="wrap", width=60, height=24)
    result = text_truncates_in_widget(w, "Hi")
    assert result is False


def test_ellipsize_zero_max():
    assert ellipsize_chars("ABC", 0) == ""


def test_ellipsize_no_ellipsis():
    result = ellipsize_chars("ABCDEFG", 4, ellipsis="")
    assert result == "ABCD"


# ---------------------------------------------------------------------------
# text_metrics — wrap_text_chars
# ---------------------------------------------------------------------------

def test_wrap_single_line():
    lines, trunc = wrap_text_chars("HELLO", max_chars=10, max_lines=3)
    assert lines == ["HELLO"]
    assert not trunc


def test_wrap_multi_word():
    lines, trunc = wrap_text_chars("HELLO WORLD", max_chars=6, max_lines=3)
    assert len(lines) == 2
    assert lines[0] == "HELLO"
    assert lines[1] == "WORLD"
    assert not trunc


def test_wrap_truncation():
    lines, trunc = wrap_text_chars("A B C D E F", max_chars=4, max_lines=2)
    assert len(lines) <= 2
    assert trunc


def test_wrap_long_word_chunked():
    lines, trunc = wrap_text_chars("ABCDEFGHIJKL", max_chars=4, max_lines=10)
    assert all(len(line) <= 4 for line in lines)
    assert len(lines) == 3  # ABCD, EFGH, IJKL


def test_wrap_zero_max_chars():
    lines, trunc = wrap_text_chars("X", max_chars=0, max_lines=5)
    assert lines == []


def test_wrap_zero_max_lines():
    lines, trunc = wrap_text_chars("X", max_chars=5, max_lines=0)
    assert lines == []
    assert trunc


def test_wrap_preserves_newlines():
    lines, trunc = wrap_text_chars("A\nB", max_chars=10, max_lines=5)
    assert "A" in lines
    assert "B" in lines


# ---------------------------------------------------------------------------
# text_metrics — text_truncates_in_widget
# ---------------------------------------------------------------------------

def test_truncates_short_text():
    w = WidgetConfig(type="label", x=0, y=0, width=60, height=14, border=True)
    assert not text_truncates_in_widget(w, "HI")


def test_truncates_long_text():
    w = WidgetConfig(type="label", x=0, y=0, width=30, height=14, border=True)
    assert text_truncates_in_widget(w, "ABCDEFGHIJKLMNOP")


def test_truncates_empty_text():
    w = WidgetConfig(type="label", x=0, y=0, width=40, height=14)
    assert not text_truncates_in_widget(w, "")


def test_truncates_with_wrap_overflow():
    w = WidgetConfig(type="label", x=0, y=0, width=40, height=14,
                     text_overflow="wrap")
    # Only 1 line fits in height 14, "WRAP THIS" is 9 chars, fits ~5 chars per line
    assert text_truncates_in_widget(w, "WRAP THIS LONG TEXT")
