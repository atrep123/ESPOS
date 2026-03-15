"""Tests for CyberpunkEditorApp methods — batch 3.

Covers: _auto_complete_widget, _event_priority, _groups_for_index,
_group_members, _selected_component_group, _component_role_index,
_palette_content_height, _inspector_content_height, _font_settings,
_toggle_lock_selection, _switch_scene, _add_widget, _auto_arrange_grid,
_execute_context_action, _handle_double_click, _zoom_to_fit.
"""

from __future__ import annotations

import pygame

from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    def test_button_gets_default_text(self, make_app):
        app = make_app()
        w = WidgetConfig(type="button", x=0, y=0, width=40, height=16, text="")
        app._auto_complete_widget(w)
        assert w.text == "Button"

    def test_button_keeps_existing_text(self, make_app):
        app = make_app()
        w = WidgetConfig(type="button", x=0, y=0, width=40, height=16, text="OK")
        app._auto_complete_widget(w)
        assert w.text == "OK"

    def test_fills_missing_fg_color(self, make_app):
        app = make_app()
        w = WidgetConfig(type="label", x=0, y=0, width=40, height=16, text="X", color_fg="")
        app._auto_complete_widget(w)
        assert w.color_fg == "#f5f5f5"

    def test_fills_missing_bg_color(self, make_app):
        app = make_app()
        w = WidgetConfig(type="label", x=0, y=0, width=40, height=16, text="X", color_bg="")
        app._auto_complete_widget(w)
        assert w.color_bg == "#000000"

    def test_keeps_existing_colors(self, make_app):
        app = make_app()
        w = WidgetConfig(
            type="label",
            x=0,
            y=0,
            width=40,
            height=16,
            text="X",
            color_fg="#aabbcc",
            color_bg="#112233",
        )
        app._auto_complete_widget(w)
        assert w.color_fg == "#aabbcc"
        assert w.color_bg == "#112233"

    def test_snaps_position_to_grid(self, make_app):
        app = make_app()
        w = WidgetConfig(type="label", x=3, y=5, width=41, height=17, text="X")
        app._auto_complete_widget(w)
        assert w.x % 8 == 0
        assert w.y % 8 == 0
        assert w.width % 8 == 0
        assert w.height % 8 == 0

    def test_label_sizing_expands_narrow(self, make_app):
        app = make_app()
        w = WidgetConfig(type="label", x=0, y=0, width=1, height=1, text="Hello World")
        app._auto_complete_widget(w)
        # Should expand to fit text
        assert w.width > 1
        assert w.height > 1


# ===================================================================
# _event_priority
# ===================================================================


class TestEventPriority:
    def test_quit_has_highest_priority(self, make_app):
        app = make_app()
        ev = pygame.event.Event(pygame.QUIT)
        assert app._event_priority(ev) == 0

    def test_keydown_precedes_mouse(self, make_app):
        app = make_app()
        key_ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode="a", scancode=0)
        mouse_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(0, 0), button=1)
        assert app._event_priority(key_ev) < app._event_priority(mouse_ev)

    def test_unknown_event_type_gets_default(self, make_app):
        app = make_app()
        ev = pygame.event.Event(pygame.USEREVENT)
        assert app._event_priority(ev) == 10

    def test_videoresize_before_keys(self, make_app):
        app = make_app()
        resize_ev = pygame.event.Event(pygame.VIDEORESIZE, size=(800, 600), w=800, h=600)
        key_ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode="a", scancode=0)
        assert app._event_priority(resize_ev) < app._event_priority(key_ev)

    def test_mousewheel_after_mousebuttondown(self, make_app):
        app = make_app()
        wheel = pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1)
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(0, 0), button=1)
        assert app._event_priority(wheel) > app._event_priority(click)

    def test_textinput_lowest_mapped(self, make_app):
        app = make_app()
        ev = pygame.event.Event(pygame.TEXTINPUT, text="a")
        assert app._event_priority(ev) == 8

    def test_mousemotion_priority(self, make_app):
        app = make_app()
        ev = pygame.event.Event(pygame.MOUSEMOTION, pos=(10, 10), rel=(1, 1), buttons=(0, 0, 0))
        assert app._event_priority(ev) == 7


# ===================================================================
# _groups_for_index
# ===================================================================


