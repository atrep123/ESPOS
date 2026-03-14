"""Tests for cyberpunk_designer/reporting.py — screenshot_canvas."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pygame

from cyberpunk_designer.reporting import screenshot_canvas


def _widget(**kw):
    defaults = dict(x=0, y=0, width=20, height=10, z_index=0, visible=True)
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _scene(widgets=None, width=256, height=128):
    return SimpleNamespace(widgets=widgets or [], width=width, height=height)


def _app(scene=None, pixel_padding=4):
    sc = scene or _scene()
    state = SimpleNamespace(current_scene=lambda: sc)
    app = MagicMock()
    app.state = state
    app.pixel_padding = pixel_padding
    app._draw_widget_preview = MagicMock()
    app._set_status = MagicMock()
    return app


class TestScreenshotCanvas:
    def test_saves_png(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        app = _app(_scene([_widget(x=10, y=10)]))
        screenshot_canvas(app)
        report_dir = tmp_path / "reports"
        assert report_dir.exists()
        pngs = list(report_dir.glob("*.png"))
        assert len(pngs) == 1
        assert pngs[0].name.endswith("_canvas.png")
        app._draw_widget_preview.assert_called_once()
        app._set_status.assert_called_once()
        assert "Saved" in app._set_status.call_args[0][0]

    def test_invisible_widget_skipped(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        w_vis = _widget(x=0, y=0, visible=True)
        w_invis = _widget(x=10, y=10, visible=False)
        app = _app(_scene([w_vis, w_invis]))
        screenshot_canvas(app)
        assert app._draw_widget_preview.call_count == 1

    def test_z_order_sorting(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        w_back = _widget(x=0, y=0, z_index=0)
        w_front = _widget(x=10, y=10, z_index=5)
        app = _app(_scene([w_front, w_back]))
        screenshot_canvas(app)
        calls = app._draw_widget_preview.call_args_list
        assert len(calls) == 2
        # z_index=0 drawn first, z_index=5 drawn second
        assert calls[0].kwargs["w"] is w_back
        assert calls[1].kwargs["w"] is w_front

    def test_empty_scene(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        app = _app(_scene([]))
        screenshot_canvas(app)
        app._draw_widget_preview.assert_not_called()
        pngs = list((tmp_path / "reports").glob("*.png"))
        assert len(pngs) == 1

    def test_oserror_handled(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        app = _app(_scene([_widget()]))
        with patch("cyberpunk_designer.reporting.pygame.image.save", side_effect=OSError("disk")):
            screenshot_canvas(app)
        app._set_status.assert_called_once()
        assert "failed" in app._set_status.call_args[0][0].lower()

    def test_pygame_error_handled(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        app = _app(_scene([_widget()]))
        with patch(
            "cyberpunk_designer.reporting.pygame.image.save",
            side_effect=pygame.error("surface"),
        ):
            screenshot_canvas(app)
        app._set_status.assert_called_once()
        assert "failed" in app._set_status.call_args[0][0].lower()

    def test_widget_minimum_size(self, tmp_path, monkeypatch):
        """Widgets with zero/None dimensions get clamped to 1."""
        monkeypatch.chdir(tmp_path)
        w = _widget(x=0, y=0, width=0, height=0)
        app = _app(_scene([w]))
        screenshot_canvas(app)
        call_kw = app._draw_widget_preview.call_args.kwargs
        rect = call_kw["rect"]
        assert rect.width >= 1
        assert rect.height >= 1


# ===================================================================
# BK – reporting edge cases
# ===================================================================


class TestScreenshotCanvasEdge:
    def test_large_scene(self, tmp_path, monkeypatch):
        """Screenshot with many widgets doesn't crash."""
        monkeypatch.chdir(tmp_path)
        widgets = [_widget(x=i * 10, y=0, z_index=i) for i in range(50)]
        app = _app(_scene(widgets))
        screenshot_canvas(app)
        assert app._draw_widget_preview.call_count == 50

    def test_widget_at_scene_edge(self, tmp_path, monkeypatch):
        """Widget at far edge of scene is still drawn."""
        monkeypatch.chdir(tmp_path)
        w = _widget(x=250, y=120, width=6, height=8)
        app = _app(_scene([w]))
        screenshot_canvas(app)
        app._draw_widget_preview.assert_called_once()

    def test_negative_z_index(self, tmp_path, monkeypatch):
        """Widget with negative z_index is drawn first."""
        monkeypatch.chdir(tmp_path)
        w_neg = _widget(x=0, y=0, z_index=-5)
        w_pos = _widget(x=10, y=0, z_index=5)
        app = _app(_scene([w_pos, w_neg]))
        screenshot_canvas(app)
        calls = app._draw_widget_preview.call_args_list
        assert calls[0].kwargs["w"] is w_neg
        assert calls[1].kwargs["w"] is w_pos

    def test_pixel_padding_minimum(self, tmp_path, monkeypatch):
        """pixel_padding=0 still produces pad >= 2."""
        monkeypatch.chdir(tmp_path)
        app = _app(_scene([_widget()]), pixel_padding=0)
        screenshot_canvas(app)
        call_kw = app._draw_widget_preview.call_args.kwargs
        assert call_kw["padding"] >= 2

    def test_all_invisible_produces_empty_png(self, tmp_path, monkeypatch):
        """If all widgets are invisible, PNG is created but no widgets drawn."""
        monkeypatch.chdir(tmp_path)
        w = _widget(visible=False)
        app = _app(_scene([w]))
        screenshot_canvas(app)
        app._draw_widget_preview.assert_not_called()
        pngs = list((tmp_path / "reports").glob("*.png"))
        assert len(pngs) == 1
