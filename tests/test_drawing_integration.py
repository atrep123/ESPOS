"""Integration tests for the drawing pipeline.

Exercises the full render cycle (draw_canvas → panels → toolbar → overlays)
to verify that the drawing package works as a cohesive unit without crashes.
"""

from __future__ import annotations

import pygame
import pytest

from cyberpunk_designer.drawing import (
    draw_canvas,
    draw_distance_indicators,
    draw_inspector,
    draw_overflow_marker,
    draw_palette,
    draw_rulers,
    draw_scene_tabs,
    draw_selection_info,
    draw_status,
    draw_toolbar,
)
from cyberpunk_editor import CyberpunkEditorApp
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app(tmp_path, monkeypatch, *, widgets=None, profile=None):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    app = CyberpunkEditorApp(json_path, (256, 128), profile=profile)
    if widgets:
        sc = app.state.current_scene()
        for w in widgets:
            sc.widgets.append(w)
    return app


def _w(**kw):
    defaults = dict(type="label", x=10, y=10, width=40, height=16, text="Test")
    defaults.update(kw)
    return WidgetConfig(**defaults)


# ---------------------------------------------------------------------------
# Full frame render cycle
# ---------------------------------------------------------------------------

class TestFullFrameRender:
    """Render canvas + panels + toolbar + status in a single frame cycle."""

    def test_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_canvas(app)
        draw_palette(app)
        draw_inspector(app)
        draw_toolbar(app)
        draw_status(app)
        draw_scene_tabs(app)

    def test_scene_with_widgets(self, tmp_path, monkeypatch):
        widgets = [
            _w(type="label", x=5, y=5, width=60, height=12, text="Title"),
            _w(type="button", x=5, y=25, width=50, height=14, text="OK"),
            _w(type="progressbar", x=5, y=45, width=80, height=8, value=50),
            _w(type="checkbox", x=5, y=60, width=60, height=12, checked=True),
            _w(type="gauge", x=100, y=5, width=30, height=30, value=75),
        ]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        draw_canvas(app)
        draw_palette(app)
        draw_inspector(app)
        draw_toolbar(app)
        draw_status(app)

    def test_scene_with_selection(self, tmp_path, monkeypatch):
        widgets = [_w(), _w(x=60, y=10), _w(x=120, y=10)]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        app.state.selected = [0, 2]
        app.state.selected_idx = 0
        draw_canvas(app)
        draw_inspector(app)

    def test_scene_with_grid_and_rulers(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.show_grid = True
        app.show_rulers = True
        app.show_center_guides = True
        draw_canvas(app)


# ---------------------------------------------------------------------------
# Widget type coverage
# ---------------------------------------------------------------------------

class TestAllWidgetTypes:
    """Ensure every widget type renders without error."""

    @pytest.mark.parametrize("wtype", [
        "label", "button", "panel", "progressbar", "gauge",
        "slider", "checkbox", "textbox", "chart", "list",
        "toggle", "icon",
    ])
    def test_widget_type_renders(self, tmp_path, monkeypatch, wtype):
        kw = dict(type=wtype, x=5, y=5, width=50, height=20)
        if wtype in ("progressbar", "gauge", "slider"):
            kw["value"] = 42
        if wtype == "checkbox":
            kw["checked"] = True
        if wtype == "chart":
            kw["data_points"] = [10, 30, 20, 50, 40]
        if wtype == "icon":
            kw["icon_char"] = "A"
        if wtype == "list":
            kw["text"] = "one\ntwo\nthree"
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(**kw)])
        draw_canvas(app)


# ---------------------------------------------------------------------------
# Drawing helper functions
# ---------------------------------------------------------------------------

class TestDrawingHelpers:
    def test_rulers_render(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sr = pygame.Rect(0, 0, 256, 128)
        draw_rulers(app, sr, 256, 128)

    def test_selection_info_dragging(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.dragging = True
        from types import SimpleNamespace
        bounds = SimpleNamespace(x=10, y=10, width=40, height=16)
        sel_rect = pygame.Rect(10, 10, 40, 16)
        sr = pygame.Rect(0, 0, 256, 128)
        draw_selection_info(app, sel_rect, bounds, sr)

    def test_selection_info_resizing(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.resizing = True
        from types import SimpleNamespace
        bounds = SimpleNamespace(x=10, y=10, width=40, height=16)
        sel_rect = pygame.Rect(10, 10, 40, 16)
        sr = pygame.Rect(0, 0, 256, 128)
        draw_selection_info(app, sel_rect, bounds, sr)

    def test_distance_indicators(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=40, y=32)])
        idx = 0
        app.state.selected = [idx]
        app.state.selected_idx = idx
        app.state.dragging = True
        sc = app.state.current_scene()
        sr = app.layout.canvas_rect
        draw_distance_indicators(app, sc, sr.x, sr.y, sr)

    def test_overflow_marker(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf = app.logical_surface
        rect = pygame.Rect(10, 10, 30, 20)
        draw_overflow_marker(app, surf, rect)

    def test_overflow_marker_tiny_rect(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf = app.logical_surface
        rect = pygame.Rect(0, 0, 0, 0)
        draw_overflow_marker(app, surf, rect)


# ---------------------------------------------------------------------------
# Profile-specific rendering
# ---------------------------------------------------------------------------

class TestProfileRendering:
    def test_esp32os_profile(self, tmp_path, monkeypatch):
        widgets = [
            _w(type="label", x=0, y=0, width=100, height=12, text="ESP32"),
            _w(type="button", x=0, y=20, width=60, height=14, text="Go"),
        ]
        app = _make_app(
            tmp_path, monkeypatch, widgets=widgets,
            profile="esp32os_256x128_gray4",
        )
        draw_canvas(app)
        draw_palette(app)
        draw_inspector(app)


# ---------------------------------------------------------------------------
# Multiple scene tabs
# ---------------------------------------------------------------------------

class TestMultiScene:
    def test_render_with_multiple_scenes(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.designer.create_scene("second")
        sc2 = app.designer.scenes["second"]
        sc2.width, sc2.height = 256, 128
        draw_scene_tabs(app)
        draw_canvas(app)