class TestGroupsForIndex:
    def test_no_groups(self, make_app):
        app = make_app()
        _add(app)
        assert app._groups_for_index(0) == []

    def test_one_group(self, make_app):
        app = make_app()
        _add(app)
        app.designer.groups = {"grp1": [0]}
        assert app._groups_for_index(0) == ["grp1"]

    def test_multiple_groups_sorted(self, make_app):
        app = make_app()
        _add(app)
        app.designer.groups = {"beta": [0], "alpha": [0, 1]}
        result = app._groups_for_index(0)
        assert result == ["alpha", "beta"]

    def test_index_not_in_any_group(self, make_app):
        app = make_app()
        _add(app)
        _add(app)
        app.designer.groups = {"grp": [1]}
        assert app._groups_for_index(0) == []

    def test_groups_is_none_safe(self, make_app):
        app = make_app()
        app.designer.groups = None
        assert app._groups_for_index(0) == []


# ===================================================================
# _group_members
# ===================================================================


class TestGroupMembers:
    def test_basic_members(self, make_app):
        app = make_app()
        _add(app)
        _add(app)
        app.designer.groups = {"g": [0, 1]}
        assert app._group_members("g") == [0, 1]

    def test_filters_out_of_range(self, make_app):
        app = make_app()
        _add(app)
        app.designer.groups = {"g": [0, 5, 99]}
        assert app._group_members("g") == [0]

    def test_deduplicates(self, make_app):
        app = make_app()
        _add(app)
        app.designer.groups = {"g": [0, 0, 0]}
        assert app._group_members("g") == [0]

    def test_returns_sorted(self, make_app):
        app = make_app()
        for _ in range(4):
            _add(app)
        app.designer.groups = {"g": [3, 1, 2]}
        assert app._group_members("g") == [1, 2, 3]

    def test_missing_group_name(self, make_app):
        app = make_app()
        app.designer.groups = {"g": [0]}
        assert app._group_members("nonexistent") == []

    def test_no_groups_attr(self, make_app):
        app = make_app()
        app.designer.groups = None
        assert app._group_members("g") == []


# ===================================================================
# _selected_component_group
# ===================================================================


class TestSelectedComponentGroup:
    def test_no_selection(self, make_app):
        app = make_app()
        assert app._selected_component_group() is None

    def test_no_component_groups(self, make_app):
        app = make_app()
        _add(app)
        _sel(app, 0)
        app.designer.groups = {"plain_group": [0]}
        assert app._selected_component_group() is None

    def test_component_group_match(self, make_app):
        app = make_app()
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

    def test_selection_not_subset_of_members(self, make_app):
        """If selection includes widget not in component group, no match."""
        app = make_app()
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
    def test_basic_roles(self, make_app):
        app = make_app()
        w0 = _add(app)
        w1 = _add(app)
        w0._widget_id = "hdr.title"
        w1._widget_id = "hdr.icon"
        roles = app._component_role_index([0, 1], "hdr")
        assert roles == {"title": 0, "icon": 1}

    def test_no_matching_prefix(self, make_app):
        app = make_app()
        w0 = _add(app)
        w0._widget_id = "other.title"
        roles = app._component_role_index([0], "hdr")
        assert roles == {}

    def test_invalid_indices_ignored(self, make_app):
        app = make_app()
        _add(app)
        roles = app._component_role_index([0, 99], "x")
        assert 99 not in roles.values()

    def test_empty_prefix(self, make_app):
        app = make_app()
        _add(app)
        roles = app._component_role_index([0], "")
        assert roles == {}

    def test_first_role_wins(self, make_app):
        """If two widgets have the same role, first encountered wins."""
        app = make_app()
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
    def test_positive_height(self, make_app):
        app = make_app()
        h = app._palette_content_height()
        assert h > 0

    def test_grows_with_widgets(self, make_app):
        app = make_app()
        h0 = app._palette_content_height()
        for _ in range(5):
            _add(app)
        h5 = app._palette_content_height()
        assert h5 > h0

    def test_collapsed_vs_expanded_height(self, make_app):
        app = make_app()
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
    def test_positive_height(self, make_app):
        app = make_app()
        _add(app)
        _sel(app, 0)
        h = app._inspector_content_height()
        assert h > 0

    def test_minimum_one_row(self, make_app):
        app = make_app()
        # No widget selected — inspector may have minimal rows
        h = app._inspector_content_height()
        assert h >= app.pixel_row_height

    def test_collapsed_sections_reduce(self, make_app):
        app = make_app()
        _add(app)
        _sel(app, 0)
        h_full = app._inspector_content_height()
        # Collapse all inspector sections
        rows, _, _ = app._compute_inspector_rows()
        for key, _ in rows:
            if isinstance(key, str) and key.startswith("_section:"):
                sec = key[len("_section:") :]
                if not hasattr(app, "inspector_collapsed"):
                    app.inspector_collapsed = set()
                app.inspector_collapsed.add(sec)
        h_collapsed = app._inspector_content_height()
        assert h_collapsed <= h_full


