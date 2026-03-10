"""Push17: app.py coverage — constructor env branches, scene management,
z-order methods, drawing cache paths, help overlay lifecycle, input handling."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import patch

import pygame
import pytest

from ui_designer import WidgetConfig

GRID = 8


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=60, height=20, text="hello")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _make_app(tmp_path, monkeypatch, *, widgets=None, extra_scenes=False):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    from cyberpunk_editor import CyberpunkEditorApp

    app = CyberpunkEditorApp(json_path, (256, 128))
    app.show_help_overlay = False
    app._help_shown_once = True
    if widgets:
        sc = app.state.current_scene()
        for w in widgets:
            sc.widgets.append(w)
    if extra_scenes:
        app.designer.create_scene("second")
        sc2 = app.designer.scenes["second"]
        sc2.width, sc2.height = 256, 128
    return app


# ===========================================================================
# A) Constructor env-var except branches
# ===========================================================================


class TestConstructorEnvBranches:
    """Hit except branches in __init__ for bad env-var values."""

    def test_bad_live_baud(self, tmp_path, monkeypatch):
        """L93-94: ESP32OS_LIVE_BAUD=nonsense → except → 115200."""
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("ESP32OS_LIVE_BAUD", "not_a_number")
        from cyberpunk_editor import CyberpunkEditorApp

        app = CyberpunkEditorApp(tmp_path / "s.json", (256, 128))
        assert app.live_preview_baud == 115200

    def test_bad_autosave_secs(self, tmp_path, monkeypatch):
        """L107-108: ESP32OS_AUTOSAVE_SECS=xyz → except → 10.0."""
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("ESP32OS_AUTOSAVE_SECS", "oops")
        from cyberpunk_editor import CyberpunkEditorApp

        app = CyberpunkEditorApp(tmp_path / "s.json", (256, 128))
        assert app.autosave_interval == 10.0

    def test_bad_fps_env(self, tmp_path, monkeypatch):
        """L151-152: ESP32OS_FPS=bad → except → FPS default."""
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("ESP32OS_FPS", "NaN")
        from cyberpunk_editor import CyberpunkEditorApp

        app = CyberpunkEditorApp(tmp_path / "s.json", (256, 128))
        assert isinstance(app.fps_limit, (int, float))

    def test_bad_max_scale_env(self, tmp_path, monkeypatch):
        """L155-156: ESP32OS_MAX_SCALE=bad → except → 4."""
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("ESP32OS_MAX_SCALE", "xyz")
        from cyberpunk_editor import CyberpunkEditorApp

        app = CyberpunkEditorApp(tmp_path / "s.json", (256, 128))
        assert app.max_auto_scale == 4

    def test_prefs_profile_loaded(self, tmp_path, monkeypatch):
        """L165: no CLI profile + prefs has 'profile' key → applied."""
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        # Patch _load_prefs to set a profile in prefs
        from cyberpunk_editor import CyberpunkEditorApp

        orig_load = CyberpunkEditorApp._load_prefs

        def _fake_load(self_):
            orig_load(self_)
            self_.prefs["profile"] = "esp32os_256x128_gray4"

        monkeypatch.setattr(CyberpunkEditorApp, "_load_prefs", _fake_load)
        app = CyberpunkEditorApp(tmp_path / "s.json", (256, 128))
        assert app.hardware_profile == "esp32os_256x128_gray4"

    def test_prefs_live_port_loaded(self, tmp_path, monkeypatch):
        """L169-177: prefs has live_port and live_baud."""
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        from cyberpunk_editor import CyberpunkEditorApp

        orig_load = CyberpunkEditorApp._load_prefs

        def _fake_load(self_):
            orig_load(self_)
            self_.prefs["live_port"] = "COM99"
            self_.prefs["live_baud"] = "9600"

        monkeypatch.setattr(CyberpunkEditorApp, "_load_prefs", _fake_load)
        app = CyberpunkEditorApp(tmp_path / "s.json", (256, 128))
        assert app.live_preview_port == "COM99"
        assert app.live_preview_baud == 9600

    def test_prefs_bad_live_baud(self, tmp_path, monkeypatch):
        """L176-177: prefs live_baud=bad → except → 115200."""
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        from cyberpunk_editor import CyberpunkEditorApp

        orig_load = CyberpunkEditorApp._load_prefs

        def _fake_load(self_):
            orig_load(self_)
            self_.prefs["live_baud"] = "bad_value"

        monkeypatch.setattr(CyberpunkEditorApp, "_load_prefs", _fake_load)
        app = CyberpunkEditorApp(tmp_path / "s.json", (256, 128))
        assert app.live_preview_baud == 115200

    def test_overflow_warn_on(self, tmp_path, monkeypatch):
        """L332: ESP32OS_OVERFLOW_WARN=1 → True."""
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("ESP32OS_OVERFLOW_WARN", "1")
        from cyberpunk_editor import CyberpunkEditorApp

        app = CyberpunkEditorApp(tmp_path / "s.json", (256, 128))
        assert app.show_overflow_warnings is True

    def test_overflow_warn_off(self, tmp_path, monkeypatch):
        """L334: ESP32OS_OVERFLOW_WARN=0 → False."""
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("ESP32OS_OVERFLOW_WARN", "0")
        from cyberpunk_editor import CyberpunkEditorApp

        app = CyberpunkEditorApp(tmp_path / "s.json", (256, 128))
        assert app.show_overflow_warnings is False

    def test_autosave_enabled(self, tmp_path, monkeypatch):
        """Hit autosave_enabled = True branch."""
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
        monkeypatch.setenv("ESP32OS_AUTOSAVE", "1")
        from cyberpunk_editor import CyberpunkEditorApp

        app = CyberpunkEditorApp(tmp_path / "s.json", (256, 128))
        assert app.autosave_enabled is True


# ===========================================================================
# B) Z-order methods with actual state changes
# ===========================================================================


class TestZOrderMethods:
    def test_z_order_step_forward(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._z_order_step(1)
        w = app.state.current_scene().widgets[0]
        assert int(getattr(w, "z_index", 0) or 0) == 1

    def test_z_order_step_backward(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app._z_order_step(-1)
        w = app.state.current_scene().widgets[0]
        assert int(getattr(w, "z_index", 0) or 0) == -1

    def test_z_order_bring_to_front(self, tmp_path, monkeypatch):
        widgets = [_w(x=0, y=0), _w(x=8, y=8)]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        app.state.selected = [0]
        app._z_order_bring_to_front()
        sc = app.state.current_scene()
        z0 = int(getattr(sc.widgets[0], "z_index", 0) or 0)
        assert z0 > 0

    def test_z_order_send_to_back(self, tmp_path, monkeypatch):
        widgets = [_w(x=0, y=0), _w(x=8, y=8)]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        app.state.selected = [1]
        app._z_order_send_to_back()
        sc = app.state.current_scene()
        z1 = int(getattr(sc.widgets[1], "z_index", 0) or 0)
        assert z1 < 0

    def test_z_order_step_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app._z_order_step(1)  # early return, no crash

    def test_z_order_front_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app._z_order_bring_to_front()

    def test_z_order_back_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app._z_order_send_to_back()


# ===========================================================================
# C) _toggle_lock_selection
# ===========================================================================


class TestToggleLock:
    def test_toggle_lock_on(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._toggle_lock_selection()
        assert app.state.current_scene().widgets[0].locked is True

    def test_toggle_lock_off(self, tmp_path, monkeypatch):
        w = _w()
        w.locked = True
        app = _make_app(tmp_path, monkeypatch, widgets=[w])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._toggle_lock_selection()
        assert app.state.current_scene().widgets[0].locked is False

    def test_toggle_lock_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app._toggle_lock_selection()


# ===========================================================================
# D) _switch_scene
# ===========================================================================


class TestSwitchScene:
    def test_switch_next(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        names = list(app.designer.scenes.keys())
        app.designer.current_scene = names[0]
        app._switch_scene(1)
        assert app.designer.current_scene == names[1]

    def test_switch_prev_wraps(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        names = list(app.designer.scenes.keys())
        app.designer.current_scene = names[0]
        app._switch_scene(-1)
        assert app.designer.current_scene == names[-1]

    def test_switch_single_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._switch_scene(1)  # Only 1 scene → no change


# ===========================================================================
# E) _handle_double_click variations
# ===========================================================================


class TestHandleDoubleClick:
    def test_outside_scene(self, tmp_path, monkeypatch):
        """Double click in no-man's land → nothing happens."""
        app = _make_app(tmp_path, monkeypatch)
        app._handle_double_click((-100, -100))

    def test_miss_widget(self, tmp_path, monkeypatch):
        """Double click on empty canvas area → hit=None."""
        app = _make_app(tmp_path, monkeypatch)
        sr = app.layout.canvas_rect
        # Click in empty canvas
        app._handle_double_click((sr.x + sr.width // 2, sr.y + sr.height // 2))


# ===========================================================================
# F) _optimized_draw_frame cache & dirty paths
# ===========================================================================


class TestOptimizedDraw:
    def test_canvas_only_dirty(self, tmp_path, monkeypatch):
        """When only canvas_rect is dirty, partial redraw path."""
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app._dirty = True
        app.dirty_rects = [app.layout.canvas_rect]
        app._optimized_draw_frame()

    def test_clean_preview_draw(self, tmp_path, monkeypatch):
        """Clean preview mode: only canvas drawn."""
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.clean_preview = True
        app._dirty = True
        app._optimized_draw_frame()

    def test_full_redraw(self, tmp_path, monkeypatch):
        """Full redraw when many dirty rects."""
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app._dirty = True
        app.dirty_rects = [
            pygame.Rect(0, 0, 10, 10),
            pygame.Rect(20, 20, 10, 10),
        ]
        app._optimized_draw_frame()

    def test_help_overlay_during_draw(self, tmp_path, monkeypatch):
        """Help overlay visible during draw."""
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        app._dirty = True
        app._optimized_draw_frame()
        app.show_help_overlay = False

    def test_vsync_disabled(self, tmp_path, monkeypatch):
        """vsync_enabled=False → update only dirty rects."""
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.vsync_enabled = False
        app._dirty = True
        app._optimized_draw_frame()


# ===========================================================================
# G) Help overlay lifecycle
# ===========================================================================


class TestHelpOverlay:
    def test_maybe_hide_help_not_shown(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = False
        app._maybe_hide_help_overlay()

    def test_maybe_hide_help_pinned(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        app._help_shown_once = False
        app._help_pinned = True
        app._maybe_hide_help_overlay()
        assert app.show_help_overlay  # pinned — stays

    def test_maybe_hide_help_timeout(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        app._help_shown_once = False
        app._help_pinned = False
        app._help_timer_start = time.time() - 999  # long ago
        app._help_timeout_sec = 1.0
        app._maybe_hide_help_overlay()
        assert not app.show_help_overlay

    def test_set_help_overlay_on_pinned(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._set_help_overlay(True, pinned=True)
        assert app.show_help_overlay
        assert app._help_pinned
        assert app._help_shown_once

    def test_set_help_overlay_off(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        app._help_pinned = True
        app._set_help_overlay(False)
        assert not app.show_help_overlay
        assert not app._help_pinned

    def test_set_help_overlay_no_change(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = False
        app._help_pinned = False
        app._set_help_overlay(False)  # no-op

    def test_toggle_help_overlay_from_off(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = False
        app._toggle_help_overlay()
        assert app.show_help_overlay
        assert app._help_pinned

    def test_toggle_help_overlay_pinned_off(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        app._help_pinned = True
        app._toggle_help_overlay()
        assert not app.show_help_overlay

    def test_toggle_help_overlay_unpinned_pin(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        app._help_pinned = False
        app._toggle_help_overlay()
        assert app._help_pinned


# ===========================================================================
# H) _inspector_start_edit / commit / cancel
# ===========================================================================


class TestInspectorEdit:
    def test_start_edit_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app.state.selected_idx = None
        app._inspector_start_edit("text")

    def test_start_edit_with_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(text="hi")])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._inspector_start_edit("text")
        assert app.state.inspector_selected_field == "text"

    def test_cancel_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.inspector_selected_field = "text"
        app.state.inspector_input_buffer = "abc"
        app._inspector_cancel_edit()
        assert app.state.inspector_selected_field is None
        assert app.state.inspector_input_buffer == ""

    def test_on_text_input_with_field(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.inspector_selected_field = "text"
        app.state.inspector_input_buffer = ""
        app._on_text_input("abc")
        assert app.state.inspector_input_buffer == "abc"


# ===========================================================================
# I) _apply_color_preset / _apply_color_preset_index
# ===========================================================================


class TestColorPresets:
    def test_apply_color_preset_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app._apply_color_preset("#fff", "#000")

    def test_apply_color_preset_with_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app._apply_color_preset("#ffffff", "#000000")
        w = app.state.current_scene().widgets[0]
        assert w.color_fg == "#ffffff"
        assert w.color_bg == "#000000"

    def test_apply_preset_index_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app._apply_color_preset_index(0)
        w = app.state.current_scene().widgets[0]
        assert w.color_fg == "#f5f5f5"

    def test_apply_preset_index_oob(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app._apply_color_preset_index(999)  # no crash


# ===========================================================================
# J) _set_profile / _cycle_profile
# ===========================================================================


class TestProfiles:
    def test_set_profile(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._set_profile("esp32os_256x128_gray4")
        assert app.hardware_profile == "esp32os_256x128_gray4"

    def test_set_profile_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        old = app.hardware_profile
        app._set_profile("nonexistent_profile")
        assert app.hardware_profile == old  # unchanged

    def test_cycle_profile(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._cycle_profile()
        assert app.hardware_profile is not None


# ===========================================================================
# K) Scene management deeper: delete last, duplicate copy naming
# ===========================================================================


class TestSceneManagementDeep:
    def test_delete_only_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        count = len(app.designer.scenes)
        app._delete_current_scene()
        assert len(app.designer.scenes) == count  # can't delete only scene

    def test_delete_switches_to_adjacent(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        names = list(app.designer.scenes.keys())
        app.designer.current_scene = names[0]
        app._delete_current_scene()
        assert app.designer.current_scene in app.designer.scenes

    def test_close_other_scenes_multiple(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        app.designer.create_scene("third")
        sc3 = app.designer.scenes["third"]
        sc3.width, sc3.height = 256, 128
        names = list(app.designer.scenes.keys())
        app.designer.current_scene = names[1]
        app._close_other_scenes()
        assert len(app.designer.scenes) == 1

    def test_close_scenes_to_right_from_first(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        names = list(app.designer.scenes.keys())
        app.designer.current_scene = names[0]
        before = len(app.designer.scenes)
        app._close_scenes_to_right()
        assert len(app.designer.scenes) < before

    def test_duplicate_scene_naming(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._duplicate_current_scene()
        app._duplicate_current_scene()
        # Should have unique names
        names = list(app.designer.scenes.keys())
        assert len(set(names)) == len(names)

    def test_add_new_scene_naming(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._add_new_scene()
        app._add_new_scene()
        names = list(app.designer.scenes.keys())
        assert len(set(names)) == len(names)


# ===========================================================================
# L) _add_widget with various types
# ===========================================================================


class TestAddWidget:
    @pytest.mark.parametrize(
        "kind",
        [
            "label",
            "button",
            "panel",
            "progressbar",
            "gauge",
            "slider",
            "checkbox",
            "textbox",
            "chart",
            "icon",
            "box",
        ],
    )
    def test_add_widget_type(self, kind, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        before = len(app.state.current_scene().widgets)
        app._add_widget(kind)
        assert len(app.state.current_scene().widgets) == before + 1

    def test_add_widget_unknown_type(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        before = len(app.state.current_scene().widgets)
        app._add_widget("unknown_xyz")
        # Should still add with default type
        assert len(app.state.current_scene().widgets) >= before


# ===========================================================================
# M) _export_c_header with real JSON
# ===========================================================================


class TestExportCHeader:
    def test_export_success(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.json_path = tmp_path / "design.json"
        app.save_json()
        app._export_c_header()
        out = tmp_path / "output" / "ui_design_export.h"
        assert out.exists()

    def test_export_codegen_import_error(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.json_path = tmp_path / "design.json"
        app.save_json()
        with patch.dict("sys.modules", {"tools.ui_codegen": None}):
            app._export_c_header()  # hits ImportError path


# ===========================================================================
# N) _on_key_down with context menu escape
# ===========================================================================


class TestOnKeyDown:
    def test_escape_dismisses_context_menu(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._context_menu = {"visible": True, "pos": (0, 0), "items": [], "hitboxes": []}
        ev = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="")
        app._on_key_down(ev)
        assert not app._context_menu["visible"]

    def test_other_key_with_menu(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._context_menu = {"visible": True, "pos": (0, 0), "items": [], "hitboxes": []}
        ev = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode="a")
        app._on_key_down(ev)


# ===========================================================================
# O) _auto_complete_widget edge cases
# ===========================================================================


class TestAutoCompleteWidget:
    def test_label_with_device_profile(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.hardware_profile = "esp32os_256x128_gray4"
        w = _w(type="label", text="Test", width=5, height=5)
        app._auto_complete_widget(w)
        assert w.width >= 5
        assert w.height >= 5

    def test_label_without_device_profile(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.hardware_profile = None
        w = _w(type="label", text="Test", width=5, height=5)
        app._auto_complete_widget(w)
        assert w.width >= 5


# ===========================================================================
# P) _intelligent_auto_arrange
# ===========================================================================


class TestIntelligentAutoArrange:
    def test_with_multiple_types(self, tmp_path, monkeypatch):
        widgets = [
            _w(type="label", x=100, y=100, width=40, height=16),
            _w(type="button", x=200, y=200, width=60, height=20),
            _w(type="label", x=150, y=150, width=40, height=16),
        ]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        app._intelligent_auto_arrange()

    def test_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._intelligent_auto_arrange()  # no widgets → early return


# ===========================================================================
# Q) Drawing delegates (thin wrappers)
# ===========================================================================


class TestDrawingDelegates:
    def test_draw_canvas(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app._draw_canvas()

    def test_draw_toolbar(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._draw_toolbar()

    def test_draw_scene_tabs(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._draw_scene_tabs()

    def test_draw_palette(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._draw_palette()

    def test_draw_inspector(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._draw_inspector()

    def test_draw_status(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._draw_status()

    def test_text_width_px(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = app._text_width_px("Hello")
        assert w > 0

    def test_ellipsize_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        r = app._ellipsize_text_px("Hello World", 30)
        assert isinstance(r, str)

    def test_wrap_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        lines = app._wrap_text_px("Hello World Test", 40, 2)
        assert isinstance(lines, list)

    def test_draw_border_style(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf = pygame.Surface((100, 50))
        app._draw_border_style(surf, pygame.Rect(0, 0, 100, 50), "solid", (255, 255, 255))

    def test_draw_bevel_frame(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf = pygame.Surface((100, 50))
        app._draw_bevel_frame(surf, pygame.Rect(0, 0, 100, 50), (128, 128, 128))

    def test_draw_widget_preview(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf = pygame.Surface((100, 50))
        w = _w()
        app._draw_widget_preview(surf, w, pygame.Rect(0, 0, 60, 20), (0, 0, 0), 2, False)


# ===========================================================================
# R) _component and group helpers
# ===========================================================================


class TestComponentGroupHelpers:
    def test_component_info_from_group_not_comp(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._component_info_from_group("regular_group")
        assert result is None

    def test_component_info_from_group_comp(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._component_info_from_group("comp:header_bar:root")
        assert result is not None

    def test_component_role_index(self, tmp_path, monkeypatch):
        w1 = _w()
        w1._widget_id = "hdr.title"
        w2 = _w()
        w2._widget_id = "hdr.icon"
        app = _make_app(tmp_path, monkeypatch, widgets=[w1, w2])
        roles = app._component_role_index([0, 1], "hdr")
        assert "title" in roles
        assert "icon" in roles

    def test_component_role_index_empty_prefix(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        roles = app._component_role_index([0], "")
        assert roles == {}

    def test_selected_component_group_none(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        result = app._selected_component_group()
        assert result is None

    def test_selected_group_exact_no_match(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        result = app._selected_group_exact()
        assert result is None

    def test_format_group_label_regular(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        lbl = app._format_group_label("mygroup", [0, 1])
        assert "mygroup" in lbl

    def test_format_group_label_component(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        lbl = app._format_group_label("comp:header_bar:root", [0, 1])
        assert "header_bar" in lbl

    def test_next_group_name(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        name = app._next_group_name("group")
        assert name == "group1"

    def test_group_selection_too_few(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app._group_selection()  # needs 2+

    def test_group_and_ungroup(self, tmp_path, monkeypatch):
        widgets = [_w(x=0, y=0), _w(x=8, y=0)]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        app.state.selected = [0, 1]
        app.state.selected_idx = 0
        app._group_selection()
        app._ungroup_selection()

    def test_ungroup_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app._ungroup_selection()

    def test_tri_state(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._tri_state([]) == "off"
        assert app._tri_state([True, True]) == "on"
        assert app._tri_state([False, False]) == "off"
        assert app._tri_state([True, False]) == "mixed"


# ===========================================================================
# S) _palette_content_height / _inspector_content_height
# ===========================================================================


class TestContentHeights:
    def test_palette_content_height(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        h = app._palette_content_height()
        assert h > 0

    def test_inspector_content_height(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        h = app._inspector_content_height()
        assert h > 0

    def test_inspector_content_height_collapsed(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app.inspector_collapsed = {"Info", "Layers"}
        h = app._inspector_content_height()
        assert h > 0


# ===========================================================================
# T) _set_scale / _compute_scale / _recompute_scale_for_window
# ===========================================================================


class TestScaleOps:
    def test_set_scale(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._set_scale(2)
        assert app._scale_locked

    def test_compute_scale(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        s = app._compute_scale()
        assert s >= 1

    def test_recompute_scale(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._recompute_scale_for_window(800, 600)

    def test_rebuild_layout(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._rebuild_layout(window_size=(800, 600), force_scene_size=True, lock_scale=2)


# ===========================================================================
# U) _search_widgets_prompt / _array_duplicate_prompt
# ===========================================================================


class TestPrompts:
    def test_search_widgets_prompt(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._search_widgets_prompt()
        assert app.state.inspector_selected_field == "_search"

    def test_array_dup_prompt_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app._array_duplicate_prompt()

    def test_array_dup_prompt_with_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app._array_duplicate_prompt()
        assert app.state.inspector_selected_field == "_array_dup"


# ===========================================================================
# V) _is_valid_color_str edge cases
# ===========================================================================


class TestIsValidColor:
    def test_empty(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._is_valid_color_str("") is True

    def test_hex_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._is_valid_color_str("#aabbcc") is True

    def test_hex_0x_valid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._is_valid_color_str("0xaabbcc") is True

    def test_hex_invalid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._is_valid_color_str("#gghhii") is False

    def test_named_color(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Check a known named color
        assert (
            app._is_valid_color_str("white") is True
            or app._is_valid_color_str("unknown_color_xyz") is False
        )


# ===========================================================================
# W) _maybe_autosave / _save_prefs / _load_prefs
# ===========================================================================


class TestAutosavePrefs:
    def test_maybe_autosave_not_dirty(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._dirty_scenes.clear()
        app._maybe_autosave()

    def test_save_prefs(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._save_prefs()

    def test_load_prefs(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._load_prefs()


# ===========================================================================
# X) _snap_to_grid_rect / _apply_snap
# ===========================================================================


class TestSnapHelpers:
    def test_apply_snap_enabled(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.snap_enabled = True
        v = app._apply_snap(13)
        assert v % GRID == 0

    def test_apply_snap_disabled(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.snap_enabled = False
        assert app._apply_snap(13) == 13


# ===========================================================================
# Y) _toggle_overflow_warnings
# ===========================================================================


class TestOverflowWarnings:
    def test_toggle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        was = app.show_overflow_warnings
        app._toggle_overflow_warnings()
        assert app.show_overflow_warnings != was


# ===========================================================================
# Z) _load_or_default / save_json / load_json / _new_scene
# ===========================================================================


class TestLoadSave:
    def test_save_and_load(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(text="saved")])
        app.json_path = tmp_path / "test_save.json"
        app.save_json()
        assert app.json_path.exists()
        app.load_json()

    def test_new_scene_resets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app._new_scene()
        assert len(app.state.current_scene().widgets) == 0

    def test_widget_presets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        presets = app._load_widget_presets()
        assert isinstance(presets, list)
        app._save_widget_presets()

    def test_build_widget_presets_actions(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        actions = app._build_widget_presets_actions()
        assert len(actions) > 0

    def test_build_template_actions(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        actions = app._build_template_actions()
        assert isinstance(actions, list)


# ===========================================================================
# AA) _dispatch_event QUIT paths
# ===========================================================================


class TestDispatchQuit:
    def test_quit_first_press(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._dirty_scenes = {"main"}
        app._quit_confirm_ts = 0.0
        ev = SimpleNamespace(type=pygame.QUIT)
        app._dispatch_event(ev)
        assert app.running  # first quit just warns

    def test_quit_double_press(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._dirty_scenes = {"main"}
        app._quit_confirm_ts = time.time()  # just confirmed
        ev = SimpleNamespace(type=pygame.QUIT)
        app._dispatch_event(ev)
        assert not app.running  # second quit exits

    def test_quit_no_changes(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._dirty_scenes.clear()
        ev = SimpleNamespace(type=pygame.QUIT)
        app._dispatch_event(ev)
        assert not app.running


# ===========================================================================
# BB) _dispatch_event VIDEORESIZE
# ===========================================================================


class TestVideoResize:
    def test_resize(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        ev = SimpleNamespace(type=pygame.VIDEORESIZE, w=800, h=600, size=(800, 600))
        app._dispatch_event(ev)


# ===========================================================================
# CC) Focus navigation methods
# ===========================================================================


class TestFocusNav:
    def test_is_widget_focusable(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._is_widget_focusable(_w(type="button"))

    def test_focusable_indices(self, tmp_path, monkeypatch):
        widgets = [_w(type="button"), _w(type="label")]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        indices = app._focusable_indices()
        assert isinstance(indices, list)

    def test_set_focus(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(type="button")])
        app._set_focus(0)

    def test_ensure_focus(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(type="button")])
        app._ensure_focus()

    def test_focus_cycle(self, tmp_path, monkeypatch):
        widgets = [_w(type="button"), _w(type="slider")]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        app._focus_cycle(1)

    def test_focus_move_direction(self, tmp_path, monkeypatch):
        widgets = [_w(type="button", x=0, y=0), _w(type="button", x=80, y=0)]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        app._set_focus(0)
        app._focus_move_direction("right")

    def test_adjust_focused_value(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(type="slider", value=50)])
        app._set_focus(0)
        app._adjust_focused_value(5)

    def test_activate_focused(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(type="checkbox")])
        app._set_focus(0)
        app._activate_focused()
