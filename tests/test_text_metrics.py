"""Tests for cyberpunk_designer/text_metrics.py pure functions."""

from types import SimpleNamespace

from cyberpunk_designer.text_metrics import (
    ellipsize_chars,
    inner_text_area_px,
    is_device_profile,
    text_truncates_in_widget,
    wrap_text_chars,
)

# ── is_device_profile ──


class TestIsDeviceProfile:
    def test_esp32os_prefix(self):
        assert is_device_profile("esp32os_256x128_gray4") is True

    def test_oled_prefix(self):
        assert is_device_profile("oled_ssd1306") is True

    def test_none(self):
        assert is_device_profile(None) is False

    def test_empty(self):
        assert is_device_profile("") is False

    def test_generic(self):
        assert is_device_profile("generic_lcd") is False

    def test_case_insensitive(self):
        assert is_device_profile("ESP32OS_128x64") is True


# ── ellipsize_chars ──


class TestEllipsizeChars:
    def test_short_text_unchanged(self):
        assert ellipsize_chars("Hi", 10) == "Hi"

    def test_exact_length(self):
        assert ellipsize_chars("Hello", 5) == "Hello"

    def test_truncated_with_ellipsis(self):
        assert ellipsize_chars("Hello World", 8) == "Hello..."

    def test_very_short_max(self):
        result = ellipsize_chars("Hello", 3)
        assert len(result) == 3

    def test_empty_text(self):
        assert ellipsize_chars("", 10) == ""

    def test_zero_max(self):
        assert ellipsize_chars("Hello", 0) == ""

    def test_none_text(self):
        assert ellipsize_chars(None, 5) == ""

    def test_custom_ellipsis(self):
        result = ellipsize_chars("Hello World", 7, ellipsis="..")
        assert result.endswith("..")
        assert len(result) <= 7

    def test_no_ellipsis(self):
        result = ellipsize_chars("Hello World", 5, ellipsis="")
        assert result == "Hello"


# ── wrap_text_chars ──


class TestWrapTextChars:
    def test_single_line(self):
        lines, truncated = wrap_text_chars("Hi", 10, 5)
        assert lines == ["Hi"]
        assert truncated is False

    def test_two_lines(self):
        lines, truncated = wrap_text_chars("Hello World", 5, 5)
        assert len(lines) == 2
        assert truncated is False

    def test_truncated(self):
        lines, truncated = wrap_text_chars("one two three four five", 5, 2)
        assert len(lines) <= 2
        assert truncated is True

    def test_empty_text(self):
        lines, truncated = wrap_text_chars("", 10, 5)
        assert lines == []
        assert truncated is False

    def test_zero_max_chars(self):
        lines, truncated = wrap_text_chars("Hi", 0, 5)
        assert lines == []

    def test_zero_max_lines(self):
        lines, truncated = wrap_text_chars("Hi", 10, 0)
        assert lines == []

    def test_long_word_chunked(self):
        lines, truncated = wrap_text_chars("ABCDEFGHIJ", 5, 5)
        assert len(lines) == 2
        assert lines[0] == "ABCDE"
        assert lines[1] == "FGHIJ"

    def test_explicit_newlines(self):
        lines, truncated = wrap_text_chars("A\nB\nC", 10, 10)
        assert len(lines) == 3
        assert "A" in lines[0]
        assert "B" in lines[1]
        assert "C" in lines[2]

    def test_trailing_ellipsis_on_truncation(self):
        lines, truncated = wrap_text_chars("one two three four five six", 5, 2, ellipsis="...")
        assert truncated is True
        # Last line should be present and not exceed max_chars
        assert len(lines) == 2
        assert len(lines[-1]) <= 5


# ── inner_text_area_px ──


def _widget(type="label", width=40, height=14, border=True, **kw):
    return SimpleNamespace(type=type, width=width, height=height, border=border, **kw)


class TestInnerTextAreaPx:
    def test_label_with_border(self):
        w = _widget(type="label", width=40, height=14, border=True)
        iw, ih = inner_text_area_px(w)
        assert iw > 0
        assert ih > 0
        assert iw < 40
        assert ih < 14

    def test_label_no_border(self):
        w = _widget(type="label", width=40, height=14, border=False)
        iw, ih = inner_text_area_px(w)
        assert iw > 0
        assert ih > 0

    def test_border_inset_larger(self):
        w_border = _widget(width=40, height=14, border=True)
        w_no = _widget(width=40, height=14, border=False)
        iw_b, ih_b = inner_text_area_px(w_border)
        iw_n, ih_n = inner_text_area_px(w_no)
        assert iw_b < iw_n
        assert ih_b < ih_n

    def test_zero_dimensions(self):
        w = _widget(width=0, height=0)
        iw, ih = inner_text_area_px(w)
        assert iw == 0
        assert ih == 0

    def test_checkbox(self):
        w = _widget(type="checkbox", width=40, height=14)
        iw, ih = inner_text_area_px(w)
        # Checkbox subtracts box area from width
        assert iw > 0

    def test_tiny_widget(self):
        w = _widget(width=2, height=2, border=True)
        iw, ih = inner_text_area_px(w)
        assert iw >= 0
        assert ih >= 0


# ---------------------------------------------------------------------------
# AW: Text metrics edge case tests — Unicode, long words, text_truncates
# ---------------------------------------------------------------------------