# ===================================================================
# _font_settings
# ===================================================================


class TestFontSettings:
    def test_defaults(self, make_app, monkeypatch):
        app = make_app()
        monkeypatch.delenv("ESP32OS_FONT_SIZE", raising=False)
        monkeypatch.delenv("ESP32OS_FONT_SCALE", raising=False)
        size, scale = app._font_settings()
        assert size == 10
        assert scale == 2

    def test_env_override(self, make_app, monkeypatch):
        monkeypatch.setenv("ESP32OS_FONT_SIZE", "14")
        monkeypatch.setenv("ESP32OS_FONT_SCALE", "3")
        app = make_app()
        size, scale = app._font_settings()
        assert size == 14
        assert scale == 3

    def test_clamp_low(self, make_app, monkeypatch):
        monkeypatch.setenv("ESP32OS_FONT_SIZE", "1")
        monkeypatch.setenv("ESP32OS_FONT_SCALE", "0")
        app = make_app()
        size, scale = app._font_settings()
        assert size == 5
        assert scale == 1

    def test_clamp_high(self, make_app, monkeypatch):
        monkeypatch.setenv("ESP32OS_FONT_SIZE", "999")
        monkeypatch.setenv("ESP32OS_FONT_SCALE", "100")
        app = make_app()
        size, scale = app._font_settings()
        assert size == 24
        assert scale == 6

    def test_invalid_env_uses_default(self, make_app, monkeypatch):
        monkeypatch.setenv("ESP32OS_FONT_SIZE", "abc")
        monkeypatch.setenv("ESP32OS_FONT_SCALE", "xyz")
        app = make_app()
        size, scale = app._font_settings()
        assert size == 10
        assert scale == 2


# ===================================================================
# _toggle_lock_selection
# ===================================================================


