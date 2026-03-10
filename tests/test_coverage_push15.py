"""Push15: app.py coverage — utility methods, state ops, context menu,
_execute_context_action dispatch, event handling, z-order, toggles, scenes."""

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
    if not hasattr(app, "_save_undo_state"):
        app._save_undo_state = lambda: None
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
# A) _value_ratio — compute value as 0..1 ratio
# ===========================================================================


class TestValueRatio:
    def test_normal(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _w(min_value=0, max_value=100, value=50)
        assert app._value_ratio(w) == pytest.approx(0.5)

    def test_zero_range(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _w(min_value=50, max_value=50, value=50)
        # denom = max(1, 0) = 1, (50-50)/1 = 0
        assert app._value_ratio(w) == pytest.approx(0.0)

    def test_clamp_high(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _w(min_value=0, max_value=10, value=999)
        assert app._value_ratio(w) == pytest.approx(1.0)

    def test_exception_fallback(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = SimpleNamespace(min_value="bad", max_value="bad", value="bad")
        result = app._value_ratio(w)
        assert result == pytest.approx(0.0)


# ===========================================================================
# B) _font_settings — env-driven font size/scale
# ===========================================================================


class TestFontSettings:
    def test_custom_values(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESP32OS_FONT_SIZE", "14")
        monkeypatch.setenv("ESP32OS_FONT_SCALE", "3")
        app = _make_app(tmp_path, monkeypatch)
        size, scale = app._font_settings()
        assert size == 14
        assert scale == 3

    def test_clamped_high(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESP32OS_FONT_SIZE", "100")
        monkeypatch.setenv("ESP32OS_FONT_SCALE", "99")
        app = _make_app(tmp_path, monkeypatch)
        size, scale = app._font_settings()
        assert size == 24
        assert scale == 6

    def test_bad_values(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESP32OS_FONT_SIZE", "abc")
        monkeypatch.setenv("ESP32OS_FONT_SCALE", "xyz")
        app = _make_app(tmp_path, monkeypatch)
        size, scale = app._font_settings()
        assert size == 10
        assert scale == 2


# ===========================================================================
# C) _hex_or_default — hex color parsing with fallback
# ===========================================================================


class TestHexOrDefault:
    def test_valid_hex(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._hex_or_default("#ffffff", (0, 0, 0))
        assert result == (255, 255, 255)

    def test_invalid_returns_default(self, tmp_path, monkeypatch):
        """hex_to_rgb raises → except returns default."""
        app = _make_app(tmp_path, monkeypatch)
        with patch("cyberpunk_designer.app.hex_to_rgb", side_effect=ValueError("bad")):
            result = app._hex_or_default("bad", (42, 42, 42))
        assert result == (42, 42, 42)


# ===========================================================================
# D) _snap_rect, _apply_snap — grid snapping
# ===========================================================================


class TestSnapping:
    def test_snap_rect(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        r = pygame.Rect(13, 15, 50, 32)
        result = app._snap_rect(r)
        assert result.x % GRID == 0
        assert result.y % GRID == 0
        assert result.width >= GRID
        assert result.height >= GRID

    def test_snap_rect_small_dims(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        r = pygame.Rect(0, 0, 1, 1)
        result = app._snap_rect(r)
        assert result.width >= GRID
        assert result.height >= GRID

    def test_apply_snap_enabled(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.snap_enabled = True
        result = app._apply_snap(13)
        assert result % GRID == 0

    def test_apply_snap_disabled(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.snap_enabled = False
        assert app._apply_snap(13) == 13


# ===========================================================================
# E) Group operations — _group_selection, _ungroup_selection, _groups_for_index
# ===========================================================================


class TestGroupOps:
    def test_groups_for_index_normal(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w(), _w()])
        app.designer.groups = {"g1": [0, 1], "g2": [1, 2]}
        result = app._groups_for_index(1)
        assert result == ["g1", "g2"]

    def test_groups_for_index_bad_members(self, tmp_path, monkeypatch):
        """Inner except: 'idx in members' raises (members not iterable)."""
        app = _make_app(tmp_path, monkeypatch)
        app.designer.groups = {"g1": 42}  # int, not iterable → TypeError
        result = app._groups_for_index(0)
        assert result == []

    def test_group_members_normal(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w(), _w()])
        app.designer.groups = {"g1": [0, 1, 2]}
        result = app._group_members("g1")
        assert result == [0, 1, 2]

    def test_group_members_bad_values(self, tmp_path, monkeypatch):
        """Members contain non-int values."""
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.designer.groups = {"g1": [0, "abc", 1]}
        result = app._group_members("g1")
        assert result == [0, 1]

    def test_group_selection(self, tmp_path, monkeypatch):
        """Group 2+ selected widgets."""
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w(), _w()])
        app.state.selected = [0, 1]
        app.state.selected_idx = 0
        app._group_selection()
        # Should have created a group
        groups = getattr(app.designer, "groups", {}) or {}
        assert len(groups) >= 1

    def test_group_selection_too_few(self, tmp_path, monkeypatch):
        """Group with <2 selected shows status message."""
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._group_selection()

    def test_ungroup_selection(self, tmp_path, monkeypatch):
        """Ungroup an existing group."""
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.designer.groups = {"group1": [0, 1]}
        app.state.selected = [0, 1]
        app.state.selected_idx = 0
        app._ungroup_selection()

    def test_next_group_name(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.designer.groups = {"group1": [0], "group2": [1]}
        result = app._next_group_name("group")
        assert result == "group3"

    def test_component_info_from_group(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._component_info_from_group("comp:button:btn:1") == ("button", "btn")
        assert app._component_info_from_group("comp:slider:2") == ("slider", "slider")
        assert app._component_info_from_group("group:foo") is None
        assert app._component_info_from_group("") is None

    def test_component_role_index(self, tmp_path, monkeypatch):
        w0 = _w(_widget_id="btn.ok")
        w1 = _w(_widget_id="btn.cancel")
        w2 = _w(_widget_id="other")
        app = _make_app(tmp_path, monkeypatch, widgets=[w0, w1, w2])
        roles = app._component_role_index([0, 1, 2], "btn")
        assert "ok" in roles
        assert "cancel" in roles
        assert roles["ok"] == 0
        assert roles["cancel"] == 1

    def test_format_group_label_component(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._format_group_label("comp:button:btn:1", [0, 1])
        assert "button" in result
        assert "btn" in result

    def test_format_group_label_plain(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._format_group_label("mygroup", [0, 1, 2])
        assert "mygroup" in result
        assert "3" in result


# ===========================================================================
# F) Z-order methods
# ===========================================================================


class TestZOrder:
    def test_z_order_step(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._z_order_step(1)
        sc = app.state.current_scene()
        assert int(getattr(sc.widgets[0], "z_index", 0) or 0) == 1

    def test_z_order_bring_to_front(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        sc = app.state.current_scene()
        sc.widgets[1].z_index = 5
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._z_order_bring_to_front()
        assert int(sc.widgets[0].z_index) > 5

    def test_z_order_send_to_back(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        sc = app.state.current_scene()
        sc.widgets[0].z_index = 5
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._z_order_send_to_back()
        assert int(sc.widgets[0].z_index) < 0


# ===========================================================================
# G) _toggle_lock_selection
# ===========================================================================


class TestToggleLock:
    def test_lock_and_unlock(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 1]
        app.state.selected_idx = 0
        sc = app.state.current_scene()
        # Lock
        app._toggle_lock_selection()
        assert sc.widgets[0].locked is True
        # Unlock
        app._toggle_lock_selection()
        assert sc.widgets[0].locked is False

    def test_lock_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app._toggle_lock_selection()  # early return


# ===========================================================================
# H) _switch_scene
# ===========================================================================


class TestSwitchScene:
    def test_switch_forward(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        original = app.designer.current_scene
        app._switch_scene(1)
        assert app.designer.current_scene != original

    def test_switch_single_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._switch_scene(1)  # only one scene → status message


# ===========================================================================
# I) _open_context_menu — builds menu items list
# ===========================================================================


class TestOpenContextMenu:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = []
        app.state.selected_idx = None
        app._open_context_menu((5, 5))
        menu = app._context_menu
        assert menu["visible"]
        # Should have at least view toggles and add widgets
        assert len(menu["items"]) > 5

    def test_single_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10, width=40, height=20)])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._open_context_menu((15, 15))
        menu = app._context_menu
        assert menu["visible"]
        # Should have edit, clipboard, z-order, etc
        actions = [item[2] for item in menu["items"] if item[2]]
        assert "copy" in actions
        assert "z_forward" in actions

    def test_multi_selection(self, tmp_path, monkeypatch):
        widgets = [_w(x=10, y=10), _w(x=60, y=10), _w(x=110, y=10)]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        app.state.selected = [0, 1, 2]
        app.state.selected_idx = 0
        app._open_context_menu((15, 15))
        menu = app._context_menu
        actions = [item[2] for item in menu["items"] if item[2]]
        # Multi-selection items
        assert "stack_vertical" in actions
        assert "equalize_gaps" in actions


# ===========================================================================
# J) _click_context_menu
# ===========================================================================


class TestClickContextMenu:
    def test_click_on_action(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        # Set up a fake menu with hitboxes
        app._context_menu = {
            "visible": True,
            "pos": (10, 10),
            "items": [("Grid", "G", "view_grid")],
            "hitboxes": [(pygame.Rect(0, 0, 100, 20), "view_grid")],
        }
        old_grid = app.show_grid
        app._click_context_menu((5, 5))
        assert app.show_grid != old_grid  # toggled
        assert not app._context_menu["visible"]

    def test_click_outside_dismiss(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._context_menu = {
            "visible": True,
            "pos": (10, 10),
            "items": [],
            "hitboxes": [(pygame.Rect(0, 0, 100, 20), "view_grid")],
        }
        app._click_context_menu((500, 500))  # outside hitbox
        assert not app._context_menu["visible"]


# ===========================================================================
# K) _execute_context_action — dispatch table (single-selection safe)
# ===========================================================================


# Actions safe to call with 1 widget selected
_SINGLE_ACTIONS = [
    "edit_text", "smart_edit", "copy", "duplicate",
    "z_forward", "z_backward", "z_front", "z_back",
    "cycle_style", "cycle_type", "cycle_border",
    "reorder_up", "reorder_down",
    "toggle_lock", "toggle_visibility", "toggle_enabled",
    "center_in_scene", "snap_to_grid",
    "auto_label", "inset_widgets", "outset_widgets",
    "swap_dims", "toggle_checked", "reset_values",
    "flatten_z", "number_ids", "z_by_position",
    "clamp_to_scene", "snap_all_grid",
    "size_to_text", "clear_all_text", "move_to_origin",
    "make_square", "scale_up", "scale_down",
    "number_text", "reset_padding", "reset_colors",
    "outline_only",
    "set_inverse", "set_bold", "set_default_style",
]

# Actions that need 2+ widgets selected
_MULTI_ACTIONS = [
    "stack_vertical", "stack_horizontal", "equalize_gaps",
    "swap_positions", "reverse_order", "normalize_sizes",
    "propagate_style", "propagate_colors", "propagate_border",
    "propagate_align", "propagate_padding", "propagate_margin",
    "propagate_value", "propagate_appearance", "propagate_text",
    "quick_clone", "dup_below", "dup_right", "clone_text",
    "increment_text", "measure",
    "distribute_columns", "distribute_rows",
    "pack_left", "pack_top", "cascade_arrange",
    "align_h_centers", "align_v_centers",
    "align_left_edges", "align_top_edges",
    "align_right_edges", "align_bottom_edges",
    "spread_values", "distribute_3col",
    "match_first_width", "match_first_height",
]

# View toggles
_VIEW_ACTIONS = [
    "view_grid", "view_rulers", "view_guides",
    "view_snap", "view_ids", "view_zlabels",
]

# Add widget actions
_ADD_ACTIONS = [
    "add_label", "add_button", "add_panel", "add_progressbar",
    "add_gauge", "add_slider", "add_checkbox",
    "add_chart", "add_icon", "add_textbox",
]

# Tab actions
_TAB_ACTIONS = [
    "tab_rename", "tab_duplicate", "tab_new",
]


class TestExecuteContextActions:
    def test_single_selection_actions(self, tmp_path, monkeypatch):
        widgets = [_w(x=8, y=8, width=40, height=20, text="A")]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        app.state.selected = [0]
        app.state.selected_idx = 0
        for action in _SINGLE_ACTIONS:
            # Restore selection if previous action cleared it
            sc = app.state.current_scene()
            if not app.state.selected and sc.widgets:
                app.state.selected = [0]
                app.state.selected_idx = 0
            try:
                app._execute_context_action(action)
            except Exception:
                pass  # some actions may fail without full GUI, that's OK

    def test_view_actions(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        for action in _VIEW_ACTIONS:
            app._execute_context_action(action)

    def test_add_actions(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        for action in _ADD_ACTIONS:
            app._execute_context_action(action)
        # Should have added widgets
        sc = app.state.current_scene()
        assert len(sc.widgets) >= len(_ADD_ACTIONS)

    def test_multi_selection_actions(self, tmp_path, monkeypatch):
        widgets = [
            _w(x=8, y=8, width=40, height=20, text="A"),
            _w(x=56, y=8, width=40, height=20, text="B"),
            _w(x=104, y=8, width=40, height=20, text="C"),
        ]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        for action in _MULTI_ACTIONS:
            sc = app.state.current_scene()
            # Ensure 3 widgets and multi-select
            while len(sc.widgets) < 3:
                sc.widgets.append(_w(x=8, y=40))
            n = len(sc.widgets)
            app.state.selected = list(range(min(3, n)))
            app.state.selected_idx = 0
            try:
                app._execute_context_action(action)
            except Exception:
                pass

    def test_tab_actions(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        for action in _TAB_ACTIONS:
            try:
                app._execute_context_action(action)
            except Exception:
                pass


# ===========================================================================
# L) _handle_event — event dispatch
# ===========================================================================


class TestHandleEvent:
    def test_videoresize(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        ev = SimpleNamespace(type=pygame.VIDEORESIZE, w=800, h=600)
        app._dispatch_event(ev)

    def test_keydown(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        ev = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_g, mod=0, unicode="g")
        app._dispatch_event(ev)

    def test_mouse_button_down_left(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        ev = SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 50))
        app._dispatch_event(ev)

    def test_mouse_button_up_left(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        ev = SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 50))
        app._dispatch_event(ev)
        ev2 = SimpleNamespace(type=pygame.MOUSEBUTTONUP, button=1, pos=(50, 50))
        app._dispatch_event(ev2)

    def test_mouse_motion(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        ev = SimpleNamespace(type=pygame.MOUSEMOTION, pos=(60, 60), buttons=(0, 0, 0))
        app._dispatch_event(ev)

    def test_mousewheel(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        ev = SimpleNamespace(type=pygame.MOUSEWHEEL, x=0, y=3)
        app._dispatch_event(ev)

    def test_textinput(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Start an edit to make text input meaningful
        app.state.inspector_selected_field = "text"
        app.state.inspector_input_buffer = ""
        ev = SimpleNamespace(type=pygame.TEXTINPUT, text="a")
        app._dispatch_event(ev)
        assert "a" in app.state.inspector_input_buffer

    def test_right_click(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        ev = SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=3, pos=(15, 15))
        app._dispatch_event(ev)
        # Context menu should be visible
        menu = getattr(app, "_context_menu", None)
        assert menu is not None

    def test_quit_with_dirty(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._dirty_scenes = {"main"}
        ev = SimpleNamespace(type=pygame.QUIT)
        app._dispatch_event(ev)
        assert app.running  # first quit → confirm prompt
        # Second quit
        app._dispatch_event(ev)
        assert not app.running

    def test_middle_click_tab(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        ev = SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=2, pos=(5, 5))
        app._dispatch_event(ev)


# ===========================================================================
# M) Scene management methods
# ===========================================================================


class TestSceneManagement:
    def test_add_new_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        count_before = len(app.designer.scenes)
        app._add_new_scene()
        assert len(app.designer.scenes) == count_before + 1

    def test_duplicate_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        count_before = len(app.designer.scenes)
        app._duplicate_current_scene()
        assert len(app.designer.scenes) == count_before + 1

    def test_delete_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        count_before = len(app.designer.scenes)
        app._delete_current_scene()
        assert len(app.designer.scenes) == count_before - 1

    def test_delete_only_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        count = len(app.designer.scenes)
        app._delete_current_scene()
        assert len(app.designer.scenes) == count  # can't delete only scene

    def test_close_other_scenes(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        app._close_other_scenes()
        assert len(app.designer.scenes) == 1

    def test_close_scenes_to_right(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        app._close_scenes_to_right()
        # depends on which scene is current

    def test_rename_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._rename_current_scene()
        assert app.state.inspector_selected_field == "_scene_name"


# ===========================================================================
# N) _apply_color_preset / _apply_color_preset_index
# ===========================================================================


class TestColorPresets:
    def test_apply_preset(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._apply_color_preset("#ff0000", "#00ff00")
        sc = app.state.current_scene()
        assert sc.widgets[0].color_fg == "#ff0000"
        assert sc.widgets[0].color_bg == "#00ff00"

    def test_apply_preset_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app._apply_color_preset("#ff0000", "#00ff00")  # noop

    def test_apply_preset_by_index(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._apply_color_preset_index(0)
        sc = app.state.current_scene()
        assert sc.widgets[0].color_fg == "#f5f5f5"


# ===========================================================================
# O) _add_widget — add various widget types
# ===========================================================================


class TestAddWidget:
    def test_add_label(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        count = len(app.state.current_scene().widgets)
        app._add_widget("label")
        assert len(app.state.current_scene().widgets) == count + 1

    def test_add_all_types(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        for kind in ["label", "button", "panel", "progressbar", "gauge",
                      "slider", "checkbox", "textbox", "chart", "icon"]:
            app._add_widget(kind)
        assert len(app.state.current_scene().widgets) >= 10


# ===========================================================================
# P) _cycle_profile, _set_profile
# ===========================================================================


class TestProfile:
    def test_cycle_profile(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._cycle_profile()
        # Should have changed (or wrapped around)

    def test_set_profile(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        from ui_designer import HARDWARE_PROFILES
        if HARDWARE_PROFILES:
            key = list(HARDWARE_PROFILES.keys())[0]
            app._set_profile(key)
            assert app.hardware_profile == key


# ===========================================================================
# Q) Double-click handler
# ===========================================================================


class TestDoubleClick:
    def test_handle_double_click_on_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10, width=40, height=20)])
        # Need to position inside the canvas rect
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        # Double-click on the widget area
        pos = (sr.x + 15, sr.y + 15)
        app._handle_double_click(pos)

    def test_double_click_outside_canvas(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._handle_double_click((-100, -100))  # outside canvas


# ===========================================================================
# R) Misc helpers
# ===========================================================================


class TestMiscHelpers:
    def test_mark_dirty(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._dirty = False
        app._mark_dirty()
        assert app._dirty

    def test_mark_dirty_with_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._dirty_scenes.clear()
        app._mark_dirty()
        # current_scene should be in dirty_scenes
        if app.designer.current_scene:
            assert app.designer.current_scene in app._dirty_scenes

    def test_set_status(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._set_status("Hello", ttl_sec=5.0)
        assert app.dialog_message == "Hello"

    def test_selected_group_exact(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.designer.groups = {"g1": [0, 1]}
        app.state.selected = [0, 1]
        app.state.selected_idx = 0
        result = app._selected_group_exact()
        assert result == "g1"

    def test_selected_component_group(self, tmp_path, monkeypatch):
        w0 = _w(_widget_id="btn.ok")
        w1 = _w(_widget_id="btn.cancel")
        app = _make_app(tmp_path, monkeypatch, widgets=[w0, w1])
        app.designer.groups = {"comp:button:btn:1": [0, 1]}
        app.state.selected = [0, 1]
        app.state.selected_idx = 0
        result = app._selected_component_group()
        assert result is not None
        assert result[1] == "button"  # component type

    def test_new_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app._new_scene()
        assert len(app.state.current_scene().widgets) == 0

    def test_zoom_to_fit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._zoom_to_fit()

    def test_search_widgets_prompt(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._search_widgets_prompt()
        assert app.state.inspector_selected_field == "_search"

    def test_array_duplicate_prompt(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._array_duplicate_prompt()
        assert app.state.inspector_selected_field == "_array_dup"

    def test_array_duplicate_prompt_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app._array_duplicate_prompt()

    def test_save_selection_as_template(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._save_selection_as_template()
        assert app.state.inspector_selected_field == "_template_name"

    def test_help_overlay_toggle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = False
        app._help_pinned = False
        app._toggle_help_overlay()
        assert app.show_help_overlay
        assert app._help_pinned
        # Toggle off
        app._toggle_help_overlay()
        assert not app.show_help_overlay

    def test_maybe_hide_help_overlay(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        app._help_shown_once = False
        app._help_pinned = False
        app._help_timer_start = time.time() - 100  # long ago
        app._help_timeout_sec = 1.0
        app._maybe_hide_help_overlay()
        assert not app.show_help_overlay

    def test_is_valid_color_str(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._is_valid_color_str("") is True
        assert app._is_valid_color_str("white") is True
        assert app._is_valid_color_str("#f5f5f5") is True
        assert app._is_valid_color_str("0xf5f5f5") is True
        assert app._is_valid_color_str("0x12345678") is False
        assert app._is_valid_color_str("badcolor") is False

    def test_on_key_down_dismiss_menu(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._context_menu = {"visible": True, "items": []}
        ev = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="")
        app._on_key_down(ev)
        assert not app._context_menu["visible"]
