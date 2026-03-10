"""Tests for windowing advanced functions and live_preview framing.

Covers: compute_scale, rebuild_layout, hardware_accelerated_scale,
        handle_video_resize, toggle_fullscreen, live_preview frame format,
        refresh_available_ports.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from cyberpunk_designer import live_preview, windowing
from cyberpunk_designer.layout import Layout
from cyberpunk_editor import CyberpunkEditorApp

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path, monkeypatch, *, width=256, height=128, profile=None):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    return CyberpunkEditorApp(json_path, (width, height), profile=profile)


def _stub_app(
    *,
    scale=1,
    width=256,
    height=128,
    palette_w=120,
    inspector_w=200,
    toolbar_h=24,
    status_h=18,
    scene_tabs_h=0,
    max_auto_scale=4,
    panels_collapsed=False,
):
    """Lightweight app-like dictionary for pure windowing math functions."""
    designer = SimpleNamespace(width=width, height=height)
    app = SimpleNamespace(
        designer=designer,
        scale=scale,
        max_auto_scale=max_auto_scale,
        toolbar_h=toolbar_h,
        status_h=status_h,
        scene_tabs_h=scene_tabs_h,
        panels_collapsed=panels_collapsed,
        _default_palette_w=palette_w,
        _default_inspector_w=inspector_w,
    )
    return app


# ---------------------------------------------------------------------------
# compute_scale
# ---------------------------------------------------------------------------
class TestComputeScale:
    def test_with_force_window(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        s = windowing.compute_scale(app, force_window=(800, 600))
        assert isinstance(s, int)
        assert s >= 1

    def test_small_window_gives_scale_1(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        s = windowing.compute_scale(app, force_window=(256, 128))
        assert s == 1

    def test_larger_window_may_increase_scale(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        s1 = windowing.compute_scale(app, force_window=(256, 128))
        s2 = windowing.compute_scale(app, force_window=(2560, 1440))
        assert s2 >= s1

    def test_panels_collapsed_allows_higher_scale(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        s1 = windowing.compute_scale(app, force_window=(800, 600))
        app.panels_collapsed = True
        s2 = windowing.compute_scale(app, force_window=(800, 600))
        assert s2 >= s1


# ---------------------------------------------------------------------------
# rebuild_layout
# ---------------------------------------------------------------------------
class TestRebuildLayout:
    def test_creates_layout_and_surface(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        windowing.rebuild_layout(app, window_size=(800, 600))
        assert isinstance(app.layout, Layout)
        assert app.logical_surface is not None
        assert app.logical_surface.get_width() > 0

    def test_scene_rect_exists(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        windowing.rebuild_layout(app, window_size=(800, 600))
        assert hasattr(app, "scene_rect")
        assert app.scene_rect.width > 0

    def test_lock_scale(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        windowing.rebuild_layout(app, window_size=(1600, 900), lock_scale=2)
        assert app.scale <= 2

    def test_window_resizes(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        windowing.rebuild_layout(app, window_size=(1024, 768))
        w1, h1 = app.window.get_size()
        assert w1 >= 1 and h1 >= 1


# ---------------------------------------------------------------------------
# handle_video_resize
# ---------------------------------------------------------------------------
class TestHandleVideoResize:
    def test_resize_updates_layout(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        windowing.handle_video_resize(app, 1200, 800)
        # Layout should be rebuilt (may or may not change size)
        assert isinstance(app.layout, Layout)

    def test_locked_scale_preserved(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._scale_locked = True
        app.scale = 1
        windowing.handle_video_resize(app, 1200, 800)
        assert app.scale == 1


# ---------------------------------------------------------------------------
# hardware_accelerated_scale
# ---------------------------------------------------------------------------
class TestHardwareAcceleratedScale:
    def test_sets_render_offsets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        windowing.hardware_accelerated_scale(app)
        assert hasattr(app, "_render_offset_x")
        assert hasattr(app, "_render_offset_y")
        assert app._render_scale_x >= 1.0
        assert app._render_scale_y >= 1.0

    def test_render_scale_matches_scale(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.scale = 1
        windowing.hardware_accelerated_scale(app)
        assert app._render_scale_x == 1.0


# ---------------------------------------------------------------------------
# live_preview framing
# ---------------------------------------------------------------------------
class TestLivePreviewFrame:
    """Test frame construction and error handling in send_live_preview."""

    def test_no_port_sets_status(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.live_preview_port = ""
        statuses = []
        app._set_status = lambda msg, **kw: statuses.append(msg)
        live_preview.send_live_preview(app)
        assert any("set ESP32OS" in s or "live_port" in s for s in statuses)

    def test_missing_pyserial_sets_status(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.live_preview_port = "COM99"
        statuses = []
        app._set_status = lambda msg, **kw: statuses.append(msg)
        # Simulate pyserial missing
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *a, **kw):
            if name == "serial":
                raise ImportError("no serial")
            return real_import(name, *a, **kw)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        live_preview.send_live_preview(app)
        assert any("pyserial" in s for s in statuses)

    def test_frame_format_with_mock_serial(self, tmp_path, monkeypatch):
        """Verify <<UIJSON>>...<<END>> framing."""
        app = _make_app(tmp_path, monkeypatch)
        # Write a real JSON to the file
        data = {"name": "test", "width": 256, "height": 128, "widgets": []}
        app.json_path.write_text(json.dumps(data), encoding="utf-8")
        app.live_preview_port = "COM99"
        app.live_preview_baud = 115200
        statuses = []
        app._set_status = lambda msg, **kw: statuses.append(msg)

        written_data = []
        mock_ser = MagicMock()
        mock_ser.write = lambda d: written_data.append(d)
        mock_ser.flush = MagicMock()
        mock_ser.__enter__ = lambda s: s
        mock_ser.__exit__ = MagicMock(return_value=False)

        mock_serial_mod = MagicMock()
        mock_serial_mod.Serial.return_value = mock_ser

        monkeypatch.setitem(__import__("sys").modules, "serial", mock_serial_mod)

        live_preview.send_live_preview(app)

        assert len(written_data) == 1
        frame = written_data[0]
        assert frame.startswith(b"<<UIJSON>>")
        assert frame.endswith(b"<<END>>")
        # Payload should be valid JSON
        payload = frame[len(b"<<UIJSON>>") : -len(b"<<END>>")]
        parsed = json.loads(payload.decode("utf-8"))
        assert parsed["name"] == "test"


class TestRefreshAvailablePorts:
    def test_no_pyserial_empty(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        statuses = []
        app._set_status = lambda msg, **kw: statuses.append(msg)
        # Guarantee pyserial is missing
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *a, **kw):
            if "serial" in name:
                raise ImportError("no serial")
            return real_import(name, *a, **kw)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        live_preview.refresh_available_ports(app)
        assert app.available_ports == []

    def test_with_mocked_ports(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        statuses = []
        app._set_status = lambda msg, **kw: statuses.append(msg)

        port1 = SimpleNamespace(device="COM3")
        port2 = SimpleNamespace(device="/dev/ttyUSB0")

        mock_list_ports = MagicMock()
        mock_list_ports.comports.return_value = [port1, port2]
        mock_serial_tools = MagicMock()
        mock_serial_tools.list_ports = mock_list_ports
        mock_serial = MagicMock()
        mock_serial.tools = mock_serial_tools

        monkeypatch.setitem(__import__("sys").modules, "serial", mock_serial)
        monkeypatch.setitem(__import__("sys").modules, "serial.tools", mock_serial_tools)
        monkeypatch.setitem(__import__("sys").modules, "serial.tools.list_ports", mock_list_ports)

        live_preview.refresh_available_ports(app)
        assert "COM3" in app.available_ports
        assert "/dev/ttyUSB0" in app.available_ports
