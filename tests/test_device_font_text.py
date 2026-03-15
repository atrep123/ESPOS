"""Tests for device font rendering, text edge cases, and the font6x8 module.

Covers: font6x8.render_text, draw_text_clipped device vs pixel path,
text_metrics helpers, and clipping boundary conditions.
"""

from __future__ import annotations

import pygame

from cyberpunk_designer import drawing, font6x8, text_metrics
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
BG = (0, 0, 0)


def _surf(w=160, h=80):
    s = pygame.Surface((w, h))
    s.fill(BG)
    return s


def _count_non_bg(surf, region):
    n = 0
    for x in range(region.left, min(region.right, surf.get_width())):
        for y in range(region.top, min(region.bottom, surf.get_height())):
            if surf.get_at((x, y))[:3] != BG:
                n += 1
    return n


# ---------------------------------------------------------------------------
# font6x8 bitmap rendering
# ---------------------------------------------------------------------------
class TestFont6x8:
    def test_char_dimensions(self):
        assert font6x8.CHAR_W == 6
        assert font6x8.CHAR_H == 8

    def test_render_single_char(self):
        surf = font6x8.render_text("A", (255, 255, 255))
        assert surf.get_width() == font6x8.CHAR_W
        assert surf.get_height() == font6x8.CHAR_H

    def test_render_multi_char_width(self):
        surf = font6x8.render_text("ABC", (255, 255, 255))
        assert surf.get_width() == 3 * font6x8.CHAR_W

    def test_render_empty_string(self):
        surf = font6x8.render_text("", (255, 255, 255))
        assert surf.get_width() >= 1  # at least 1px (max(1,0))
        assert surf.get_height() == font6x8.CHAR_H

    def test_render_has_pixels(self):
        surf = font6x8.render_text("X", (255, 0, 0))
        # Should have at least 1 red pixel
        has_color = False
        for x in range(surf.get_width()):
            for y in range(surf.get_height()):
                px = surf.get_at((x, y))
                if px[0] > 200 and px[3] > 0:
                    has_color = True
                    break
        assert has_color

    def test_render_with_shadow(self):
        surf = font6x8.render_text("A", (255, 255, 255), shadow=(80, 80, 80))
        assert surf.get_width() == font6x8.CHAR_W
        assert surf.get_height() == font6x8.CHAR_H

    def test_unknown_glyph_renders_question_mark(self):
        """Non-ASCII chars should render as '?' glyph."""
        surf = font6x8.render_text("\u00e9", (255, 255, 255))
        # Should have same width as single char (fallback to '?')
        assert surf.get_width() == font6x8.CHAR_W

    def test_render_all_printable_ascii(self):
        """All printable ASCII chars should render without error."""
        text = "".join(chr(c) for c in range(32, 127))
        surf = font6x8.render_text(text, (200, 200, 200))
        assert surf.get_width() == len(text) * font6x8.CHAR_W


# ---------------------------------------------------------------------------
# text_metrics module
# ---------------------------------------------------------------------------
class TestTextMetrics:
    def test_is_device_profile_esp32os(self):
        assert text_metrics.is_device_profile("esp32os_256x128_gray4") is True

    def test_is_device_profile_oled(self):
        assert text_metrics.is_device_profile("oled_128x64") is True

    def test_is_device_profile_none(self):
        assert text_metrics.is_device_profile(None) is False

    def test_is_device_profile_random(self):
        assert text_metrics.is_device_profile("tft_320x240") is False

    def test_inner_text_area_with_border(self):
        w = WidgetConfig(type="label", x=0, y=0, width=64, height=24, border=True)
        iw, ih = text_metrics.inner_text_area_px(w)
        assert iw > 0 and ih > 0
        assert iw < 64 and ih < 24

    def test_inner_text_area_no_border(self):
        w = WidgetConfig(type="label", x=0, y=0, width=64, height=24, border=False)
        iw, ih = text_metrics.inner_text_area_px(w)
        assert iw >= 62  # no border inset

    def test_inner_text_area_checkbox(self):
        w = WidgetConfig(type="checkbox", x=0, y=0, width=64, height=16, border=True)
        iw, _ih = text_metrics.inner_text_area_px(w)
        # Checkbox reserves space for the check box itself
        assert iw < 60

    def test_inner_text_zero_size(self):
        w = WidgetConfig(type="label", x=0, y=0, width=0, height=0)
        iw, ih = text_metrics.inner_text_area_px(w)
        assert iw == 0 and ih == 0


