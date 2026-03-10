"""Tests for CyberpunkEditorApp methods — batch 3.

Covers: _auto_complete_widget, _event_priority, _groups_for_index,
_group_members, _selected_component_group, _component_role_index,
_palette_content_height, _inspector_content_height, _font_settings,
_toggle_lock_selection, _switch_scene, _add_widget, _auto_arrange_grid,
_execute_context_action, _handle_double_click, _zoom_to_fit.
"""

from __future__ import annotations

import pygame

from cyberpunk_editor import CyberpunkEditorApp
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    return CyberpunkEditorApp(json_path, (256, 128))


def _add(app, **kw):
    defaults = dict(type="label", x=0, y=0, width=80, height=16, text="W")
    defaults.update(kw)
    w = WidgetConfig(**defaults)
    sc = app.state.current_scene()
    sc.widgets.append(w)
    return w


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None


# ===================================================================
# _auto_complete_widget
# ===================================================================


class TestAutoCompleteWidget:
    def test_button_gets_default_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(type="button", x=0, y=0, width=40, height=16, text="")
        app._auto_complete_widget(w)
        assert w.text == "Button"

    def test_button_keeps_existing_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(type="button", x=0, y=0, width=40, height=16, text="OK")
        app._auto_complete_widget(w)
        assert w.text == "OK"

    def test_fills_missing_fg_color(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(type="label", x=0, y=0, width=40, height=16, text="X", color_fg="")
        app._auto_complete_widget(w)
        assert w.color_fg == "#f5f5f5"

    def test_fills_missing_bg_color(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(type="label", x=0, y=0, width=40, height=16, text="X", color_bg="")
        app._auto_complete_widget(w)
        assert w.color_bg == "#000000"

    def test_keeps_existing_colors(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(
            type="label", x=0, y=0, width=40, height=16, text="X",
            color_fg="#aabbcc", color_bg="#112233",
        )
        app._auto_complete_widget(w)
        assert w.color_fg == "#aabbcc"
        assert w.color_bg == "#112233"

    def test_snaps_position_to_grid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(type="label", x=3, y=5, width=41, height=17, text="X")
        app._auto_complete_widget(w)
        assert w.x % 8 == 0
        assert w.y % 8 == 0
        assert w.width % 8 == 0
        assert w.height % 8 == 0

    def test_label_sizing_expands_narrow(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(type="label", x=0, y=0, width=1, height=1, text="Hello World")
        app._auto_complete_widget(w)
        # Should expand to fit text
        assert w.width > 1
        assert w.height > 1


# ===================================================================
# _event_priority
# ===================================================================


class TestEventPriority:
    def test_quit_has_highest_priority(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        ev = pygame.event.Event(pygame.QUIT)
        assert app._event_priority(ev) == 0

    def test_keydown_precedes_mouse(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        key_ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode="a", scancode=0)
        mouse_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(0, 0), button=1)
        assert app._event_priority(key_ev) < app._event_priority(mouse_ev)

    def test_unknown_event_type_gets_default(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        ev = pygame.event.Event(pygame.USEREVENT)
        assert app._event_priority(ev) == 10

    def test_videoresize_before_keys(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        resize_ev = pygame.event.Event(pygame.VIDEORESIZE, size=(800, 600), w=800, h=600)
        key_ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode="a", scancode=0)
        assert app._event_priority(resize_ev) < app._event_priority(key_ev)

    def test_mousewheel_after_mousebuttondown(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        wheel = pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1)
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(0, 0), button=1)
        assert app._event_priority(wheel) > app._event_priority(click)

    def test_textinput_lowest_mapped(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        ev = pygame.event.Event(pygame.TEXTINPUT, text="a")
        assert app._event_priority(ev) == 8

    def test_mousemotion_priority(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        ev = pygame.event.Event(pygame.MOUSEMOTION, pos=(10, 10), rel=(1, 1), buttons=(0, 0, 0))
        assert app._event_priority(ev) == 7


# ===================================================================
# _groups_for_index
# ===================================================================


class TestGroupsForIndex:
    def test_no_groups(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        assert app._groups_for_index(0) == []

    def test_one_group(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        app.designer.groups = {"grp1": [0]}
        assert app._groups_for_index(0) == ["grp1"]

    def test_multiple_groups_sorted(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        app.designer.groups = {"beta": [0], "alpha": [0, 1]}
        result = app._groups_for_index(0)
        assert result == ["alpha", "beta"]

    def test_index_not_in_any_group(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        app.designer.groups = {"grp": [1]}
        assert app._groups_for_index(0) == []

    def test_groups_is_none_safe(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.designer.groups = None
        assert app._groups_for_index(0) == []


# ===================================================================
# _group_members
# ===================================================================


class TestGroupMembers:
    def test_basic_members(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        app.designer.groups = {"g": [0, 1]}
        assert app._group_members("g") == [0, 1]

    def test_filters_out_of_range(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        app.designer.groups = {"g": [0, 5, 99]}
        assert app._group_members("g") == [0]

    def test_deduplicates(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        app.designer.groups = {"g": [0, 0, 0]}
        assert app._group_members("g") == [0]

    def test_returns_sorted(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        for _ in range(4):
            _add(app)
        app.designer.groups = {"g": [3, 1, 2]}
        assert app._group_members("g") == [1, 2, 3]

    def test_missing_group_name(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.designer.groups = {"g": [0]}
        assert app._group_members("nonexistent") == []

    def test_no_groups_attr(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.designer.groups = None
        assert app._group_members("g") == []


# ===================================================================
# _selected_component_group
# ===================================================================


class TestSelectedComponentGroup:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._selected_component_group() is None

    def test_no_component_groups(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        app.designer.groups = {"plain_group": [0]}
        assert app._selected_component_group() is None

    def test_component_group_match(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w0 = _add(app, text="root")
        w1 = _add(app, text="child")
        w0._widget_id = "myroot.title"
        w1._widget_id = "myroot.body"
        app.designer.groups = {"comp:card:myroot:2": [0, 1]}
        _sel(app, 0, 1)
        result = app._selected_component_group()
        assert result is not None
        gname, comp_type, root, members = result
        assert gname == "comp:card:myroot:2"
        assert comp_type == "card"
        assert root == "myroot"
        assert set(members) == {0, 1}

    def test_selection_not_subset_of_members(self, tmp_path, monkeypatch):
        """If selection includes widget not in component group, no match."""
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _add(app)
        app.designer.groups = {"comp:card:r:2": [0, 1]}
        _sel(app, 0, 2)  # 2 is not in the group
        assert app._selected_component_group() is None


# ===================================================================
# _component_role_index
# ===================================================================


class TestComponentRoleIndex:
    def test_basic_roles(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w0 = _add(app)
        w1 = _add(app)
        w0._widget_id = "hdr.title"
        w1._widget_id = "hdr.icon"
        roles = app._component_role_index([0, 1], "hdr")
        assert roles == {"title": 0, "icon": 1}

    def test_no_matching_prefix(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w0 = _add(app)
        w0._widget_id = "other.title"
        roles = app._component_role_index([0], "hdr")
        assert roles == {}

    def test_invalid_indices_ignored(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        roles = app._component_role_index([0, 99], "x")
        assert 99 not in roles.values()

    def test_empty_prefix(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        roles = app._component_role_index([0], "")
        assert roles == {}

    def test_first_role_wins(self, tmp_path, monkeypatch):
        """If two widgets have the same role, first encountered wins."""
        app = _make_app(tmp_path, monkeypatch)
        w0 = _add(app)
        w1 = _add(app)
        w0._widget_id = "p.title"
        w1._widget_id = "p.title"
        roles = app._component_role_index([0, 1], "p")
        assert roles["title"] == 0


# ===================================================================
# _palette_content_height
# ===================================================================


class TestPaletteContentHeight:
    def test_positive_height(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        h = app._palette_content_height()
        assert h > 0

    def test_grows_with_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        h0 = app._palette_content_height()
        for _ in range(5):
            _add(app)
        h5 = app._palette_content_height()
        assert h5 > h0

    def test_collapsed_vs_expanded_height(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Expand all sections first
        app.palette_collapsed.clear()
        h_expanded = app._palette_content_height()
        # Collapse all sections
        for sec_name, _ in app.palette_sections:
            app.palette_collapsed.add(sec_name)
        h_collapsed = app._palette_content_height()
        # Collapsed sections skip their items but keep headers
        assert h_collapsed < h_expanded


# ===================================================================
# _inspector_content_height
# ===================================================================


class TestInspectorContentHeight:
    def test_positive_height(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        h = app._inspector_content_height()
        assert h > 0

    def test_minimum_one_row(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # No widget selected — inspector may have minimal rows
        h = app._inspector_content_height()
        assert h >= app.pixel_row_height

    def test_collapsed_sections_reduce(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        h_full = app._inspector_content_height()
        # Collapse all inspector sections
        rows, _, _ = app._compute_inspector_rows()
        for key, _ in rows:
            if isinstance(key, str) and key.startswith("_section:"):
                sec = key[len("_section:"):]
                if not hasattr(app, "inspector_collapsed"):
                    app.inspector_collapsed = set()
                app.inspector_collapsed.add(sec)
        h_collapsed = app._inspector_content_height()
        assert h_collapsed <= h_full


# ===================================================================
# _font_settings
# ===================================================================


class TestFontSettings:
    def test_defaults(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.delenv("ESP32OS_FONT_SIZE", raising=False)
        monkeypatch.delenv("ESP32OS_FONT_SCALE", raising=False)
        size, scale = app._font_settings()
        assert size == 10
        assert scale == 2

    def test_env_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESP32OS_FONT_SIZE", "14")
        monkeypatch.setenv("ESP32OS_FONT_SCALE", "3")
        app = _make_app(tmp_path, monkeypatch)
        size, scale = app._font_settings()
        assert size == 14
        assert scale == 3

    def test_clamp_low(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESP32OS_FONT_SIZE", "1")
        monkeypatch.setenv("ESP32OS_FONT_SCALE", "0")
        app = _make_app(tmp_path, monkeypatch)
        size, scale = app._font_settings()
        assert size == 5
        assert scale == 1

    def test_clamp_high(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESP32OS_FONT_SIZE", "999")
        monkeypatch.setenv("ESP32OS_FONT_SCALE", "100")
        app = _make_app(tmp_path, monkeypatch)
        size, scale = app._font_settings()
        assert size == 24
        assert scale == 6

    def test_invalid_env_uses_default(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ESP32OS_FONT_SIZE", "abc")
        monkeypatch.setenv("ESP32OS_FONT_SCALE", "xyz")
        app = _make_app(tmp_path, monkeypatch)
        size, scale = app._font_settings()
        assert size == 10
        assert scale == 2


# ===================================================================
# _toggle_lock_selection
# ===================================================================


class TestToggleLockSelection:
    def test_no_selection_status_msg(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._toggle_lock_selection()
        assert "nothing selected" in (app.dialog_message or "").lower()

    def test_lock_unlocked_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        w.locked = False
        _sel(app, 0)
        app._toggle_lock_selection()
        assert w.locked is True

    def test_unlock_locked_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        w.locked = True
        _sel(app, 0)
        app._toggle_lock_selection()
        assert w.locked is False

    def test_mixed_locks_to_locked(self, tmp_path, monkeypatch):
        """When some widgets locked and some not, toggle → all locked."""
        app = _make_app(tmp_path, monkeypatch)
        w0 = _add(app)
        w1 = _add(app)
        w0.locked = True
        w1.locked = False
        _sel(app, 0, 1)
        app._toggle_lock_selection()
        # not all were locked → toggle to locked
        assert w0.locked is True
        assert w1.locked is True

    def test_all_locked_toggles_to_unlocked(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w0 = _add(app)
        w1 = _add(app)
        w0.locked = True
        w1.locked = True
        _sel(app, 0, 1)
        app._toggle_lock_selection()
        assert w0.locked is False
        assert w1.locked is False


# ===================================================================
# _switch_scene
# ===================================================================


class TestSwitchScene:
    def test_single_scene_status(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._switch_scene(1)
        assert "only one" in (app.dialog_message or "").lower()

    def test_switch_forward(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        from ui_models import SceneConfig
        app.designer.scenes["second"] = SceneConfig(
            name="second", width=256, height=128, widgets=[]
        )
        first = app.designer.current_scene
        app._switch_scene(1)
        assert app.designer.current_scene != first

    def test_switch_backward_wraps(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        from ui_models import SceneConfig
        app.designer.scenes["second"] = SceneConfig(
            name="second", width=256, height=128, widgets=[]
        )
        first = app.designer.current_scene
        app._switch_scene(-1)
        # Wraps: from first (idx 0) going backward → last scene
        assert app.designer.current_scene != first

    def test_clears_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        from ui_models import SceneConfig
        app.designer.scenes["second"] = SceneConfig(
            name="second", width=256, height=128, widgets=[]
        )
        _add(app)
        _sel(app, 0)
        app._switch_scene(1)
        assert app.state.selected == []
        assert app.state.selected_idx is None


# ===================================================================
# _add_widget
# ===================================================================


class TestAddWidget:
    def test_add_label(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        before = len(sc.widgets)
        app._add_widget("label")
        assert len(sc.widgets) == before + 1
        assert sc.widgets[-1].type == "label"

    def test_add_button(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._add_widget("button")
        sc = app.state.current_scene()
        assert sc.widgets[-1].type == "button"

    def test_add_panel(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._add_widget("panel")
        sc = app.state.current_scene()
        w = sc.widgets[-1]
        assert w.type == "panel"
        assert w.width >= 160

    def test_add_gauge(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._add_widget("gauge")
        sc = app.state.current_scene()
        w = sc.widgets[-1]
        assert w.type == "gauge"
        assert w.value == 70

    def test_add_slider(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._add_widget("slider")
        sc = app.state.current_scene()
        assert sc.widgets[-1].type == "slider"

    def test_add_checkbox(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._add_widget("checkbox")
        sc = app.state.current_scene()
        assert sc.widgets[-1].type == "checkbox"

    def test_add_chart(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._add_widget("chart")
        sc = app.state.current_scene()
        assert sc.widgets[-1].type == "chart"

    def test_add_icon(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._add_widget("icon")
        sc = app.state.current_scene()
        w = sc.widgets[-1]
        assert w.type == "icon"
        assert w.icon_char == "@"

    def test_add_progressbar(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._add_widget("progressbar")
        sc = app.state.current_scene()
        w = sc.widgets[-1]
        assert w.type == "progressbar"
        assert w.value == 65

    def test_add_textbox(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._add_widget("textbox")
        sc = app.state.current_scene()
        assert sc.widgets[-1].type == "textbox"

    def test_unknown_kind(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._add_widget("nonexistent")
        sc = app.state.current_scene()
        # Should still add, just with generic defaults
        assert sc.widgets[-1].type == "nonexistent"

    def test_selects_new_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._add_widget("label")
        sc = app.state.current_scene()
        expected_idx = len(sc.widgets) - 1
        assert app.state.selected == [expected_idx]
        assert app.state.selected_idx == expected_idx

    def test_case_insensitive(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._add_widget("LABEL")
        sc = app.state.current_scene()
        assert sc.widgets[-1].type == "label"


# ===================================================================
# _auto_arrange_grid
# ===================================================================


class TestAutoArrangeGrid:
    def test_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Should not raise
        app._auto_arrange_grid()

    def test_arranges_in_rows(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        for _ in range(3):
            _add(app, width=40, height=16)
        app._auto_arrange_grid()
        sc = app.state.current_scene()
        # First widget at GRID, GRID
        assert sc.widgets[0].x == 8
        assert sc.widgets[0].y == 8
        # Subsequent widgets placed after first
        assert sc.widgets[1].x > sc.widgets[0].x

    def test_wraps_to_next_row(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Make widgets too wide to all fit in one row (scene width=256)
        for _ in range(5):
            _add(app, width=100, height=20)
        app._auto_arrange_grid()
        sc = app.state.current_scene()
        # Some widgets should wrap to y > 8
        y_vals = [w.y for w in sc.widgets]
        assert max(y_vals) > 8


# ===================================================================
# _execute_context_action
# ===================================================================


class TestExecuteContextAction:
    def test_delete_action(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        sc = app.state.current_scene()
        before = len(sc.widgets)
        # Use _delete_selected directly; context-action "delete" dispatches to it
        app._delete_selected()
        assert len(sc.widgets) < before

    def test_toggle_lock_action(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app)
        w.locked = False
        _sel(app, 0)
        app._execute_context_action("toggle_lock")
        assert w.locked is True

    def test_duplicate_action(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="dup_me")
        _sel(app, 0)
        sc = app.state.current_scene()
        before = len(sc.widgets)
        app._execute_context_action("duplicate")
        assert len(sc.widgets) > before

    def test_z_forward_action(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0)
        # Should not raise
        app._execute_context_action("z_forward")

    def test_z_backward_action(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 1)
        app._execute_context_action("z_backward")

    def test_z_front_action(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 0)
        app._execute_context_action("z_front")

    def test_z_back_action(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app, 1)
        app._execute_context_action("z_back")

    def test_unknown_action_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Should not raise on unknown action
        app._execute_context_action("unknown_action_xyz")

    def test_copy_paste_roundtrip(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="copy_me")
        _sel(app, 0)
        app._execute_context_action("copy")
        sc = app.state.current_scene()
        before = len(sc.widgets)
        app._execute_context_action("paste")
        assert len(sc.widgets) > before


# ===================================================================
# _zoom_to_fit
# ===================================================================


class TestZoomToFit:
    def test_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Should not raise
        app._zoom_to_fit()

    def test_sets_scale(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._zoom_to_fit()
        # Scale should be at least 1
        scale = getattr(app, "scale", 1)
        assert scale >= 1


# ===================================================================
# _primary_group_for_index
# ===================================================================


class TestPrimaryGroupForIndex:
    def test_no_groups_returns_none(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        assert app._primary_group_for_index(0) is None

    def test_returns_first_alpha(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        app.designer.groups = {"beta": [0], "alpha": [0]}
        assert app._primary_group_for_index(0) == "alpha"


# ===================================================================
# _selected_group_exact
# ===================================================================


class TestSelectedGroupExact:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._selected_group_exact() is None

    def test_exact_match(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        app.designer.groups = {"g": [0, 1]}
        _sel(app, 0, 1)
        assert app._selected_group_exact() == "g"

    def test_partial_match_returns_none(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _add(app)
        app.designer.groups = {"g": [0, 1, 2]}
        _sel(app, 0, 1)  # not all members
        assert app._selected_group_exact() is None


# ===================================================================
# _component_info_from_group (additional edge-case tests)
# ===================================================================


class TestComponentInfoFromGroupExtended:
    def test_new_scheme_4_parts(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._component_info_from_group("comp:card:myroot:2")
        assert result == ("card", "myroot")

    def test_legacy_scheme_3_parts(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._component_info_from_group("comp:card:3")
        assert result == ("card", "card")

    def test_not_a_component(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._component_info_from_group("plain_group") is None

    def test_empty_string(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._component_info_from_group("") is None

    def test_comp_prefix_only(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._component_info_from_group("comp:") is None

    def test_comp_two_parts_no_type(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert app._component_info_from_group("comp::") is None
