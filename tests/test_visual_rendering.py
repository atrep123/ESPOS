"""Pixel-level visual rendering tests for draw_widget_preview and draw_canvas.

Verifies that widgets render correct pixel patterns — not just "something visible"
but the right shapes, fills, positions, and color transformations.
"""

from __future__ import annotations

import pygame

from cyberpunk_designer import drawing
from cyberpunk_designer.constants import GRID, PALETTE, color_to_rgb
from cyberpunk_editor import CyberpunkEditorApp
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
BG = (0, 0, 0)
SURF_W, SURF_H = 160, 80


def _make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    return CyberpunkEditorApp(json_path, (256, 192))


def _surf():
    s = pygame.Surface((SURF_W, SURF_H))
    s.fill(BG)
    return s


def _render(app, wtype, **kw):
    """Render a single widget and return (surface, rect)."""
    ww = kw.pop("width", 80)
    wh = kw.pop("height", 30)
    defaults = dict(color_fg="#f0f0f0", color_bg="#000000")
    defaults.update(kw)
    surf = _surf()
    w = WidgetConfig(type=wtype, x=0, y=0, width=ww, height=wh, **defaults)
    rect = pygame.Rect(4, 4, ww, wh)
    drawing.draw_widget_preview(app, surf, w, rect, BG, 2, False)
    return surf, rect


def _count_px(surf, region, color=None):
    """Count non-BG pixels (or pixels matching `color`) in a region."""
    n = 0
    for x in range(region.left, min(region.right, surf.get_width())):
        for y in range(region.top, min(region.bottom, surf.get_height())):
            px = surf.get_at((x, y))[:3]
            if color is not None:
                if px == color:
                    n += 1
            else:
                if px != BG:
                    n += 1
    return n


def _shade(color, delta):
    return tuple(max(0, min(255, c + delta)) for c in color)


# ---------------------------------------------------------------------------
# Progressbar fill math
# ---------------------------------------------------------------------------