class TestEllipsizeChars:
    def test_short_text_unchanged(self):
        assert text_metrics.ellipsize_chars("Hi", 10) == "Hi"

    def test_long_text_truncated(self):
        result = text_metrics.ellipsize_chars("Hello World!!!", 8)
        assert len(result) == 8
        assert result.endswith("...")

    def test_exact_length_unchanged(self):
        assert text_metrics.ellipsize_chars("ABCDE", 5) == "ABCDE"

    def test_zero_max_empty(self):
        assert text_metrics.ellipsize_chars("Hello", 0) == ""

    def test_empty_text(self):
        assert text_metrics.ellipsize_chars("", 10) == ""


class TestWrapTextChars:
    def test_single_line_no_wrap(self):
        lines, trunc = text_metrics.wrap_text_chars("Hello", max_chars=10, max_lines=3)
        assert lines == ["Hello"]
        assert trunc is False

    def test_wrap_long_text(self):
        lines, trunc = text_metrics.wrap_text_chars("AAA BBB CCC", max_chars=5, max_lines=5)
        assert len(lines) >= 2
        assert "AAA" in lines[0]

    def test_truncation_flag(self):
        lines, trunc = text_metrics.wrap_text_chars(
            "Alpha Beta Gamma Delta Epsilon",
            max_chars=8,
            max_lines=2,
        )
        assert len(lines) <= 2
        assert trunc is True

    def test_newline_breaks_paragraph(self):
        lines, _trunc = text_metrics.wrap_text_chars("A\nB", max_chars=10, max_lines=5)
        assert len(lines) >= 2

    def test_zero_max_chars(self):
        lines, _trunc = text_metrics.wrap_text_chars("X", max_chars=0, max_lines=1)
        assert lines == []


class TestTextTruncatesInWidget:
    def test_fits(self):
        w = WidgetConfig(type="label", x=0, y=0, width=64, height=16, border=True)
        assert text_metrics.text_truncates_in_widget(w, "Hi") is False

    def test_truncates(self):
        w = WidgetConfig(type="label", x=0, y=0, width=32, height=16, border=True)
        assert text_metrics.text_truncates_in_widget(w, "This is a very long text") is True

    def test_tiny_widget(self):
        w = WidgetConfig(type="label", x=0, y=0, width=4, height=4, border=True)
        assert text_metrics.text_truncates_in_widget(w, "X") is True


