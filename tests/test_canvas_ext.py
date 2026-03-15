"""Extended tests for cyberpunk_designer/drawing/canvas.py — targeting
uncovered lines to push coverage from 74% to 85%+."""

from __future__ import annotations

import pygame

from cyberpunk_designer.drawing.canvas import (
    draw_canvas,
    draw_distance_indicators,
    draw_overflow_marker,
    draw_rulers,
    draw_widget_preview,
)
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add(app, **kw):
    defaults = dict(type="label", x=0, y=0, width=24, height=16, text="w")
    defaults.update(kw)
    sc = app.state.current_scene()
    sc.widgets.append(WidgetConfig(**defaults))
    return len(sc.widgets) - 1


# ---------------------------------------------------------------------------
# draw_canvas — center guides (lines 51-55)
# ---------------------------------------------------------------------------


class TestDrawCanvasCenterGuides:
    def test_center_guides_on(self, make_app):
        app = make_app()
        app.show_center_guides = True
        draw_canvas(app)

    def test_center_guides_off(self, make_app):
        app = make_app()
        app.show_center_guides = False
        draw_canvas(app)


# ---------------------------------------------------------------------------
# draw_canvas — active guides (lines 76-81)
# ---------------------------------------------------------------------------


class TestDrawCanvasActiveGuides:
    def test_vertical_guide(self, make_app):
        app = make_app()
        app.state.active_guides = [("v", 64)]
        draw_canvas(app)

    def test_horizontal_guide(self, make_app):
        app = make_app()
        app.state.active_guides = [("h", 32)]
        draw_canvas(app)

    def test_both_guides(self, make_app):
        app = make_app()
        app.state.active_guides = [("v", 64), ("h", 32)]
        draw_canvas(app)


# ---------------------------------------------------------------------------
# draw_canvas — widget ID labels (lines 121, 138-139)
# ---------------------------------------------------------------------------


class TestDrawCanvasWidgetLabels:
    def test_show_widget_ids(self, make_app):
        app = make_app()
        _add(app, text="label1")
        app.show_widget_ids = True
        draw_canvas(app)

    def test_show_z_labels(self, make_app):
        app = make_app()
        _add(app, text="z", z_index=5)
        app.show_z_labels = True
        draw_canvas(app)

    def test_show_both_labels(self, make_app):
        app = make_app()
        _add(app, text="both", z_index=3)
        app.show_widget_ids = True
        app.show_z_labels = True
        draw_canvas(app)


# ---------------------------------------------------------------------------
# draw_canvas — focus order overlay (lines 163-186)
# ---------------------------------------------------------------------------


class TestDrawCanvasFocusOrder:
    def test_focus_order_overlay(self, make_app):
        app = make_app()
        _add(app, type="button", text="btn1")
        _add(app, type="checkbox", text="chk1", x=40)
        _add(app, type="slider", text="sl1", x=80)
        app.show_focus_order = True
        draw_canvas(app)


# ---------------------------------------------------------------------------
# draw_canvas — scene_rect edge cases (lines 30, 34-35)
# ---------------------------------------------------------------------------


class TestDrawCanvasSceneRect:
    def test_no_scene_rect(self, make_app):
        """When scene_rect is not a pygame.Rect \u2192 fallback (line 30)."""
        app = make_app()
        app.scene_rect = None
        draw_canvas(app)

    def test_scene_rect_outside_canvas(self, make_app):
        """scene_rect outside canvas \u2192 clamped (lines 34-35)."""
        app = make_app()
        app.scene_rect = pygame.Rect(9999, 9999, 256, 128)
        draw_canvas(app)


# ---------------------------------------------------------------------------
# draw_canvas — selection info during resize/drag (lines 256-275)
# ---------------------------------------------------------------------------


class TestDrawCanvasSelectionInfo:
    def test_selection_resizing(self, make_app):
        app = make_app()
        idx = _add(app, text="resizable", x=0, y=0, width=40, height=32)
        app.state.selected = [idx]
        app.state.selected_idx = idx
        app.state.resizing = True
        draw_canvas(app)

    def test_selection_dragging(self, make_app):
        app = make_app()
        idx = _add(app, text="draggable", x=16, y=16, width=40, height=32)
        app.state.selected = [idx]
        app.state.selected_idx = idx
        app.state.dragging = True
        draw_canvas(app)