class TestToggleLockSelection:
    def test_no_selection_status_msg(self, make_app):
        app = make_app()
        app._toggle_lock_selection()
        assert "nothing selected" in (app.dialog_message or "").lower()

    def test_lock_unlocked_widget(self, make_app):
        app = make_app()
        w = _add(app)
        w.locked = False
        _sel(app, 0)
        app._toggle_lock_selection()
        assert w.locked is True

    def test_unlock_locked_widget(self, make_app):
        app = make_app()
        w = _add(app)
        w.locked = True
        _sel(app, 0)
        app._toggle_lock_selection()
        assert w.locked is False

    def test_mixed_locks_to_locked(self, make_app):
        """When some widgets locked and some not, toggle → all locked."""
        app = make_app()
        w0 = _add(app)
        w1 = _add(app)
        w0.locked = True
        w1.locked = False
        _sel(app, 0, 1)
        app._toggle_lock_selection()
        # not all were locked → toggle to locked
        assert w0.locked is True
        assert w1.locked is True

    def test_all_locked_toggles_to_unlocked(self, make_app):
        app = make_app()
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
    def test_single_scene_status(self, make_app):
        app = make_app()
        app._switch_scene(1)
        assert "only one" in (app.dialog_message or "").lower()

    def test_switch_forward(self, make_app):
        app = make_app()
        from ui_models import SceneConfig

        app.designer.scenes["second"] = SceneConfig(
            name="second", width=256, height=128, widgets=[]
        )
        first = app.designer.current_scene
        app._switch_scene(1)
        assert app.designer.current_scene != first

    def test_switch_backward_wraps(self, make_app):
        app = make_app()
        from ui_models import SceneConfig

        app.designer.scenes["second"] = SceneConfig(
            name="second", width=256, height=128, widgets=[]
        )
        first = app.designer.current_scene
        app._switch_scene(-1)
        # Wraps: from first (idx 0) going backward → last scene
        assert app.designer.current_scene != first

    def test_clears_selection(self, make_app):
        app = make_app()
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
    def test_add_label(self, make_app):
        app = make_app()
        sc = app.state.current_scene()
        before = len(sc.widgets)
        app._add_widget("label")
        assert len(sc.widgets) == before + 1
        assert sc.widgets[-1].type == "label"

    def test_add_button(self, make_app):
        app = make_app()
        app._add_widget("button")
        assert app.state.current_scene() is not None

    def test_add_panel(self, make_app):
        app = make_app()
        app._add_widget("panel")
        sc = app.state.current_scene()
        w = sc.widgets[-1]
        assert w.type == "panel"
        assert w.width >= 160

    def test_add_gauge(self, make_app):
        app = make_app()
        app._add_widget("gauge")
        sc = app.state.current_scene()
        w = sc.widgets[-1]
        assert w.type == "gauge"
        assert w.value == 70

    def test_add_slider(self, make_app):
        app = make_app()
        app._add_widget("slider")
        sc = app.state.current_scene()
        assert sc.widgets[-1].type == "slider"

    def test_add_checkbox(self, make_app):
        app = make_app()
        app._add_widget("checkbox")
        sc = app.state.current_scene()
        assert sc.widgets[-1].type == "checkbox"

    def test_add_chart(self, make_app):
        app = make_app()
        app._add_widget("chart")
        sc = app.state.current_scene()
        assert sc.widgets[-1].type == "chart"

    def test_add_icon(self, make_app):
        app = make_app()
        app._add_widget("icon")
        sc = app.state.current_scene()
        w = sc.widgets[-1]
        assert w.type == "icon"
        assert w.icon_char == "@"

    def test_add_progressbar(self, make_app):
        app = make_app()
        app._add_widget("progressbar")
        sc = app.state.current_scene()
        w = sc.widgets[-1]
        assert w.type == "progressbar"
        assert w.value == 65

    def test_add_textbox(self, make_app):
        app = make_app()
        app._add_widget("textbox")
        sc = app.state.current_scene()
        assert sc.widgets[-1].type == "textbox"

    def test_unknown_kind(self, make_app):
        app = make_app()
        before = len(app.state.current_scene().widgets)
        app._add_widget("nonexistent")
        # Unknown type is rejected — no widget added
        assert len(app.state.current_scene().widgets) == before

    def test_selects_new_widget(self, make_app):
        app = make_app()
        app._add_widget("label")
        sc = app.state.current_scene()
        expected_idx = len(sc.widgets) - 1
        assert app.state.selected == [expected_idx]
        assert app.state.selected_idx == expected_idx

    def test_case_insensitive(self, make_app):
        app = make_app()
        app._add_widget("LABEL")
        sc = app.state.current_scene()
        assert sc.widgets[-1].type == "label"


# ===================================================================
# _auto_arrange_grid
# ===================================================================