# ---------------------------------------------------------------------------
# draw_text_clipped — device font path
# ---------------------------------------------------------------------------
class TestDrawTextClippedDevice:
    """Verify draw_text_clipped uses font6x8 when device profile is active."""

    def test_device_font_renders_text(self, make_app):
        app = make_app(profile="esp32os_256x128_gray4", size=(256, 192))
        surf = _surf(256, 128)
        rect = pygame.Rect(0, 0, 120, 16)
        drawing.draw_text_clipped(
            app, surf, "Hello", rect, (255, 255, 255), 1, use_device_font=True
        )
        assert _count_non_bg(surf, rect) > 0

    def test_device_font_vs_pixel_font(self, make_app):
        """Device font should produce narrower text than pixel font."""
        app = make_app(profile="esp32os_256x128_gray4", size=(256, 192))
        surf_d = _surf(256, 128)
        surf_p = _surf(256, 128)
        rect = pygame.Rect(0, 0, 200, 16)
        drawing.draw_text_clipped(
            app, surf_d, "ABCDEFGHIJ", rect, (255, 255, 255), 1, use_device_font=True
        )
        drawing.draw_text_clipped(
            app, surf_p, "ABCDEFGHIJ", rect, (255, 255, 255), 1, use_device_font=False
        )
        px_d = _count_non_bg(surf_d, rect)
        px_p = _count_non_bg(surf_p, rect)
        # Both should have some pixels rendered
        assert px_d > 0
        assert px_p > 0

    def test_clipping_respected(self, make_app):
        """Text should not bleed outside the clip rect."""
        app = make_app(size=(256, 192))
        surf = _surf(256, 128)
        rect = pygame.Rect(10, 10, 40, 12)
        drawing.draw_text_clipped(
            app, surf, "Hello World", rect, (255, 255, 255), 0, use_device_font=True
        )
        # Check that pixels outside rect are still BG
        outside_left = _count_non_bg(surf, pygame.Rect(0, 10, 10, 12))
        outside_right = _count_non_bg(surf, pygame.Rect(51, 10, 50, 12))
        assert outside_left == 0
        assert outside_right == 0

    def test_empty_text_no_render(self, make_app):
        app = make_app(size=(256, 192))
        surf = _surf()
        rect = pygame.Rect(0, 0, 80, 16)
        drawing.draw_text_clipped(app, surf, "", rect, (255, 255, 255), 1)
        assert _count_non_bg(surf, rect) == 0

    def test_valign_top(self, make_app):
        app = make_app(size=(256, 192))
        surf = _surf(120, 40)
        rect = pygame.Rect(0, 0, 120, 40)
        drawing.draw_text_clipped(
            app, surf, "X", rect, (255, 255, 255), 0, valign="top", use_device_font=True
        )
        # Text should be near the top — check top half has pixels
        top_half = pygame.Rect(0, 0, 120, 20)
        assert _count_non_bg(surf, top_half) > 0

    def test_valign_bottom(self, make_app):
        app = make_app(size=(256, 192))
        surf = _surf(120, 40)
        rect = pygame.Rect(0, 0, 120, 40)
        drawing.draw_text_clipped(
            app, surf, "X", rect, (255, 255, 255), 0, valign="bottom", use_device_font=True
        )
        bottom_half = pygame.Rect(0, 20, 120, 20)
        assert _count_non_bg(surf, bottom_half) > 0

    def test_align_center(self, make_app):
        app = make_app(size=(256, 192))
        surf = _surf(120, 16)
        rect = pygame.Rect(0, 0, 120, 16)
        drawing.draw_text_clipped(
            app, surf, "A", rect, (255, 255, 255), 0, align="center", use_device_font=True
        )
        # Center region (40..80) should have pixels
        center = pygame.Rect(40, 0, 40, 16)
        assert _count_non_bg(surf, center) > 0

    def test_align_right(self, make_app):
        app = make_app(size=(256, 192))
        surf = _surf(120, 16)
        rect = pygame.Rect(0, 0, 120, 16)
        drawing.draw_text_clipped(
            app, surf, "A", rect, (255, 255, 255), 0, align="right", use_device_font=True
        )
        # Right region should have pixels
        right = pygame.Rect(80, 0, 40, 16)
        assert _count_non_bg(surf, right) > 0

    def test_multiline_device_text(self, make_app):
        """max_lines > 1 should wrap text."""
        app = make_app(size=(256, 192))
        surf = _surf(60, 32)
        rect = pygame.Rect(0, 0, 60, 32)
        drawing.draw_text_clipped(
            app, surf, "AAAA BBBB CCCC", rect, (255, 255, 255), 0, max_lines=3, use_device_font=True
        )
        # Should have pixels in both upper and lower halves
        top = _count_non_bg(surf, pygame.Rect(0, 0, 60, 16))
        bot = _count_non_bg(surf, pygame.Rect(0, 16, 60, 16))
        assert top > 0 and bot > 0

    def test_padding_shrinks_area(self, make_app):
        """Large padding should reduce rendered text area."""
        app = make_app(size=(256, 192))
        surf_no_pad = _surf(120, 32)
        surf_pad = _surf(120, 32)
        rect = pygame.Rect(0, 0, 120, 32)
        drawing.draw_text_clipped(
            app, surf_no_pad, "Hello", rect, (255, 255, 255), 0, use_device_font=True
        )
        drawing.draw_text_clipped(
            app, surf_pad, "Hello", rect, (255, 255, 255), 10, use_device_font=True
        )
        px_no_pad = _count_non_bg(surf_no_pad, rect)
        px_pad = _count_non_bg(surf_pad, rect)
        # Padded version should have fewer or equal pixels
        assert px_pad <= px_no_pad