# ---------------------------------------------------------------------------
# draw_distance_indicators (lines 282-335)
# ---------------------------------------------------------------------------


class TestDrawDistanceIndicators:
    def test_indicators_basic(self, make_app):
        app = make_app()
        idx = _add(app, text="drag", x=40, y=32, width=24, height=16)
        app.state.selected = [idx]
        app.state.selected_idx = idx
        app.state.dragging = True
        sc = app.state.current_scene()
        sr = app.layout.canvas_rect
        draw_distance_indicators(app, sc, sr.x, sr.y, sr)

    def test_indicators_at_origin(self, make_app):
        """Widget at origin \u2192 left_d=0, top_d=0."""
        app = make_app()
        idx = _add(app, text="corner", x=0, y=0, width=24, height=16)
        app.state.selected = [idx]
        app.state.selected_idx = idx
        sc = app.state.current_scene()
        sr = app.layout.canvas_rect
        draw_distance_indicators(app, sc, sr.x, sr.y, sr)

    def test_indicators_at_far_corner(self, make_app):
        """Widget at far corner \u2192 right_d=0, bottom_d=0."""
        app = make_app()
        sc = app.state.current_scene()
        x = int(sc.width) - 24
        y = int(sc.height) - 16
        idx = _add(app, text="far", x=x, y=y, width=24, height=16)
        app.state.selected = [idx]
        app.state.selected_idx = idx
        sr = app.layout.canvas_rect
        draw_distance_indicators(app, sc, sr.x, sr.y, sr)

    def test_indicators_no_selection(self, make_app):
        app = make_app()
        sc = app.state.current_scene()
        sr = app.layout.canvas_rect
        draw_distance_indicators(app, sc, sr.x, sr.y, sr)


# ---------------------------------------------------------------------------
# draw_widget_preview — various widget types (line 456 = small gauge)
# ---------------------------------------------------------------------------


class TestDrawWidgetPreview:
    def _draw(self, app, **kw):
        defaults = dict(type="label", x=0, y=0, width=24, height=16, text="t")
        defaults.update(kw)
        w = WidgetConfig(**defaults)
        r = pygame.Rect(0, 0, int(w.width), int(w.height))
        draw_widget_preview(
            app,
            surface=app.logical_surface,
            w=w,
            rect=r,
            base_bg=(30, 30, 30),
            padding=2,
            is_selected=False,
        )

    def test_gauge_small(self, make_app):
        """Small gauge uses fallback bar rendering (line 456)."""
        app = make_app()
        self._draw(app, type="gauge", width=16, height=16, value=50)

    def test_gauge_large(self, make_app):
        app = make_app()
        self._draw(app, type="gauge", width=48, height=48, value=50)

    def test_checkbox_checked(self, make_app):
        app = make_app()
        self._draw(app, type="checkbox", checked=True, text="on")

    def test_slider(self, make_app):
        app = make_app()
        self._draw(app, type="slider", text="vol", value=75)

    def test_chart_bar(self, make_app):
        app = make_app()
        self._draw(app, type="chart", style="bar", text="bar chart", width=80, height=48)

    def test_chart_line(self, make_app):
        app = make_app()
        self._draw(app, type="chart", style="line", text="line chart", width=80, height=48)

    def test_textbox(self, make_app):
        app = make_app()
        w = WidgetConfig(type="textbox", x=0, y=0, width=80, height=24, text="input")
        r = pygame.Rect(0, 0, 80, 24)
        draw_widget_preview(
            app,
            surface=app.logical_surface,
            w=w,
            rect=r,
            base_bg=(30, 30, 30),
            padding=2,
            is_selected=True,
        )

    def test_radiobutton(self, make_app):
        app = make_app()
        self._draw(app, type="radiobutton", text="opt", checked=True)

    def test_radiobutton_unchecked(self, make_app):
        app = make_app()
        self._draw(app, type="radiobutton", text="opt", checked=False)

    def test_icon(self, make_app):
        app = make_app()
        self._draw(app, type="icon", text="@")

    def test_box(self, make_app):
        app = make_app()
        self._draw(app, type="box")

    def test_panel(self, make_app):
        app = make_app()
        self._draw(app, type="panel", width=48, height=48)

    def test_progressbar(self, make_app):
        app = make_app()
        self._draw(app, type="progressbar", value=60, text="60%")

    def test_button_pressed(self, make_app):
        app = make_app()
        self._draw(app, type="button", text="btn", state="pressed")

    def test_inverse_style(self, make_app):
        app = make_app()
        self._draw(app, type="label", style="inverse", text="inv")

    def test_highlight_style(self, make_app):
        app = make_app()
        self._draw(app, type="label", style="highlight", text="hi")

    def test_disabled(self, make_app):
        app = make_app()
        self._draw(app, type="label", enabled=False, text="off")

    def test_locked_with_border(self, make_app):
        app = make_app()
        self._draw(app, type="label", locked=True, border=True, text="locked")