class TestAutoArrangeGrid:
    def test_empty_scene(self, make_app):
        app = make_app()
        # Should not raise
        app._auto_arrange_grid()

    def test_arranges_in_rows(self, make_app):
        app = make_app()
        for _ in range(3):
            _add(app, width=40, height=16)
        app._auto_arrange_grid()
        sc = app.state.current_scene()
        # First widget at GRID, GRID
        assert sc.widgets[0].x == 8
        assert sc.widgets[0].y == 8
        # Subsequent widgets placed after first
        assert sc.widgets[1].x > sc.widgets[0].x

    def test_wraps_to_next_row(self, make_app):
        app = make_app()
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
    def test_delete_action(self, make_app):
        app = make_app()
        _add(app)
        _sel(app, 0)
        sc = app.state.current_scene()
        before = len(sc.widgets)
        # Use _delete_selected directly; context-action "delete" dispatches to it
        app._delete_selected()
        assert len(sc.widgets) < before

    def test_toggle_lock_action(self, make_app):
        app = make_app()
        w = _add(app)
        w.locked = False
        _sel(app, 0)
        app._execute_context_action("toggle_lock")
        assert w.locked is True

    def test_duplicate_action(self, make_app):
        app = make_app()
        _add(app, text="dup_me")
        _sel(app, 0)
        sc = app.state.current_scene()
        before = len(sc.widgets)
        app._execute_context_action("duplicate")
        assert len(sc.widgets) > before

    def test_z_forward_action(self, make_app):
        app = make_app()
        _add(app)
        _add(app)
        _sel(app, 0)
        # Should not raise
        app._execute_context_action("z_forward")

    def test_z_backward_action(self, make_app):
        app = make_app()
        _add(app)
        _add(app)
        _sel(app, 1)
        app._execute_context_action("z_backward")

    def test_z_front_action(self, make_app):
        app = make_app()
        _add(app)
        _add(app)
        _sel(app, 0)
        app._execute_context_action("z_front")

    def test_z_back_action(self, make_app):
        app = make_app()
        _add(app)
        _add(app)
        _sel(app, 1)
        app._execute_context_action("z_back")

    def test_unknown_action_no_crash(self, make_app):
        app = make_app()
        # Should not raise on unknown action
        app._execute_context_action("unknown_action_xyz")

    def test_copy_paste_roundtrip(self, make_app):
        app = make_app()
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
    def test_no_crash(self, make_app):
        app = make_app()
        # Should not raise
        app._zoom_to_fit()

    def test_sets_scale(self, make_app):
        app = make_app()
        app._zoom_to_fit()
        # Scale should be at least 1
        scale = getattr(app, "scale", 1)
        assert scale >= 1


# ===================================================================
# _primary_group_for_index
# ===================================================================


class TestPrimaryGroupForIndex:
    def test_no_groups_returns_none(self, make_app):
        app = make_app()
        _add(app)
        assert app._primary_group_for_index(0) is None

    def test_returns_first_alpha(self, make_app):
        app = make_app()
        _add(app)
        app.designer.groups = {"beta": [0], "alpha": [0]}
        assert app._primary_group_for_index(0) == "alpha"


# ===================================================================
# _selected_group_exact
# ===================================================================


class TestSelectedGroupExact:
    def test_no_selection(self, make_app):
        app = make_app()
        assert app._selected_group_exact() is None

    def test_exact_match(self, make_app):
        app = make_app()
        _add(app)
        _add(app)
        app.designer.groups = {"g": [0, 1]}
        _sel(app, 0, 1)
        assert app._selected_group_exact() == "g"

    def test_partial_match_returns_none(self, make_app):
        app = make_app()
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
    def test_new_scheme_4_parts(self, make_app):
        app = make_app()
        result = app._component_info_from_group("comp:card:myroot:2")
        assert result == ("card", "myroot")

    def test_legacy_scheme_3_parts(self, make_app):
        app = make_app()
        result = app._component_info_from_group("comp:card:3")
        assert result == ("card", "card")

    def test_not_a_component(self, make_app):
        app = make_app()
        assert app._component_info_from_group("plain_group") is None

    def test_empty_string(self, make_app):
        app = make_app()
        assert app._component_info_from_group("") is None

    def test_comp_prefix_only(self, make_app):
        app = make_app()
        assert app._component_info_from_group("comp:") is None

    def test_comp_two_parts_no_type(self, make_app):
        app = make_app()
        assert app._component_info_from_group("comp::") is None


# ===================================================================
# BD – _coalesce_motion_and_wheel
# ===================================================================


