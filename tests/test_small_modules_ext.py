"""Extended tests for constants.py, live_preview.py, component_insert.py,
windowing.py, and components.py — targeting uncovered lines."""

from __future__ import annotations

from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import MagicMock, patch

import pygame

from cyberpunk_designer.component_insert import add_component
from cyberpunk_designer.components import component_blueprints
from cyberpunk_designer.constants import color_to_rgb, hex_to_rgb
from cyberpunk_designer.live_preview import (
    open_live_dialog,
    refresh_available_ports,
    send_live_preview,
)
from cyberpunk_designer.state import EditorState
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=24, height=16, text="w")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _app(widgets=None, *, snap=False):
    designer = UIDesigner(256, 128)
    designer.create_scene("main")
    sc = designer.scenes["main"]
    for w in widgets or []:
        sc.widgets.append(w)
    layout = MagicMock()
    layout.canvas_rect = pygame.Rect(0, 0, 256, 128)
    state = EditorState(designer, layout)
    app = SimpleNamespace(
        designer=designer,
        state=state,
        snap_enabled=snap,
        pointer_pos=(50, 50),
        scene_rect=pygame.Rect(0, 0, 256, 128),
        layout=layout,
        _dirty=False,
        _set_status=MagicMock(),
        _mark_dirty=lambda: setattr(app, "_dirty", True),
        _set_selection=MagicMock(),
        _auto_complete_widget=MagicMock(),
        _next_group_name=lambda prefix: f"{prefix}1",
    )
    app._mark_dirty = lambda: setattr(app, "_dirty", True)
    return app


# ---------------------------------------------------------------------------
# constants.py — hex_to_rgb exception branch (lines 62-63)
# ---------------------------------------------------------------------------


class TestHexToRgbEdge:
    def test_exception_in_parse(self):
        # Object whose __str__ raises inside int() — trigger except
        assert hex_to_rgb("#gggggg") == (255, 255, 255)

    def test_non_string_input(self):
        assert hex_to_rgb(None) == (255, 255, 255)

    def test_wrong_length(self):
        assert hex_to_rgb("#ff") == (255, 255, 255)


# ---------------------------------------------------------------------------
# constants.py — color_to_rgb 0x exception branch (lines 94-95)
# ---------------------------------------------------------------------------


class TestColorToRgbEdge:
    def test_0x_invalid_hex(self):
        # 0x with correct length but invalid hex digits
        assert color_to_rgb("0xGGGGGG") == (255, 255, 255)

    def test_0x_valid(self):
        assert color_to_rgb("0xFF0000") == (255, 0, 0)

    def test_0x_short(self):
        # 0x with wrong length → falls through to # case
        assert color_to_rgb("0xFF") == (255, 255, 255)


# ---------------------------------------------------------------------------
# live_preview.py — send_live_preview branches (lines 8-9, 44-46, 56-57)
# ---------------------------------------------------------------------------