# ---------------------------------------------------------------------------
# draw_overflow_marker (line 553)
# ---------------------------------------------------------------------------


class TestDrawOverflowMarker:
    def test_overflow_marker(self, make_app):
        app = make_app()
        surf = app.logical_surface
        r = pygame.Rect(10, 10, 40, 20)
        draw_overflow_marker(app, surf, r)

    def test_overflow_marker_zero_rect(self, make_app):
        app = make_app()
        draw_overflow_marker(app, app.logical_surface, pygame.Rect(0, 0, 0, 0))

    def test_overflow_marker_none_surface(self, make_app):
        app = make_app()
        draw_overflow_marker(app, None, pygame.Rect(0, 0, 10, 10))


# ---------------------------------------------------------------------------
# draw_canvas — overflow warnings (line 553)
# ---------------------------------------------------------------------------


class TestDrawCanvasOverflow:
    def test_overflow_warnings_enabled(self, make_app):
        app = make_app()
        app.show_overflow_warnings = True
        app.hardware_profile = "esp32os_256x128_gray4"
        # Add a widget with text that will overflow its tiny bounds
        _add(app, type="label", text="This is a very long text", width=8, height=8)
        draw_canvas(app)


# ---------------------------------------------------------------------------
# draw_canvas — sim_input_mode (lines 192, 200-214)
# ---------------------------------------------------------------------------


class TestDrawCanvasSimInputMode:
    def test_sim_input_mode_with_focus(self, make_app):
        app = make_app()
        _add(app, type="button", text="btn1")
        app.sim_input_mode = True
        app._ensure_focus()
        draw_canvas(app)

    def test_sim_input_mode_editing_value(self, make_app):
        app = make_app()
        _add(app, type="slider", text="vol")
        app.sim_input_mode = True
        app._ensure_focus()
        app.focus_edit_value = True
        draw_canvas(app)


# ---------------------------------------------------------------------------
# draw_canvas — box select / hover highlight
# ---------------------------------------------------------------------------


class TestDrawCanvasBoxSelect:
    def test_box_select_rect(self, make_app):
        app = make_app()
        app.state.box_select_rect = pygame.Rect(20, 20, 60, 40)
        draw_canvas(app)

    def test_hover_highlight(self, make_app):
        """Hover over unselected widget draws dashed outline."""
        app = make_app()
        _add(app, text="hover_me", x=40, y=32, width=40, height=24)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        # Position pointer over the widget
        app.pointer_pos = (sr.x + 50, sr.y + 40)
        app.pointer_down = False
        app.sim_input_mode = False
        draw_canvas(app)


# ---------------------------------------------------------------------------
# draw_rulers (line 231, 241)
# ---------------------------------------------------------------------------


class TestDrawRulers:
    def test_rulers(self, make_app):
        app = make_app()
        sr = pygame.Rect(0, 0, 256, 128)
        draw_rulers(app, sr, 256, 128)