class TestCoalesceMotionAndWheel:
    """Only the *last* MOUSEMOTION and MOUSEWHEEL per frame survive."""

    def test_multiple_motions_keep_last(self, make_app):
        app = make_app()
        evs = [
            pygame.event.Event(pygame.MOUSEMOTION, pos=(1, 1), buttons=(0, 0, 0)),
            pygame.event.Event(pygame.MOUSEMOTION, pos=(2, 2), buttons=(0, 0, 0)),
            pygame.event.Event(pygame.MOUSEMOTION, pos=(3, 3), buttons=(0, 0, 0)),
        ]
        out = app._coalesce_motion_and_wheel(evs)
        motions = [e for e in out if e.type == pygame.MOUSEMOTION]
        assert len(motions) == 1
        assert motions[0].pos == (3, 3)

    def test_multiple_wheels_keep_last(self, make_app):
        app = make_app()
        evs = [
            pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1),
            pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1),
        ]
        out = app._coalesce_motion_and_wheel(evs)
        wheels = [e for e in out if e.type == pygame.MOUSEWHEEL]
        assert len(wheels) == 1
        assert wheels[0].y == -1

    def test_non_motion_events_pass_through(self, make_app):
        app = make_app()
        kd = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0)
        evs = [kd]
        out = app._coalesce_motion_and_wheel(evs)
        assert len(out) == 1
        assert out[0].type == pygame.KEYDOWN

    def test_empty_input(self, make_app):
        app = make_app()
        assert app._coalesce_motion_and_wheel([]) == []

    def test_mixed_events_preserves_order(self, make_app):
        """Non-motion events stay ordered; motion/wheel go to the end."""
        app = make_app()
        k1 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0)
        m1 = pygame.event.Event(pygame.MOUSEMOTION, pos=(5, 5), buttons=(0, 0, 0))
        k2 = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0)
        out = app._coalesce_motion_and_wheel([k1, m1, k2])
        # k1, k2 first, then the motion at the end
        assert out[0].type == pygame.KEYDOWN
        assert out[1].type == pygame.KEYDOWN
        assert out[2].type == pygame.MOUSEMOTION


# ===================================================================
# BD – _dedupe_keydowns
# ===================================================================


class TestDedupeKeydowns:
    """Only the first KEYDOWN per key survives in a single frame batch."""

    def test_duplicate_key_dropped(self, make_app):
        app = make_app()
        evs = [
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0),
        ]
        out = app._dedupe_keydowns(evs)
        kds = [e for e in out if e.type == pygame.KEYDOWN]
        assert len(kds) == 1

    def test_different_keys_both_kept(self, make_app):
        app = make_app()
        evs = [
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0),
        ]
        out = app._dedupe_keydowns(evs)
        assert len(out) == 2

    def test_repeat_flag_dropped(self, make_app):
        app = make_app()
        evs = [
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_x, mod=0, repeat=True),
        ]
        out = app._dedupe_keydowns(evs)
        kds = [e for e in out if e.type == pygame.KEYDOWN]
        assert len(kds) == 0

    def test_non_keydown_passes_through(self, make_app):
        app = make_app()
        evs = [
            pygame.event.Event(pygame.MOUSEMOTION, pos=(1, 1), buttons=(0, 0, 0)),
        ]
        out = app._dedupe_keydowns(evs)
        assert len(out) == 1

    def test_empty_input(self, make_app):
        app = make_app()
        assert app._dedupe_keydowns([]) == []


# ===================================================================
# BD – _dispatch_event: QUIT double-confirm
# ===================================================================


class TestDispatchQuit:
    """QUIT requires double-press when there are dirty scenes."""

    def test_quit_clean_exits_immediately(self, make_app):
        app = make_app()
        app._dirty_scenes.clear()
        ev = pygame.event.Event(pygame.QUIT)
        app._dispatch_event(ev)
        assert app.running is False

    def test_quit_dirty_first_press_warns(self, make_app):
        app = make_app()
        app._dirty_scenes.add("main")
        app._quit_confirm_ts = 0.0
        ev = pygame.event.Event(pygame.QUIT)
        app._dispatch_event(ev)
        # First press: still running, status message set
        assert app.running is True
        assert "Unsaved" in app.dialog_message

    def test_quit_dirty_second_press_exits(self, make_app):
        import time as _time

        app = make_app()
        app._dirty_scenes.add("main")
        # Simulate first press happened recently (within 3s)
        app._quit_confirm_ts = _time.time()
        ev = pygame.event.Event(pygame.QUIT)
        app._dispatch_event(ev)
        assert app.running is False


# ===================================================================
# BD – _dispatch_event: VIDEORESIZE
# ===================================================================


class TestDispatchVideoResize:
    def test_videoresize_calls_handler(self, make_app, monkeypatch):
        app = make_app()
        called = {}

        def fake_resize(a, w, h):
            called["w"] = w
            called["h"] = h

        import cyberpunk_designer.app as app_mod

        monkeypatch.setattr(app_mod.windowing, "handle_video_resize", fake_resize)
        ev = pygame.event.Event(pygame.VIDEORESIZE, w=800, h=600)
        app._dispatch_event(ev)
        assert called == {"w": 800, "h": 600}