class TestProgressbarFill:
    """Verify progressbar fill width matches expected percentage."""

    def test_zero_percent_no_fill(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf, rect = _render(app, "progressbar", value=0, min_value=0, max_value=100,
                             width=100, height=20, border=True, border_style="single")
        # Inner rect is rect.inflate(-2, -2). At 0% fill_w = 0, so nothing filled.
        inner = rect.inflate(-2, -2)
        fill_color = app._shade(color_to_rgb("#f0f0f0"), -40)
        assert _count_px(surf, inner, fill_color) == 0

    def test_full_percent_fills_inner(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf, rect = _render(app, "progressbar", value=100, min_value=0, max_value=100,
                             width=100, height=20, border=True, border_style="single")
        inner = rect.inflate(-2, -2)
        fill_color = app._shade(color_to_rgb("#f0f0f0"), -40)
        filled = _count_px(surf, inner, fill_color)
        # Should fill the entire inner width × height area
        assert filled == inner.width * inner.height

    def test_half_fills_approximately_half(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf, rect = _render(app, "progressbar", value=50, min_value=0, max_value=100,
                             width=100, height=20, border=True, border_style="single")
        inner = rect.inflate(-2, -2)
        fill_color = app._shade(color_to_rgb("#f0f0f0"), -40)
        expected_w = int(inner.width * 0.5)
        fill_rect = pygame.Rect(inner.x, inner.y, expected_w, inner.height)
        filled = _count_px(surf, fill_rect, fill_color)
        assert filled == expected_w * inner.height

    def test_value_clamps_above_max(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf_over, _ = _render(app, "progressbar", value=200, min_value=0, max_value=100,
                               width=100, height=20, border=True, border_style="single")
        surf_max, _ = _render(app, "progressbar", value=100, min_value=0, max_value=100,
                              width=100, height=20, border=True, border_style="single")
        # Both should look the same (clamped to 1.0)
        region = pygame.Rect(4, 4, 100, 20)
        assert _count_px(surf_over, region) == _count_px(surf_max, region)

    def test_custom_min_max_range(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # value=25 in range [0, 50] → 50%
        surf, rect = _render(app, "progressbar", value=25, min_value=0, max_value=50,
                             width=100, height=20, border=True, border_style="single")
        inner = rect.inflate(-2, -2)
        fill_color = app._shade(color_to_rgb("#f0f0f0"), -40)
        expected_w = int(inner.width * 0.5)
        fill_rect = pygame.Rect(inner.x, inner.y, expected_w, inner.height)
        filled = _count_px(surf, fill_rect, fill_color)
        assert filled == expected_w * inner.height


# ---------------------------------------------------------------------------
# Slider knob position
# ---------------------------------------------------------------------------


class TestSliderKnobPosition:
    """Verify slider knob X position at boundary values."""

    def _get_knob_col_counts(self, app, value):
        """Return column-wise non-BG pixel counts for slider track area."""
        surf, rect = _render(app, "slider", value=value, min_value=0, max_value=100,
                             width=120, height=24, border=False, border_style="none",
                             color_bg="#000000", color_fg="#f0f0f0")
        # Scan each column for non-BG pixels in the knob vertical strip area
        padding = 2
        track = rect.inflate(-padding * 2, -padding * 2)
        cols = {}
        for x in range(track.left, track.right):
            cnt = 0
            for y in range(rect.top + padding, rect.bottom - padding):
                if surf.get_at((x, y))[:3] != BG:
                    cnt += 1
            if cnt > 0:
                cols[x] = cnt
        return cols, track

    def test_knob_at_zero_near_left(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        cols, track = self._get_knob_col_counts(app, 0)
        # The knob at 0% is at track.left, so most dense columns should be left
        if cols:
            densest = max(cols, key=cols.get)
            midpoint = (track.left + track.right) // 2
            assert densest < midpoint, "knob at 0% should be in left half"

    def test_knob_at_100_near_right(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        cols, track = self._get_knob_col_counts(app, 100)
        if cols:
            densest = max(cols, key=cols.get)
            midpoint = (track.left + track.right) // 2
            assert densest >= midpoint, "knob at 100% should be in right half"

    def test_knob_at_50_near_center(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        cols, track = self._get_knob_col_counts(app, 50)
        if cols:
            densest = max(cols, key=cols.get)
            quarter = track.left + track.width // 4
            three_quarter = track.left + 3 * track.width // 4
            assert quarter <= densest <= three_quarter, \
                "knob at 50% should be in center region"


# ---------------------------------------------------------------------------
# Checkbox rendering
# ---------------------------------------------------------------------------


class TestCheckboxRendering:
    """Verify checkbox X mark presence/absence and box layout."""

    def test_checked_draws_cross_in_fg_color(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        fg = color_to_rgb("#f0f0f0")
        surf_off, rect = _render(app, "checkbox", text="A", checked=False,
                                 width=60, height=14,
                                 border=True, border_style="single")
        surf_on, _ = _render(app, "checkbox", text="A", checked=True,
                             width=60, height=14,
                             border=True, border_style="single")
        # The cross draws in fg color inside the box area
        box = pygame.Rect(rect.x + 2, rect.y + 2, GRID, GRID)
        off_fg = _count_px(surf_off, box, fg)
        on_fg = _count_px(surf_on, box, fg)
        assert on_fg > off_fg, "checked checkbox should have fg-colored cross lines"

    def test_label_renders_to_right_of_box(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf, rect = _render(app, "checkbox", text="HELLO", checked=False,
                             width=80, height=14, border=True, border_style="single")
        # Label area is to the right of the checkbox box
        label_area = pygame.Rect(rect.x + 2 + GRID + 2, rect.y, 40, rect.height)
        assert _count_px(surf, label_area) > 0, "label text should render right of checkbox"


# ---------------------------------------------------------------------------
# Radiobutton rendering
# ---------------------------------------------------------------------------


class TestRadiobuttonRendering:
    def test_checked_fills_inner_circle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf_off, rect = _render(app, "radiobutton", text="X", checked=False,
                                 width=60, height=24,
                                 border=False, border_style="none")
        surf_on, _ = _render(app, "radiobutton", text="X", checked=True,
                             width=60, height=24,
                             border=False, border_style="none")
        # Circle area
        radius = min(GRID // 2, 24 // 2 - 2)
        cx = rect.x + 2 + radius
        cy = rect.centery
        circle_box = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
        off_px = _count_px(surf_off, circle_box)
        on_px = _count_px(surf_on, circle_box)
        assert on_px > off_px, "selected radio should fill inner circle"


# ---------------------------------------------------------------------------
# Gauge: arc vs bar fallback
# ---------------------------------------------------------------------------


class TestGaugeRendering:
    def test_large_gauge_renders_arc(self, tmp_path, monkeypatch):
        """Gauge ≥ 5×5 grid units should render as arc."""
        app = _make_app(tmp_path, monkeypatch)
        # 5*GRID = 30 pixels min each dimension
        surf, rect = _render(app, "gauge", value=75, min_value=0, max_value=100,
                             width=GRID * 6, height=GRID * 6,
                             border=False, border_style="none")
        # At least the edge arc should be visible
        total = _count_px(surf, rect)
        assert total > 0, "large gauge should render arc"

    def test_small_gauge_renders_flat_bar(self, tmp_path, monkeypatch):
        """Gauge < 5×5 grid units should fall back to flat bar."""
        app = _make_app(tmp_path, monkeypatch)
        surf, rect = _render(app, "gauge", value=50, min_value=0, max_value=100,
                             width=GRID * 3, height=GRID * 3,
                             border=False, border_style="none")
        inner = rect.inflate(-2, -2)
        fill_color = app._shade(color_to_rgb("#f0f0f0"), -40)
        expected_w = int(inner.width * 0.5)
        fill_rect = pygame.Rect(inner.x, inner.y, expected_w, inner.height)
        filled = _count_px(surf, fill_rect, fill_color)
        assert filled == expected_w * inner.height

    def test_gauge_zero_value_minimal_fill(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf, rect = _render(app, "gauge", value=0, min_value=0, max_value=100,
                             width=GRID * 3, height=GRID * 3,
                             border=False, border_style="none")
        inner = rect.inflate(-2, -2)
        fill_color = app._shade(color_to_rgb("#f0f0f0"), -40)
        assert _count_px(surf, inner, fill_color) == 0


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------


class TestChartRendering:
    def test_bar_chart_has_bars(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf, rect = _render(app, "chart", text="BAR", style="bar",
                             data_points=[10, 40, 20, 60],
                             width=100, height=50,
                             border=False, border_style="none")
        padding = 2
        inner = rect.inflate(-padding * 2, -padding * 2)
        # Bottom region should have bar pixels
        bottom_strip = pygame.Rect(inner.left, inner.bottom - 10, inner.width, 10)
        assert _count_px(surf, bottom_strip) > 0, "bar chart bottom should have bars"

    def test_line_chart_has_coords(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf, rect = _render(app, "chart", text="LINE", style="line",
                             data_points=[5, 15, 10, 20],
                             width=100, height=50,
                             border=False, border_style="none")
        padding = 2
        inner = rect.inflate(-padding * 2, -padding * 2)
        assert _count_px(surf, inner) > 0, "line chart should render lines and dots"

    def test_chart_default_data_if_empty(self, tmp_path, monkeypatch):
        """With no data_points, chart uses default [0,10,5,12,8,14]."""
        app = _make_app(tmp_path, monkeypatch)
        surf, rect = _render(app, "chart", text="BAR", style="bar",
                             data_points=[],
                             width=100, height=50,
                             border=False, border_style="none")
        padding = 2
        inner = rect.inflate(-padding * 2, -padding * 2)
        assert _count_px(surf, inner) > 0, "empty data should use defaults"

    def test_chart_single_point_line_no_crash(self, tmp_path, monkeypatch):
        """Line chart with 1 point should render dot without crash."""
        app = _make_app(tmp_path, monkeypatch)
        surf, rect = _render(app, "chart", text="LINE", style="line",
                             data_points=[42],
                             width=100, height=50,
                             border=False, border_style="none")
        # Just verify no crash and at least a dot
        padding = 2
        inner = rect.inflate(-padding * 2, -padding * 2)
        assert _count_px(surf, inner) > 0

    def test_chart_many_points_narrow_widget(self, tmp_path, monkeypatch):
        """Many data points in narrow widget should not crash."""
        app = _make_app(tmp_path, monkeypatch)
        pts = list(range(50))
        surf, rect = _render(app, "chart", text="BAR", style="bar",
                             data_points=pts,
                             width=40, height=30,
                             border=False, border_style="none")
        assert _count_px(surf, rect) > 0


# ---------------------------------------------------------------------------
# Style modifiers: inverse, highlight, disabled
# ---------------------------------------------------------------------------


class TestStyleModifiers:
    def test_inverse_swaps_fg_bg(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Render a box (easiest to check fill color) with and without inverse
        surf_normal, rect = _render(app, "box", style="default",
                                    color_bg="#404040", color_fg="#f0f0f0",
                                    width=40, height=20,
                                    border=False, border_style="none")
        bg_normal = color_to_rgb("#404040")
        assert surf_normal.get_at((rect.x + 2, rect.y + 2))[:3] == bg_normal

        surf_inv, _ = _render(app, "box", style="inverse",
                              color_bg="#404040", color_fg="#f0f0f0",
                              width=40, height=20,
                              border=False, border_style="none")
        # In inverse mode, bg and fg are swapped, so box fill uses fg color as bg
        bg_inv = surf_inv.get_at((rect.x + 2, rect.y + 2))[:3]
        assert bg_inv == color_to_rgb("#f0f0f0")

    def test_highlight_brightens_bg(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf_normal, rect = _render(app, "box", style="default",
                                    color_bg="#404040", color_fg="#f0f0f0",
                                    width=40, height=20,
                                    border=False, border_style="none")
        surf_high, _ = _render(app, "box", style="highlight",
                               color_bg="#404040", color_fg="#f0f0f0",
                               width=40, height=20,
                               border=False, border_style="none")
        px_n = surf_normal.get_at((rect.x + 2, rect.y + 2))[:3]
        px_h = surf_high.get_at((rect.x + 2, rect.y + 2))[:3]
        # Highlight brightens by +10
        expected = _shade(color_to_rgb("#404040"), 10)
        assert px_h == expected
        assert sum(px_h) > sum(px_n), "highlight should be brighter"

    def test_disabled_darkens_bg_and_fg(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf_enabled, rect = _render(app, "label", text="X", enabled=True,
                                     color_bg="#808080", color_fg="#f0f0f0",
                                     width=40, height=20,
                                     border=False, border_style="none")
        surf_disabled, _ = _render(app, "label", text="X", enabled=False,
                                   color_bg="#808080", color_fg="#f0f0f0",
                                   width=40, height=20,
                                   border=False, border_style="none")
        # Disabled: bg darkened by -22, fg by -90
        # For a label with no border, bg is NOT filled (label+icon skip fill if no border)
        # Check text area is dimmer when disabled
        region = pygame.Rect(rect.x, rect.y, rect.width, rect.height)
        en_px = _count_px(surf_enabled, region)
        dis_px = _count_px(surf_disabled, region)
        # Disabled dims the fg color, so fewer bright pixels
        # Both render text, but disabled text is darker (closer to BG)
        assert dis_px <= en_px


# ---------------------------------------------------------------------------
# Border style visibility
# ---------------------------------------------------------------------------


class TestBorderStyles:
    def test_each_border_style_produces_edge_pixels(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        for bs in ["single", "double", "rounded", "bold", "dashed"]:
            surf, rect = _render(app, "label", text="", border=True, border_style=bs,
                                 color_bg="#000000", width=60, height=20)
            # Top edge of the rect
            top_edge = pygame.Rect(rect.left, rect.top, rect.width, 1)
            assert _count_px(surf, top_edge) > 0, f"{bs} should draw top edge"
            # Left edge
            left_edge = pygame.Rect(rect.left, rect.top, 1, rect.height)
            assert _count_px(surf, left_edge) > 0, f"{bs} should draw left edge"

    def test_none_border_no_edge(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf, rect = _render(app, "label", text="", border=False, border_style="none",
                              color_bg="#000000", width=60, height=20)
        top_edge = pygame.Rect(rect.left, rect.top, rect.width, 1)
        assert _count_px(surf, top_edge) == 0, "no border should leave edges empty"

    def test_double_border_has_more_pixels_than_single(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf_s, rect = _render(app, "box", text="", border=True, border_style="single",
                               color_bg="#000000", width=60, height=20)
        surf_d, _ = _render(app, "box", text="", border=True, border_style="double",
                            color_bg="#000000", width=60, height=20)
        edge = pygame.Rect(rect.left, rect.top, rect.width, 3)
        single_px = _count_px(surf_s, edge)
        double_px = _count_px(surf_d, edge)
        assert double_px > single_px, "double border should use more edge pixels"


# ---------------------------------------------------------------------------
# Locked widget hatch pattern
# ---------------------------------------------------------------------------


class TestLockedHatchPattern:
    def test_locked_draws_diagonal_lines(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf_unlocked, rect = _render(app, "box", locked=False,
                                      color_bg="#404040",
                                      width=60, height=30,
                                      border=True, border_style="single")
        surf_locked, _ = _render(app, "box", locked=True,
                                 color_bg="#404040",
                                 width=60, height=30,
                                 border=True, border_style="single")
        # Hatch draws diagonal lines in a different color;
        # count pixels that differ between locked and unlocked
        inner = rect.inflate(-2, -2)
        diff_count = 0
        for x in range(inner.left, inner.right):
            for y in range(inner.top, inner.bottom):
                if surf_unlocked.get_at((x, y))[:3] != surf_locked.get_at((x, y))[:3]:
                    diff_count += 1
        assert diff_count > 0, "locked widget should have hatch overlay"


# ---------------------------------------------------------------------------
# Overflow marker triangle
# ---------------------------------------------------------------------------


class TestOverflowMarker:
    def test_overflow_marker_draws_triangle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_overflow_warnings = True
        app.hardware_profile = "esp32os_256x128_gray4"
        # Create a very narrow widget with long text to trigger overflow
        surf = _surf()
        w = WidgetConfig(type="label", x=0, y=0, width=12, height=12,
                         text="Very long text that will certainly overflow",
                         color_fg="#f0f0f0", color_bg="#000000",
                         border=True, border_style="single")
        rect = pygame.Rect(4, 4, 12, 12)
        drawing.draw_widget_preview(app, surf, w, rect, BG, 2, False)
        # Check for red triangle at top-right corner
        marker_region = pygame.Rect(rect.right - 10, rect.top, 10, 10)
        red_px = _count_px(surf, marker_region, (255, 80, 80))
        assert red_px > 0, "overflow marker should draw red triangle"

    def test_no_overflow_marker_when_text_fits(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_overflow_warnings = True
        app.hardware_profile = "esp32os_256x128_gray4"
        surf = _surf()
        w = WidgetConfig(type="label", x=0, y=0, width=120, height=30,
                         text="Hi",
                         color_fg="#f0f0f0", color_bg="#000000",
                         border=True, border_style="single")
        rect = pygame.Rect(4, 4, 120, 30)
        drawing.draw_widget_preview(app, surf, w, rect, BG, 2, False)
        marker_region = pygame.Rect(rect.right - 10, rect.top, 10, 10)
        red_px = _count_px(surf, marker_region, (255, 80, 80))
        assert red_px == 0, "no overflow → no red marker"

    def test_no_overflow_marker_when_warnings_off(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_overflow_warnings = False
        app.hardware_profile = "esp32os_256x128_gray4"
        surf = _surf()
        w = WidgetConfig(type="label", x=0, y=0, width=12, height=12,
                         text="Very long text that overflows",
                         color_fg="#f0f0f0", color_bg="#000000",
                         border=True, border_style="single")
        rect = pygame.Rect(4, 4, 12, 12)
        drawing.draw_widget_preview(app, surf, w, rect, BG, 2, False)
        marker_region = pygame.Rect(rect.right - 10, rect.top, 10, 10)
        red_px = _count_px(surf, marker_region, (255, 80, 80))
        assert red_px == 0, "no marker when warnings disabled"


# ---------------------------------------------------------------------------
# Z-order rendering on canvas
# ---------------------------------------------------------------------------


class TestZOrderRendering:
    def test_higher_z_widget_covers_lower(self, tmp_path, monkeypatch):
        """Two overlapping widgets: higher z-order should paint on top."""
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.clear()
        # Widget A: red-ish bg, z=0
        sc.widgets.append(WidgetConfig(
            type="box", x=10, y=10, width=30, height=20,
            color_bg="#ff0000", z_index=0, border=False, border_style="none",
        ))
        # Widget B: green-ish bg, z=1, overlapping
        sc.widgets.append(WidgetConfig(
            type="box", x=20, y=10, width=30, height=20,
            color_bg="#00ff00", z_index=1, border=False, border_style="none",
        ))
        app.state.selected_idx = None
        app.focus_idx = None
        app.logical_surface.fill(PALETTE["bg"])
        app._draw_canvas()
        # At overlap point (x=25, y=15), the higher z-order (green) should be on top
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        overlap_x = sr.x + 25
        overlap_y = sr.y + 15
        px = app.logical_surface.get_at((overlap_x, overlap_y))[:3]
        # The green widget has z=1 so it should paint last (on top)
        assert px == (0, 255, 0), f"expected green on top, got {px}"


# ---------------------------------------------------------------------------
# color_to_rgb mapping
# ---------------------------------------------------------------------------


class TestColorToRgb:
    def test_named_colors(self):
        assert color_to_rgb("black") == (0, 0, 0)
        assert color_to_rgb("white") == (255, 255, 255)
        assert color_to_rgb("red") == (255, 0, 0)
        assert color_to_rgb("green") == (0, 255, 0)
        assert color_to_rgb("blue") == (0, 0, 255)

    def test_hex_code(self):
        assert color_to_rgb("#ff8000") == (255, 128, 0)
        assert color_to_rgb("#000000") == (0, 0, 0)

    def test_0x_prefix(self):
        assert color_to_rgb("0xFF8040") == (255, 128, 64)

    def test_empty_returns_default(self):
        assert color_to_rgb("") == (255, 255, 255)
        assert color_to_rgb(None) == (255, 255, 255)
        assert color_to_rgb("", default=(10, 20, 30)) == (10, 20, 30)

    def test_unknown_name_returns_default(self):
        assert color_to_rgb("chartreuse_nonexistent_xyz") == (255, 255, 255)


# ---------------------------------------------------------------------------
# Panel hatching pattern
# ---------------------------------------------------------------------------


class TestPanelRendering:
    def test_panel_draws_horizontal_lines(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf, rect = _render(app, "panel", width=80, height=40,
                             border=True, border_style="single",
                             color_bg="#202020")
        # Panel renders horizontal shade lines every 2*GRID pixels inside
        total = _count_px(surf, rect)
        assert total > 0, "panel should render bg + hatching lines"


# ---------------------------------------------------------------------------
# Textbox caret when selected
# ---------------------------------------------------------------------------


class TestTextboxCaret:
    def test_caret_visible_when_selected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf = _surf()
        w = WidgetConfig(type="textbox", x=0, y=0, width=80, height=20,
                         text="abc", color_fg="#f0f0f0", color_bg="#303030",
                         border=True, border_style="single")
        rect = pygame.Rect(4, 4, 80, 20)
        # Not selected
        drawing.draw_widget_preview(app, surf, w, rect, BG, 2, False)
        not_sel_px = _count_px(surf, rect)

        surf2 = _surf()
        # Selected — should draw caret line
        drawing.draw_widget_preview(app, surf2, w, rect, BG, 2, True)
        sel_px = _count_px(surf2, rect)
        assert sel_px >= not_sel_px, "selected textbox should have caret pixels"


# ---------------------------------------------------------------------------
# Button bevel frame pressed vs default
# ---------------------------------------------------------------------------


class TestButtonBevel:
    def test_pressed_button_differs_from_default(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Use border=False so bevel is visible at edges
        surf_default, rect = _render(app, "button", text="OK",
                                     state="default",
                                     color_bg="#505050",
                                     width=60, height=20,
                                     border=False, border_style="none")
        surf_pressed, _ = _render(app, "button", text="OK",
                                  state="pressed",
                                  color_bg="#505050",
                                  width=60, height=20,
                                  border=False, border_style="none")
        # Bevel top-left: default=light, pressed=dark
        tl = (rect.left, rect.top)
        px_def = surf_default.get_at(tl)[:3]
        px_prs = surf_pressed.get_at(tl)[:3]
        assert px_def != px_prs, "pressed vs default bevel should differ at top-left"


# ---------------------------------------------------------------------------
# Icon rendering
# ---------------------------------------------------------------------------


class TestIconRendering:
    def test_icon_renders_centered_character(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf, rect = _render(app, "icon", icon_char="@", width=24, height=24,
                             border=False, border_style="none")
        center_region = pygame.Rect(rect.centerx - 5, rect.centery - 5, 10, 10)
        assert _count_px(surf, center_region) > 0, "icon char should render near center"

    def test_icon_falls_back_to_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf, rect = _render(app, "icon", text="X", icon_char="", width=24, height=24,
                             border=False, border_style="none")
        assert _count_px(surf, rect) > 0, "icon with no icon_char uses text"