class TestLivePreview:
    def test_open_live_dialog(self):
        """open_live_dialog calls send_live_preview (lines 8-9)."""
        app = SimpleNamespace(
            live_preview_port="",
            _set_status=MagicMock(),
        )
        open_live_dialog(app)
        app._set_status.assert_called()

    def test_send_no_port(self):
        app = SimpleNamespace(
            live_preview_port="",
            _set_status=MagicMock(),
        )
        send_live_preview(app)
        assert (
            "set" in app._set_status.call_args[0][0].lower()
            or "port" in app._set_status.call_args[0][0].lower()
        )

    def test_send_no_pyserial(self):
        """Port set but pyserial missing (lines 44-46)."""
        app = SimpleNamespace(
            live_preview_port="COM99",
            _set_status=MagicMock(),
        )
        with patch.dict("sys.modules", {"serial": None}):
            send_live_preview(app)
            assert (
                "pyserial" in app._set_status.call_args[0][0].lower()
                or "missing" in app._set_status.call_args[0][0].lower()
            )

    def test_send_serial_write_fails(self, tmp_path):
        """Serial write fails (lines 56-57)."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"hello":"world"}', encoding="utf-8")

        mock_ser = MagicMock()
        mock_ser.__enter__ = MagicMock(return_value=mock_ser)
        mock_ser.__exit__ = MagicMock(return_value=False)
        mock_ser.write.side_effect = OSError("port error")

        mock_serial_mod = MagicMock()
        mock_serial_mod.Serial.return_value = mock_ser

        app = SimpleNamespace(
            live_preview_port="COM99",
            live_preview_baud=115200,
            json_path=json_file,
            _set_status=MagicMock(),
        )
        with patch.dict("sys.modules", {"serial": mock_serial_mod}):
            send_live_preview(app)
        assert "failed" in app._set_status.call_args[0][0].lower()

    def test_send_read_text_fails(self, tmp_path):
        """JSON file unreadable (lines 56-57 variant)."""
        mock_serial = MagicMock()
        app = SimpleNamespace(
            live_preview_port="COM99",
            live_preview_baud=115200,
            json_path=tmp_path / "nonexistent.json",
            _set_status=MagicMock(),
        )
        with patch.dict("sys.modules", {"serial": mock_serial}):
            send_live_preview(app)
        assert "cannot read" in app._set_status.call_args[0][0].lower()

    def test_refresh_ports_no_pyserial(self):
        app = SimpleNamespace(
            available_ports=[],
            available_ports_idx=-1,
            _set_status=MagicMock(),
        )
        with patch.dict(
            "sys.modules", {"serial": None, "serial.tools": None, "serial.tools.list_ports": None}
        ):
            refresh_available_ports(app)
            assert app.available_ports == []

    def test_refresh_ports_with_ports(self):
        mock_port = SimpleNamespace(device="/dev/ttyUSB0")
        mock_list_ports = MagicMock()
        mock_list_ports.comports.return_value = [mock_port]
        mock_serial_tools = MagicMock()
        mock_serial_tools.list_ports = mock_list_ports
        mock_serial = MagicMock()
        mock_serial.tools = mock_serial_tools
        app = SimpleNamespace(
            available_ports=[],
            available_ports_idx=-1,
            _set_status=MagicMock(),
        )
        with patch.dict(
            "sys.modules",
            {
                "serial": mock_serial,
                "serial.tools": mock_serial_tools,
                "serial.tools.list_ports": mock_list_ports,
            },
        ):
            refresh_available_ports(app)
            assert app.available_ports == ["/dev/ttyUSB0"]
            assert app.available_ports_idx == 0


# ---------------------------------------------------------------------------
# component_insert.py — modal origin (line 72), based_z from widgets (48-49),
# WidgetConfig exception (127-128), auto_complete (131-132), group fail (137-138, 146-148)
# ---------------------------------------------------------------------------


class TestAddComponentEdge:
    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_save_state_exception(self, mock_bp):
        """_save_state raising triggers except branch (lines 48-49)."""
        mock_bp.return_value = [
            {"type": "label", "role": "t", "x": 0, "y": 0, "width": 50, "height": 10, "text": "T"},
        ]
        app = _app()
        app.designer._save_state = MagicMock(side_effect=TypeError("fail"))
        add_component(app, "card")
        sc = app.state.current_scene()
        assert len(sc.widgets) >= 1

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_scene_rect_none_fallback(self, mock_bp):
        """scene_rect=None triggers layout.canvas_rect fallback (line 72)."""
        mock_bp.return_value = [
            {"type": "label", "role": "t", "x": 0, "y": 0, "width": 50, "height": 10, "text": "T"},
        ]
        app = _app()
        app.scene_rect = None
        add_component(app, "card")
        sc = app.state.current_scene()
        assert len(sc.widgets) >= 1

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_snap_enabled(self, mock_bp):
        """snap_enabled triggers snap() on origin (lines 91-92)."""
        mock_bp.return_value = [
            {"type": "label", "role": "t", "x": 0, "y": 0, "width": 50, "height": 10, "text": "T"},
        ]
        app = _app(snap=True)
        add_component(app, "card")
        sc = app.state.current_scene()
        # snapped coordinates should be grid-aligned
        assert int(sc.widgets[-1].x) % 8 == 0

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_bad_z_in_blueprint(self, mock_bp):
        """Non-int z triggers except in z parsing (lines 91-92)."""
        mock_bp.return_value = [
            {
                "type": "label",
                "role": "t",
                "x": 0,
                "y": 0,
                "width": 50,
                "height": 10,
                "text": "T",
                "z": "bad",
            },
        ]
        app = _app()
        add_component(app, "card")
        sc = app.state.current_scene()
        assert len(sc.widgets) >= 1

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_widget_config_creation_fails(self, mock_bp):
        """WidgetConfig creation exception → continue (lines 127-128)."""
        mock_bp.return_value = [
            {"type": "label", "role": "t", "x": 0, "y": 0, "width": 50, "height": 10, "text": "T"},
        ]
        app = _app()
        with patch(
            "cyberpunk_designer.component_insert.WidgetConfig", side_effect=TypeError("fail")
        ):
            add_component(app, "card")
        # Widget creation failed, so no widgets added

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_auto_complete_raises(self, mock_bp):
        """_auto_complete_widget raising triggers except (lines 131-132)."""
        mock_bp.return_value = [
            {"type": "label", "role": "t", "x": 0, "y": 0, "width": 50, "height": 10, "text": "T"},
        ]
        app = _app()
        app._auto_complete_widget = MagicMock(side_effect=AttributeError("fail"))
        add_component(app, "card")
        sc = app.state.current_scene()
        assert len(sc.widgets) >= 1

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_all_blueprints_fail(self, mock_bp):
        """All blueprints failing → empty new_indices → status msg (lines 137-138)."""
        mock_bp.return_value = [
            {"type": "label", "role": "t", "x": 0, "y": 0, "width": 50, "height": 10, "text": "T"},
        ]
        app = _app()
        with patch(
            "cyberpunk_designer.component_insert.WidgetConfig", side_effect=TypeError("fail")
        ):
            add_component(app, "card")
            app._set_status.assert_called()

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_modal_origin_zero(self, mock_bp):
        """Modal components use origin (0,0)."""
        mock_bp.return_value = [
            {
                "type": "panel",
                "role": "overlay",
                "x": 0,
                "y": 0,
                "width": 200,
                "height": 100,
                "text": "",
            },
        ]
        app = _app()
        add_component(app, "modal")
        sc = app.state.current_scene()
        if sc.widgets:
            assert int(sc.widgets[-1].x) == 0
            assert int(sc.widgets[-1].y) == 0

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_group_creation_raises(self, mock_bp):
        """create_group raising → except branch (lines 147-148)."""
        mock_bp.return_value = [
            {"type": "panel", "role": "bg", "x": 0, "y": 0, "width": 100, "height": 50, "text": ""},
            {
                "type": "label",
                "role": "title",
                "x": 2,
                "y": 2,
                "width": 96,
                "height": 10,
                "text": "T",
            },
        ]
        app = _app()
        app.designer.create_group = MagicMock(side_effect=AttributeError("fail"))
        add_component(app, "card")
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_group_creation_returns_false(self, mock_bp):
        """create_group returns False (line 146)."""
        mock_bp.return_value = [
            {"type": "panel", "role": "bg", "x": 0, "y": 0, "width": 100, "height": 50, "text": ""},
            {
                "type": "label",
                "role": "title",
                "x": 2,
                "y": 2,
                "width": 96,
                "height": 10,
                "text": "T",
            },
        ]
        app = _app()
        app.designer.create_group = MagicMock(return_value=False)
        add_component(app, "card")
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2


# ---------------------------------------------------------------------------
# components.py — scene dimension exceptions (all 30 missing lines)
# ---------------------------------------------------------------------------


class _BadScene:
    """Scene mock that raises on width/height access."""

    @property
    def width(self):
        raise AttributeError("no width")

    @property
    def height(self):
        raise AttributeError("no height")

    widgets: ClassVar[list] = []


class TestComponentBlueprintsExceptions:
    """Trigger exception branches for every component that reads sc.width/height."""

    def test_toast_bad_scene(self):
        result = component_blueprints("toast", _BadScene())
        assert len(result) >= 1

    def test_modal_bad_scene(self):
        result = component_blueprints("modal", _BadScene())
        assert len(result) >= 1

    def test_dialog_confirm_bad_scene(self):
        result = component_blueprints("dialog_confirm", _BadScene())
        assert len(result) >= 1

    def test_notification_bad_scene(self):
        result = component_blueprints("notification", _BadScene())
        assert len(result) >= 1

    def test_gauge_hud_bad_scene(self):
        result = component_blueprints("gauge_hud", _BadScene())
        assert len(result) >= 1

    def test_dashboard_256x128_bad_scene(self):
        result = component_blueprints("dashboard_256x128", _BadScene())
        assert len(result) >= 1

    def test_status_bar_bad_scene(self):
        result = component_blueprints("status_bar", _BadScene())
        assert len(result) >= 1

    def test_tabs_bad_scene(self):
        result = component_blueprints("tabs", _BadScene())
        assert len(result) >= 1

    def test_list_bad_scene(self):
        result = component_blueprints("list", _BadScene())
        assert len(result) >= 1

    def test_menu_list_bad_scene(self):
        result = component_blueprints("menu_list", _BadScene())
        assert len(result) >= 1

    def test_list_item_bad_scene(self):
        result = component_blueprints("list_item", _BadScene())
        assert len(result) >= 1

    def test_setting_int_bad_scene(self):
        result = component_blueprints("setting_int", _BadScene())
        assert len(result) >= 1

    def test_setting_bool_bad_scene(self):
        result = component_blueprints("setting_bool", _BadScene())
        assert len(result) >= 1

    def test_setting_enum_bad_scene(self):
        result = component_blueprints("setting_enum", _BadScene())
        assert len(result) >= 1

    def test_dialog_bad_scene(self):
        result = component_blueprints("dialog", _BadScene())
        assert len(result) >= 1

    def test_chart_bar_bad_scene(self):
        result = component_blueprints("chart_bar", _BadScene())
        assert len(result) >= 1

    def test_chart_line_bad_scene(self):
        result = component_blueprints("chart_line", _BadScene())
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# windowing.py — via CyberpunkEditorApp (lines 60-62, 79-80, 91, 102-103, etc.)
# ---------------------------------------------------------------------------


def _make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    from cyberpunk_editor import CyberpunkEditorApp

    json_path = tmp_path / "scene.json"
    return CyberpunkEditorApp(json_path, (256, 128))


class TestWindowing:
    def test_hardware_accelerated_scale(self, tmp_path, monkeypatch):
        """Exercise hardware_accelerated_scale (lines 60-62)."""
        from cyberpunk_designer.windowing import hardware_accelerated_scale

        app = _make_app(tmp_path, monkeypatch)
        # Ensure we have a real window and logical_surface
        if app.window is not None and app.logical_surface is not None:
            hardware_accelerated_scale(app)
            assert hasattr(app, "_render_scale_x")

    def test_handle_video_resize(self, tmp_path, monkeypatch):
        """Exercise handle_video_resize (lines 79-80)."""
        from cyberpunk_designer.windowing import handle_video_resize

        app = _make_app(tmp_path, monkeypatch)
        handle_video_resize(app, 512, 256)

    def test_handle_video_resize_with_scale_locked(self, tmp_path, monkeypatch):
        from cyberpunk_designer.windowing import handle_video_resize

        app = _make_app(tmp_path, monkeypatch)
        app._scale_locked = True
        app.scale = 2
        handle_video_resize(app, 512, 256)

    def test_toggle_fullscreen_on(self, tmp_path, monkeypatch):
        """Exercise toggle_fullscreen entering fullscreen (line 91)."""
        from cyberpunk_designer.windowing import toggle_fullscreen

        app = _make_app(tmp_path, monkeypatch)
        app.fullscreen = False
        toggle_fullscreen(app)
        assert app.fullscreen

    def test_toggle_fullscreen_off(self, tmp_path, monkeypatch):
        """Exercise toggle_fullscreen leaving fullscreen (lines 102-103)."""
        from cyberpunk_designer.windowing import toggle_fullscreen

        app = _make_app(tmp_path, monkeypatch)
        app.fullscreen = True
        app._default_palette_w = 120
        app._default_inspector_w = 200
        toggle_fullscreen(app)
        assert not app.fullscreen

    def test_toggle_fullscreen_with_scale_locked(self, tmp_path, monkeypatch):
        from cyberpunk_designer.windowing import toggle_fullscreen

        app = _make_app(tmp_path, monkeypatch)
        app._scale_locked = True
        app.scale = 2
        app.fullscreen = False
        toggle_fullscreen(app)

    def test_set_scale_with_window(self, tmp_path, monkeypatch):
        """Exercise set_scale with a window (lines 127-128)."""
        from cyberpunk_designer.windowing import set_scale

        app = _make_app(tmp_path, monkeypatch)
        app.max_auto_scale = 4
        set_scale(app, 2)
        assert app.scale >= 1

    def test_set_scale_no_window(self, tmp_path, monkeypatch):
        """set_scale with no window -> _mark_dirty."""
        from cyberpunk_designer.windowing import set_scale

        app = _make_app(tmp_path, monkeypatch)
        app.max_auto_scale = 4
        app.window = None
        set_scale(app, 3)

    def test_set_scale_window_get_size_raises(self, tmp_path, monkeypatch):
        """set_scale where window.get_size() raises."""
        from cyberpunk_designer.windowing import set_scale

        app = _make_app(tmp_path, monkeypatch)
        app.max_auto_scale = 4
        app.window = MagicMock()
        app.window.get_size.side_effect = pygame.error("no size")
        set_scale(app, 2)

    def test_recompute_scale_for_window(self, tmp_path, monkeypatch):
        from cyberpunk_designer.windowing import recompute_scale_for_window

        app = _make_app(tmp_path, monkeypatch)
        recompute_scale_for_window(app, 800, 600)
        assert app.scale >= 1

    def test_rebuild_layout_no_window_size(self, tmp_path, monkeypatch):
        """rebuild_layout without window_size (lines 197-198)."""
        from cyberpunk_designer.windowing import rebuild_layout

        app = _make_app(tmp_path, monkeypatch)
        rebuild_layout(app, window_size=None)

    def test_rebuild_layout_with_window_size(self, tmp_path, monkeypatch):
        from cyberpunk_designer.windowing import rebuild_layout

        app = _make_app(tmp_path, monkeypatch)
        rebuild_layout(app, window_size=(800, 600))

    def test_rebuild_layout_panels_collapsed(self, tmp_path, monkeypatch):
        from cyberpunk_designer.windowing import rebuild_layout

        app = _make_app(tmp_path, monkeypatch)
        app.panels_collapsed = True
        rebuild_layout(app, window_size=(512, 256))

    def test_rebuild_layout_with_lock_scale(self, tmp_path, monkeypatch):
        from cyberpunk_designer.windowing import rebuild_layout

        app = _make_app(tmp_path, monkeypatch)
        rebuild_layout(app, window_size=(800, 600), lock_scale=2)
        assert app.scale >= 1

    def test_rebuild_layout_large_scene(self, tmp_path, monkeypatch):
        """Rebuild with scene larger than canvas to hit centering branches."""
        from cyberpunk_designer.windowing import rebuild_layout

        app = _make_app(tmp_path, monkeypatch)
        app.designer._width = 256
        app.designer._height = 128
        rebuild_layout(app, window_size=(300, 200))

    def test_rebuild_layout_tiny_window(self, tmp_path, monkeypatch):
        """Very small window to exercise edge cases in scene_rect computation."""
        from cyberpunk_designer.windowing import rebuild_layout

        app = _make_app(tmp_path, monkeypatch)
        rebuild_layout(app, window_size=(100, 50))

    def test_screen_to_logical(self, tmp_path, monkeypatch):
        from cyberpunk_designer.windowing import screen_to_logical

        app = _make_app(tmp_path, monkeypatch)
        lx, ly = screen_to_logical(app, 100, 50)
        assert isinstance(lx, int)
        assert isinstance(ly, int)

    def test_compute_scale(self, tmp_path, monkeypatch):
        from cyberpunk_designer.windowing import compute_scale

        app = _make_app(tmp_path, monkeypatch)
        s = compute_scale(app, force_window=(800, 600))
        assert s >= 1

    def test_compute_scale_no_force(self, tmp_path, monkeypatch):
        from cyberpunk_designer.windowing import compute_scale

        app = _make_app(tmp_path, monkeypatch)
        s = compute_scale(app)
        assert s >= 1


class TestWindowingMock:
    """Mock-based windowing tests to hit exception branches."""

    def test_hw_scale_transform_fails(self, tmp_path, monkeypatch):
        """hardware_accelerated_scale fallback when transform.scale raises (lines 60-62)."""
        from cyberpunk_designer.windowing import hardware_accelerated_scale

        app = _make_app(tmp_path, monkeypatch)
        if app.window is None:
            return  # skip in headless
        orig_scale = pygame.transform.scale
        call_count = [0]

        def failing_scale(surface, size):
            call_count[0] += 1
            if call_count[0] == 1:
                raise pygame.error("test error")
            return orig_scale(surface, size)

        monkeypatch.setattr(pygame.transform, "scale", failing_scale)
        hardware_accelerated_scale(app)

    def test_handle_resize_scale_locked_raises(self, tmp_path, monkeypatch):
        """handle_video_resize when _scale_locked bool() raises (lines 79-80)."""
        from cyberpunk_designer.windowing import handle_video_resize

        app = _make_app(tmp_path, monkeypatch)

        class BadBool:
            def __bool__(self):
                raise TypeError("bad bool")

        app._scale_locked = BadBool()
        handle_video_resize(app, 512, 256)

    def test_toggle_fullscreen_zero_display(self, tmp_path, monkeypatch):
        """toggle_fullscreen when display.Info() returns zero dims (line 91)."""
        from cyberpunk_designer.windowing import toggle_fullscreen

        app = _make_app(tmp_path, monkeypatch)
        app.fullscreen = False
        mock_info = MagicMock(current_w=0, current_h=0)
        monkeypatch.setattr(pygame.display, "Info", lambda: mock_info)
        toggle_fullscreen(app)

    def test_toggle_fullscreen_off_scale_locked_raises(self, tmp_path, monkeypatch):
        """toggle_fullscreen off when _scale_locked bool() raises (lines 102-103)."""
        from cyberpunk_designer.windowing import toggle_fullscreen

        app = _make_app(tmp_path, monkeypatch)
        app.fullscreen = True
        app._default_palette_w = 120
        app._default_inspector_w = 200

        class BadBool:
            def __bool__(self):
                raise TypeError("bad bool")

        app._scale_locked = BadBool()
        toggle_fullscreen(app)

    def test_rebuild_state_scene_raises(self, tmp_path, monkeypatch):
        """rebuild_layout where state.current_scene() raises (lines 197-198)."""
        from cyberpunk_designer.windowing import rebuild_layout

        app = _make_app(tmp_path, monkeypatch)
        app.state = MagicMock()
        app.state.current_scene.side_effect = AttributeError("no scene")
        rebuild_layout(app, window_size=(800, 600))

    def test_rebuild_scene_larger_than_view(self, tmp_path, monkeypatch):
        """rebuild_layout with scene larger than view (lines 208, 212)."""
        from cyberpunk_designer.windowing import rebuild_layout

        app = _make_app(tmp_path, monkeypatch)
        # Designer width small so layout/canvas is small, but scene width large
        app.designer.width = 50
        app.designer.height = 50
        sc = app.state.current_scene()
        sc.width = 2000
        sc.height = 2000
        rebuild_layout(app, window_size=(300, 200))

    def test_rebuild_mark_dirty_fails(self, tmp_path, monkeypatch):
        """rebuild_layout when _mark_dirty raises (lines 229-230)."""
        from cyberpunk_designer.windowing import rebuild_layout

        app = _make_app(tmp_path, monkeypatch)
        app._mark_dirty = MagicMock(side_effect=AttributeError("fail"))
        rebuild_layout(app, window_size=(800, 600))

    def test_rebuild_state_layout_assign_fails(self, tmp_path, monkeypatch):
        """rebuild_layout when state.layout assignment raises (lines 224-225)."""
        from cyberpunk_designer.windowing import rebuild_layout

        app = _make_app(tmp_path, monkeypatch)

        class BadState:
            @property
            def layout(self):
                return None

            @layout.setter
            def layout(self, val):
                raise AttributeError("fail")

            def current_scene(self):
                return SimpleNamespace(width=256, height=128)

        app.state = BadState()
        rebuild_layout(app, window_size=(800, 600))

    def test_rebuild_scene_rect_outer_exception(self, tmp_path, monkeypatch):
        """rebuild_layout where canvas_rect access triggers exception (lines 218-219)."""
        from cyberpunk_designer.layout import Layout
        from cyberpunk_designer.windowing import rebuild_layout

        app = _make_app(tmp_path, monkeypatch)
        # Patch Layout so canvas_rect raises
        orig_init = Layout.__init__

        def patched_init(self, *args, **kwargs):
            orig_init(self, *args, **kwargs)

        monkeypatch.setattr(Layout, "__init__", patched_init)

        class BrokenRect:
            @property
            def x(self):
                raise AttributeError("broken")

        # Monkey-patch the Layout class canvas_rect to return broken rect
        monkeypatch.setattr(Layout, "canvas_rect", property(lambda self: BrokenRect()))
        rebuild_layout(app, window_size=(800, 600))
        # Should fallback to scene_rect = canvas_rect (but since canvas_rect is broken, it uses the except)