# ===================================================================
# BD – _dispatch_event: MOUSEWHEEL edge cases
# ===================================================================


class TestDispatchMouseWheel:
    def test_mousewheel_non_numeric_attrs(self, make_app):
        """MOUSEWHEEL with non-numeric x/y shouldn't crash."""
        app = make_app()
        called = []
        app._on_mouse_wheel = lambda dx, dy: called.append((dx, dy))
        ev = pygame.event.Event(pygame.MOUSEWHEEL, x="bad", y="bad")
        app._dispatch_event(ev)
        assert called == [(0, 0)]

    def test_mousewheel_missing_attrs(self, make_app):
        """MOUSEWHEEL with missing x/y defaults to 0."""
        app = make_app()
        called = []
        app._on_mouse_wheel = lambda dx, dy: called.append((dx, dy))
        ev = pygame.event.Event(pygame.MOUSEWHEEL)
        app._dispatch_event(ev)
        assert called == [(0, 0)]


# ===================================================================
# BD – _dispatch_event: TEXTINPUT edge cases
# ===================================================================


class TestDispatchTextInput:
    def test_textinput_normal(self, make_app):
        app = make_app()
        called = []
        app._on_text_input = lambda t: called.append(t)
        ev = pygame.event.Event(pygame.TEXTINPUT, text="abc")
        app._dispatch_event(ev)
        assert called == ["abc"]

    def test_textinput_missing_text_attr(self, make_app):
        app = make_app()
        called = []
        app._on_text_input = lambda t: called.append(t)
        ev = pygame.event.Event(pygame.TEXTINPUT)
        app._dispatch_event(ev)
        assert called == [""]


# ===================================================================
# BD – _maybe_hide_help_overlay
# ===================================================================


class TestMaybeHideHelpOverlay:
    def test_no_op_when_not_shown(self, make_app):
        app = make_app()
        app.show_help_overlay = False
        app._maybe_hide_help_overlay()
        assert app.show_help_overlay is False

    def test_no_op_when_help_already_dismissed(self, make_app):
        app = make_app()
        app.show_help_overlay = True
        app._help_shown_once = True
        app._maybe_hide_help_overlay()
        # _help_shown_once prevents auto-hide logic
        assert app.show_help_overlay is True

    def test_no_op_when_pinned(self, make_app):
        app = make_app()
        app.show_help_overlay = True
        app._help_shown_once = False
        app._help_pinned = True
        app._maybe_hide_help_overlay()
        assert app.show_help_overlay is True

    def test_hides_after_timeout(self, make_app, monkeypatch):
        app = make_app()
        app.show_help_overlay = True
        app._help_shown_once = False
        app._help_pinned = False
        # Simulate timeout elapsed
        app._help_timer_start = 0.0
        app._help_timeout_sec = 0.001
        import time as _time

        monkeypatch.setattr(_time, "time", lambda: 999.0)
        app._maybe_hide_help_overlay()
        assert app.show_help_overlay is False


# ===================================================================
# BD – _auto_adjust_quality
# ===================================================================


class TestAutoAdjustQuality:
    def test_no_op_when_disabled(self, make_app):
        app = make_app()
        app.auto_optimize = False
        app.fps_history.extend([1.0] * 50)
        app._auto_adjust_quality()
        # Should not crash or change anything

    def test_no_op_with_insufficient_history(self, make_app):
        app = make_app()
        app.auto_optimize = True
        app.fps_history.clear()
        app.fps_history.extend([10.0] * 5)  # < 30 samples
        app._auto_adjust_quality()

    def test_low_fps_disables_grid(self, make_app):
        app = make_app()
        app.auto_optimize = True
        app.show_grid = True
        app.min_acceptable_fps = 30.0
        app.fps_history.clear()
        app.fps_history.extend([5.0] * 40)  # well below threshold
        app._auto_adjust_quality()
        assert app.show_grid is False

    def test_high_fps_enables_grid(self, make_app):
        app = make_app()
        app.auto_optimize = True
        app.show_grid = False
        app.min_acceptable_fps = 30.0
        app.fps_history.clear()
        app.fps_history.extend([120.0] * 40)  # well above 2x threshold
        app._auto_adjust_quality()
        assert app.show_grid is True