class TestEllipsizeCharsUnicode:
    def test_unicode_text(self):
        result = ellipsize_chars("Příliš žluťoučký", 10)
        assert len(result) <= 10
        assert result.endswith("...")

    def test_emoji(self):
        result = ellipsize_chars("Hello 🌍🌎🌏", 8)
        assert len(result) == 8

    def test_cjk(self):
        result = ellipsize_chars("你好世界测试", 4)
        assert len(result) == 4
        assert result.endswith("...")

    def test_single_char(self):
        assert ellipsize_chars("A", 1) == "A"

    def test_max_1_truncated(self):
        result = ellipsize_chars("AB", 1)
        assert len(result) == 1


class TestWrapTextCharsEdge:
    def test_tabs_replaced(self):
        """Tabs are replaced with spaces."""
        lines, _ = wrap_text_chars("A\tB", 10, 5)
        assert any("A" in line and "B" in line for line in lines)

    def test_carriage_return_stripped(self):
        r"""\r is stripped from text."""
        lines, _ = wrap_text_chars("A\r\nB", 10, 5)
        assert len(lines) == 2

    def test_multiple_spaces_collapsed(self):
        """Multiple spaces are collapsed to single space."""
        lines, _ = wrap_text_chars("A    B", 10, 5)
        assert lines[0] == "A B"

    def test_very_long_word_chunks(self):
        """A single word longer than max_chars is chunked."""
        lines, truncated = wrap_text_chars("ABCDEFGHIJKLMNOP", 5, 10)
        assert len(lines) >= 3
        for line in lines:
            assert len(line) <= 5

    def test_many_paragraphs_truncated(self):
        text = "\n".join(f"line{i}" for i in range(20))
        lines, truncated = wrap_text_chars(text, 10, 5)
        assert len(lines) == 5
        assert truncated is True

    def test_none_text(self):
        lines, truncated = wrap_text_chars(None, 10, 5)
        assert lines == []
        assert truncated is False

    def test_single_newline_only(self):
        lines, truncated = wrap_text_chars("\n", 10, 5)
        assert truncated is False

    def test_ellipsis_on_truncated_long_word(self):
        """Long word truncated with ellipsis on final visible line."""
        lines, truncated = wrap_text_chars("A B C D E F G H I J K", 5, 2, ellipsis="...")
        assert truncated is True
        assert len(lines) == 2
        assert len(lines[-1]) <= 5


class TestInnerTextAreaPxEdge:
    def test_radiobutton(self):
        w = _widget(type="radiobutton", width=40, height=14)
        iw, ih = inner_text_area_px(w)
        assert iw > 0
        assert ih > 0

    def test_negative_dimensions(self):
        w = _widget(width=-5, height=-5)
        iw, ih = inner_text_area_px(w)
        assert iw == 0
        assert ih == 0

    def test_checkbox_tiny(self):
        """Checkbox with very small height."""
        w = _widget(type="checkbox", width=20, height=3)
        iw, ih = inner_text_area_px(w)
        assert iw >= 0
        assert ih >= 0

    def test_large_widget(self):
        w = _widget(width=500, height=300, border=True)
        iw, ih = inner_text_area_px(w)
        assert iw == 496  # 500 - (1+1)*2
        assert ih == 296  # 300 - (1+1)*2


class TestTextTruncatesInWidget:
    def test_short_text_no_truncation(self):
        w = _widget(width=60, height=14, border=True)
        assert text_truncates_in_widget(w, "Hi") is False

    def test_long_text_truncated(self):
        w = _widget(width=20, height=10, border=True)
        assert text_truncates_in_widget(w, "A very long text that overflows") is True

    def test_empty_text(self):
        w = _widget(width=40, height=14)
        assert text_truncates_in_widget(w, "") is False

    def test_zero_size_widget_with_text(self):
        w = _widget(width=0, height=0)
        assert text_truncates_in_widget(w, "text") is True

    def test_wrap_mode_fits(self):
        w = _widget(width=40, height=32, border=False, text_overflow="wrap")
        # 40px / 6 = 6 chars, 32px / 8 = 4 lines
        assert text_truncates_in_widget(w, "short") is False

    def test_wrap_mode_truncated(self):
        w = _widget(width=20, height=10, border=False, text_overflow="wrap")
        long_text = "This is a very long text that needs many lines"
        assert text_truncates_in_widget(w, long_text) is True

    def test_auto_mode_single_line(self):
        w = _widget(width=60, height=14, border=True, text_overflow="auto")
        assert text_truncates_in_widget(w, "Hi") is False

    def test_auto_mode_wraps_newline(self):
        w = _widget(width=60, height=40, border=False, text_overflow="auto")
        assert text_truncates_in_widget(w, "Line1\nLine2") is False

    def test_clip_mode(self):
        w = _widget(width=20, height=10, border=True, text_overflow="clip")
        assert text_truncates_in_widget(w, "A long text here") is True

    def test_max_lines_limit(self):
        w = _widget(width=60, height=100, border=False, text_overflow="wrap", max_lines=2)
        long_text = "Line one text\nLine two text\nLine three text"
        assert text_truncates_in_widget(w, long_text) is True

    def test_none_text(self):
        w = _widget(width=40, height=14)
        assert text_truncates_in_widget(w, None) is False

    def test_invalid_overflow_mode(self):
        """Unknown text_overflow defaults to ellipsis behavior."""
        w = _widget(width=20, height=10, border=True, text_overflow="unknown")
        assert text_truncates_in_widget(w, "A long text here") is True
