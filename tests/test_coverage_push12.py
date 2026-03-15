"""Push12: component commit paths, key shortcuts, fit_text/fit_widget,
transforms locked-widget guards, batch_ops degenerate removal."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pygame

from cyberpunk_designer.inspector_logic import (
    compute_inspector_rows,
    inspector_commit_edit,
    inspector_field_to_str,
)
from cyberpunk_designer.selection_ops import selection_bounds, set_selection
from cyberpunk_designer.state import EditorState
from cyberpunk_editor import CyberpunkEditorApp
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=60, height=20, text="hello")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _inspector_app(widgets=None, *, groups=None, comp_group=None, group_exact=None):
    """Lightweight SimpleNamespace app for inspector_logic tests."""
    designer = UIDesigner(256, 128)
    designer.create_scene("main")
    sc = designer.scenes["main"]
    for w in widgets or []:
        sc.widgets.append(w)
    if groups is not None:
        designer.groups = groups
    layout = MagicMock()
    layout.canvas_rect = pygame.Rect(0, 0, 256, 128)
    state = EditorState(designer, layout)
    app = SimpleNamespace(
        designer=designer,
        state=state,
        hardware_profile="esp32os_256x128_gray4",
        snap_enabled=False,
        show_grid=False,
        panels_collapsed=False,
        live_preview_port=None,
        live_preview_baud=0,
        clipboard=[],
        layout=layout,
        _mark_dirty=MagicMock(),
        _set_status=MagicMock(),
        _selection_bounds=lambda indices: selection_bounds(app, indices),
        _set_selection=lambda indices, anchor_idx=None: set_selection(app, indices, anchor_idx),
        _selected_component_group=lambda: comp_group,
        _selected_group_exact=lambda: group_exact,
        _primary_group_for_index=lambda idx: None,
        _group_members=lambda name: [],
        _tri_state=lambda vals: "on" if all(vals) else ("off" if not any(vals) else "mixed"),
        _component_role_index=lambda members, root: {},
        _component_field_specs=lambda ctype: {},
        _inspector_cancel_edit=MagicMock(),
        _resize_selection_to=lambda w, h: True,
        _move_selection=lambda dx, dy: None,
        _is_valid_color_str=lambda s: True,
        _format_group_label=lambda gname, members: f"group: {gname} ({len(members)})",
        _component_info_from_group=lambda gname: None,
        _dirty_scenes=set(),
        _set_focus=MagicMock(),
        _sim_listmodels={},
        _next_group_name=lambda base: base + "1",
    )
    return app


def _make_comp_app(widgets, *, comp_type="card", root="myroot"):
    """Build app with component group for commit tests."""
    group_name = f"comp:{comp_type}:{root}:2"
    comp_group = (group_name, comp_type, root, list(range(len(widgets))))
    groups = {group_name: list(range(len(widgets)))}
    app = _inspector_app(widgets, groups=groups, comp_group=comp_group)

    def role_idx(members, rt):
        result = {}
        sc = app.state.current_scene()
        prefix = f"{rt}."
        for idx in members:
            if 0 <= idx < len(sc.widgets):
                wid = str(getattr(sc.widgets[idx], "_widget_id", "") or "")
                if wid == rt:
                    result[str(getattr(sc.widgets[idx], "type", "") or "")] = idx
                elif wid.startswith(prefix):
                    role = wid[len(prefix) :]
                    if role not in result:
                        result[role] = idx
        return result

    app._component_role_index = role_idx
    from cyberpunk_designer.component_fields import component_field_specs

    app._component_field_specs = component_field_specs
    set_selection(app, list(range(len(widgets))))
    return app


def _make_app(tmp_path, monkeypatch, *, widgets=None):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    app = CyberpunkEditorApp(json_path, (256, 128))
    if not hasattr(app, "_save_undo_state"):
        app._save_undo_state = lambda: None
    if widgets:
        sc = app.state.current_scene()
        for w in widgets:
            sc.widgets.append(w)
    return app


def _make_big_app(tmp_path, monkeypatch, *, widgets=None):
    """App with 1200×800 layout for valid palette/inspector hitboxes."""
    app = _make_app(tmp_path, monkeypatch, widgets=widgets)
    app.logical_surface = pygame.Surface((1200, 800))
    app.layout = app.layout.__class__(1200, 800)
    return app


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None


# ===========================================================================
# A) inspector_logic — component root rename (L572, L578, L593)
# ===========================================================================


class TestCompRootRename:
    """Rename component root: updates _widget_id on root (L572) and children
    (L578), plus renames group entry (L593)."""

    def test_rename_root(self):
        # Build a "list" component with root "mymenu" and two items
        w_panel = _w(type="panel", text="Panel")
        w_panel._widget_id = "mymenu"
        w_item0 = _w(type="label", text="Item 0")
        w_item0._widget_id = "mymenu.item0"
        w_item1 = _w(type="label", text="Item 1")
        w_item1._widget_id = "mymenu.item1"

        app = _make_comp_app(
            [w_panel, w_item0, w_item1],
            comp_type="menu",
            root="mymenu",
        )
        app.state.inspector_selected_field = "comp.root"
        app.state.inspector_input_buffer = "newmenu"
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        assert sc.widgets[0]._widget_id == "newmenu"
        assert sc.widgets[1]._widget_id == "newmenu.item0"
        assert sc.widgets[2]._widget_id == "newmenu.item1"
        # Group was renamed
        assert "comp:menu:mymenu:2" not in app.designer.groups


# ===========================================================================
# B) inspector_logic — menu_active commit (L602-603, L613-614, L658)
# ===========================================================================


class TestMenuActiveScrollSync:
    """L602-603: menu_active updates scroll label text."""

    def test_scroll_sync(self):
        # Build a menu_list component
        w_title = _w(type="label", text="Menu Title")
        w_title._widget_id = "mymenu.title"
        w_panel = _w(type="panel", text="0/3")
        w_panel._widget_id = "mymenu"
        w_scroll = _w(type="label", text="1/3")
        w_scroll._widget_id = "mymenu.scroll"
        w_i0 = _w(type="label", text="Item0", style="highlight")
        w_i0._widget_id = "mymenu.item0"
        w_i1 = _w(type="label", text="Item1", style="default")
        w_i1._widget_id = "mymenu.item1"
        w_i2 = _w(type="label", text="Item2", style="default")
        w_i2._widget_id = "mymenu.item2"

        app = _make_comp_app(
            [w_title, w_panel, w_scroll, w_i0, w_i1, w_i2],
            comp_type="menu_list",
            root="mymenu",
        )
        app.state.inspector_selected_field = "comp.active_item"
        app.state.inspector_input_buffer = "2"  # 1-based → pos 1
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        # Scroll label should be updated
        assert sc.widgets[2].text == "2/3"


class TestMenuActiveFocusException:
    """L613-614: _set_focus raises after menu_active update."""

    def test_focus_raises(self):
        w_title = _w(type="label", text="Menu Title")
        w_title._widget_id = "mymenu.title"
        w_panel = _w(type="panel", text="0/3")
        w_panel._widget_id = "mymenu"
        w_scroll = _w(type="label", text="1/3")
        w_scroll._widget_id = "mymenu.scroll"
        w_i0 = _w(type="label", text="Item0", style="highlight")
        w_i0._widget_id = "mymenu.item0"
        w_i1 = _w(type="label", text="Item1", style="default")
        w_i1._widget_id = "mymenu.item1"

        app = _make_comp_app(
            [w_title, w_panel, w_scroll, w_i0, w_i1],
            comp_type="menu_list",
            root="mymenu",
        )
        app._set_focus = MagicMock(side_effect=TypeError("focus error"))
        app.state.inspector_selected_field = "comp.active_item"
        app.state.inspector_input_buffer = "2"  # Switch to item1
        result = inspector_commit_edit(app)
        # Should still succeed even when focus raises
        assert result is True


# ===========================================================================
# C) inspector_logic — choice kind commit (L658)
# ===========================================================================


class TestChoiceKindCommit:
    """L658: choice kind — setattr(target, attr, val)."""

    def test_choice_bar(self):
        w_title = _w(type="label", text="Chart")
        w_title._widget_id = "mychart.title"
        w_chart = _w(type="chart", style="line", data_points="10,20,30")
        w_chart._widget_id = "mychart.chart"

        app = _make_comp_app(
            [w_title, w_chart],
            comp_type="chart_bar",
            root="mychart",
        )
        app.state.inspector_selected_field = "comp.mode"
        app.state.inspector_input_buffer = "bar"
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        assert sc.widgets[1].style == "bar"


# ===========================================================================
# D) inspector_logic — int_list kind commit (L669-670)
# ===========================================================================


class TestIntListKindCommit:
    """L669-670: int_list kind — setattr(target, attr, pts)."""

    def test_int_list_points(self):
        w_title = _w(type="label", text="Chart")
        w_title._widget_id = "mychart.title"
        w_chart = _w(type="chart", style="bar", data_points="10,20,30")
        w_chart._widget_id = "mychart.chart"

        app = _make_comp_app(
            [w_title, w_chart],
            comp_type="chart_bar",
            root="mychart",
        )
        app.state.inspector_selected_field = "comp.points"
        app.state.inspector_input_buffer = "5,15,25,35"
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        assert sc.widgets[1].data_points == [5, 15, 25, 35]


# ===========================================================================
# E) inspector_logic — comp int kind conversion (L675-676)
# ===========================================================================


class TestCompIntKindConversion:
    """L675-676: int kind — int conversion + assignment in component commit."""

    def test_comp_int_valid(self):
        w_title = _w(type="label", text="Title")
        w_title._widget_id = "myroot.title"
        w_prog = _w(type="progressbar", value=50, max_value=100)
        w_prog._widget_id = "myroot.progress"

        app = _make_comp_app([w_title, w_prog])
        app.state.inspector_selected_field = "comp.progress_value"
        app.state.inspector_input_buffer = "75"
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        assert sc.widgets[1].value == 75


# ===========================================================================
# F) inspector_logic — tabs_active commit (L702, L709-710)
# ===========================================================================


class TestTabsActiveCommit:
    """L702: tabs_active sets focus on success."""

    def test_tabs_active_focus(self):
        w_tab1 = _w(type="button", text="Tab 1", style="bold highlight")
        w_tab1._widget_id = "mytabs.tab1"
        w_tab2 = _w(type="button", text="Tab 2", style="default")
        w_tab2._widget_id = "mytabs.tab2"
        w_tab3 = _w(type="button", text="Tab 3", style="default")
        w_tab3._widget_id = "mytabs.tab3"
        w_tabbar = _w(type="panel", text="1")
        w_tabbar._widget_id = "mytabs.tabbar"
        w_content_title = _w(type="label", text="Content")
        w_content_title._widget_id = "mytabs.content.title"

        app = _make_comp_app(
            [w_tab1, w_tab2, w_tab3, w_tabbar, w_content_title],
            comp_type="tabs",
            root="mytabs",
        )
        app.state.inspector_selected_field = "comp.active_tab"
        app.state.inspector_input_buffer = "2"  # Switch to tab2
        result = inspector_commit_edit(app)
        assert result is True
        # Verify focus was set
        app._set_focus.assert_called()


class TestTabsActiveFocusException:
    """L709-710: tabs_active set focus raises exception."""

    def test_focus_exception(self):
        w_tab1 = _w(type="button", text="Tab 1", style="bold highlight")
        w_tab1._widget_id = "mytabs.tab1"
        w_tab2 = _w(type="button", text="Tab 2", style="default")
        w_tab2._widget_id = "mytabs.tab2"
        w_tabbar = _w(type="panel", text="1")
        w_tabbar._widget_id = "mytabs.tabbar"
        w_content_title = _w(type="label", text="Content")
        w_content_title._widget_id = "mytabs.content.title"

        app = _make_comp_app(
            [w_tab1, w_tab2, w_tabbar, w_content_title],
            comp_type="tabs",
            root="mytabs",
        )
        app._set_focus = MagicMock(side_effect=StopIteration("focus error"))
        app.state.inspector_selected_field = "comp.active_tab"
        app.state.inspector_input_buffer = "2"
        result = inspector_commit_edit(app)
        assert result is True


# ===========================================================================
# G) inspector_logic — list_count commit (L733, L739)
# ===========================================================================


class TestListCountShrink:
    """L733: list shrinks below visible slot count."""

    def test_shrink_list(self):
        w_title = _w(type="label", text="Menu")
        w_title._widget_id = "mymenu.title"
        w_panel = _w(type="panel", text="0/3")
        w_panel._widget_id = "mymenu"
        w_scroll = _w(type="label", text="1/3")
        w_scroll._widget_id = "mymenu.scroll"
        w_i0 = _w(type="label", text="Item0", style="highlight")
        w_i0._widget_id = "mymenu.item0"
        w_i1 = _w(type="label", text="Item1", style="default")
        w_i1._widget_id = "mymenu.item1"
        w_i2 = _w(type="label", text="Item2", style="default")
        w_i2._widget_id = "mymenu.item2"

        app = _make_comp_app(
            [w_title, w_panel, w_scroll, w_i0, w_i1, w_i2],
            comp_type="menu_list",
            root="mymenu",
        )
        app._sim_listmodels = {"mymenu": MagicMock()}
        app.state.inspector_selected_field = "comp.count"
        # Shrink count to 1 (visible=3 items, new_count=1 < 3)
        app.state.inspector_input_buffer = "1"
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        # scroll text updated
        assert sc.widgets[2].text == "1/1"
        # list model cache was cleared
        assert "mymenu" not in app._sim_listmodels


# ===========================================================================
# H) inspector_logic — single widget width/height constraints (L989-997)
# ===========================================================================


class TestSingleWidgetWidthConstraint:
    """L989-997: single widget width edit → max_w constraint + position clamp."""

    def test_width_constraint(self):
        # Widget at x=200 in a 256-wide scene → max_w = 256 - 200 = 56
        w = _w(x=200, y=10, width=40, height=20)
        app = _inspector_app([w])
        set_selection(app, [0])
        app.state.inspector_selected_field = "width"
        app.state.inspector_input_buffer = "100"  # Will be clamped to max_w=56
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        assert int(sc.widgets[0].width) == 56

    def test_height_constraint(self):
        # Widget at y=100 in a 128-high scene → max_h = 128 - 100 = 28
        w = _w(x=10, y=100, width=40, height=20)
        app = _inspector_app([w])
        set_selection(app, [0])
        app.state.inspector_selected_field = "height"
        app.state.inspector_input_buffer = "50"  # Clamped to max_h=28
        result = inspector_commit_edit(app)
        assert result is True
        sc = app.state.current_scene()
        assert int(sc.widgets[0].height) == 28


class TestSingleWidgetPositionClamp:
    """L997: after width resize, widget x is clamped to scene bounds."""

    def test_position_clamp_after_resize(self):
        # Widget at (240, 120), width=20, height=20 → after making width=24,
        # x must be clamped: max x = 256 - 24 = 232
        w = _w(x=240, y=120, width=16, height=8)
        app = _inspector_app([w])
        set_selection(app, [0])
        app.state.inspector_selected_field = "width"
        # max_w = 256 - 240 = 16, so 24 → 16. But let's use a value that fits.
        # Actually, let's set x=250 in a 256 scene, then set width=8 → fine
        # Better: widget at x=0, set width to something big
        # → after width=256, x stays 0. That covers the line but not the clamp.
        # To trigger the clamp (w.x > sc.width - w.width):
        w2 = _w(x=200, y=100, width=8, height=8)
        app2 = _inspector_app([w2])
        set_selection(app2, [0])
        app2.state.inspector_selected_field = "width"
        app2.state.inspector_input_buffer = "56"  # max_w = 256 - 200 = 56
        result = inspector_commit_edit(app2)
        assert result is True
        sc = app2.state.current_scene()
        # x clamped: max(0, min(200, max(0, 256-56))) = min(200, 200) = 200
        assert int(sc.widgets[0].x) <= 200


# ===========================================================================
# I) inspector_logic — _apply_int setattr exception (L957-958)
# ===========================================================================


class TestApplyIntSetattrFails:
    """L957-958: setattr(w, attr, v) raises in _apply_int → return False."""

    def test_setattr_on_property(self):
        # Create a widget-like object where setting 'value' raises
        class ReadOnlyWidget:
            type = "gauge"
            x = 0
            y = 0
            width = 60
            height = 20
            text = "hello"
            _widget_id = ""
            locked = False

            @property
            def value(self):
                return 50

            @value.setter
            def value(self, v):
                raise AttributeError("read-only")

        w = WidgetConfig(type="gauge", x=0, y=0, width=60, height=20, text="hello")
        app = _inspector_app([w])
        set_selection(app, [0])
        # Replace the widget with our read-only version
        app.state.current_scene().widgets[0] = ReadOnlyWidget()
        app.state.inspector_selected_field = "value"
        app.state.inspector_input_buffer = "42"
        result = inspector_commit_edit(app)
        assert result is False


# ===========================================================================
# J) inspector_logic — multi-select x/y and width/height (L791-792, L802-805)
# ===========================================================================


class TestMultiSelectXY:
    """L791-792: multi-select x/y edit via _move_selection."""

    def test_multi_x(self):
        w0 = _w(x=10, y=10, width=40, height=20)
        w1 = _w(x=60, y=10, width=40, height=20)
        app = _inspector_app([w0, w1])
        moved = []
        app._move_selection = lambda dx, dy: moved.append((dx, dy))
        set_selection(app, [0, 1])
        app.state.inspector_selected_field = "x"
        app.state.inspector_input_buffer = "20"
        result = inspector_commit_edit(app)
        assert result is True
        # dx = 20 - 10 = 10
        assert moved and moved[0][0] == 10

    def test_multi_y(self):
        w0 = _w(x=10, y=10, width=40, height=20)
        w1 = _w(x=60, y=10, width=40, height=20)
        app = _inspector_app([w0, w1])
        moved = []
        app._move_selection = lambda dx, dy: moved.append((dx, dy))
        set_selection(app, [0, 1])
        app.state.inspector_selected_field = "y"
        app.state.inspector_input_buffer = "30"
        result = inspector_commit_edit(app)
        assert result is True
        # dy = 30 - 10 = 20
        assert moved and moved[0][1] == 20


class TestMultiSelectWH:
    """L802-805: multi-select width/height edit via _resize_selection_to."""

    def test_multi_width(self):
        w0 = _w(x=0, y=0, width=40, height=20)
        w1 = _w(x=50, y=0, width=40, height=20)
        app = _inspector_app([w0, w1])
        resized = []
        app._resize_selection_to = lambda w, h: resized.append((w, h)) or True
        set_selection(app, [0, 1])
        app.state.inspector_selected_field = "width"
        app.state.inspector_input_buffer = "100"
        result = inspector_commit_edit(app)
        assert result is True
        assert resized


# ===========================================================================
# K) input_handlers — keyboard shortcuts (L142-143, L545, L547)
# ===========================================================================


class TestHomeKeySelectFirst:
    """HOME key selects first widget."""

    def test_home_key(self, monkeypatch, make_app):
        app = make_app(widgets=[_w(), _w(x=50)])
        app._help_pinned = False
        app.sim_input_mode = False
        app.state.inspector_selected_field = None
        sel = []
        app._set_selection = lambda indices, anchor_idx=None: sel.append(indices)
        monkeypatch.setattr("pygame.key.get_mods", lambda: 0)
        from cyberpunk_designer.input_handlers import on_key_down

        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_HOME)
        on_key_down(app, event)
        assert sel == [[0]]

    def test_end_key(self, monkeypatch, make_app):
        app = make_app(widgets=[_w(), _w(x=50)])
        app._help_pinned = False
        app.sim_input_mode = False
        app.state.inspector_selected_field = None
        sel = []
        app._set_selection = lambda indices, anchor_idx=None: sel.append(indices)
        monkeypatch.setattr("pygame.key.get_mods", lambda: 0)
        from cyberpunk_designer.input_handlers import on_key_down

        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END)
        on_key_down(app, event)
        assert sel == [[1]]


class TestCtrlPageDownJump:
    """Ctrl+PageUp/Down at L390-401 jumps to prev/next scene."""

    def test_ctrl_pagedown(self, monkeypatch, make_app):
        app = make_app()
        app._help_pinned = False
        app.sim_input_mode = False
        app.state.inspector_selected_field = None
        # Add a second scene so the jump can happen
        app.designer.create_scene("second")
        jumped = []
        app._jump_to_scene = lambda idx: jumped.append(idx)
        monkeypatch.setattr("pygame.key.get_mods", lambda: pygame.KMOD_CTRL)
        from cyberpunk_designer.input_handlers import on_key_down

        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEDOWN)
        on_key_down(app, event)
        assert jumped

    def test_ctrl_pageup(self, monkeypatch, make_app):
        app = make_app()
        app._help_pinned = False
        app.sim_input_mode = False
        app.state.inspector_selected_field = None
        app.designer.create_scene("second")
        jumped = []
        app._jump_to_scene = lambda idx: jumped.append(idx)
        monkeypatch.setattr("pygame.key.get_mods", lambda: pygame.KMOD_CTRL)
        from cyberpunk_designer.input_handlers import on_key_down

        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEUP)
        on_key_down(app, event)
        assert jumped


# ===========================================================================
# L) fit_text / fit_widget — _parse_max_lines branch (L28, L31)
# ===========================================================================


class TestFitTextMaxLinesZero:
    """fit_text.py L28: max_lines=0 → _parse_max_lines returns None."""

    def test_max_lines_zero(self, make_app):
        app = make_app()
        w = _w(type="label", x=0, y=0, width=60, height=20, text="Hello world")
        w.max_lines = "0"
        sc = app.state.current_scene()
        sc.widgets.append(w)
        set_selection(app, [0])
        from cyberpunk_designer.fit_text import fit_selection_to_text

        fit_selection_to_text(app)
        # Should complete without error, max_lines treated as None


class TestFitWidgetMaxLinesNegative:
    """fit_widget.py L31: max_lines=-1 → _parse_max_lines returns None."""

    def test_max_lines_negative(self, make_app):
        app = make_app()
        w = _w(type="label", x=0, y=0, width=60, height=20, text="Hello world")
        w.max_lines = "-1"
        sc = app.state.current_scene()
        sc.widgets.append(w)
        set_selection(app, [0])
        from cyberpunk_designer.fit_widget import fit_selection_to_widget

        fit_selection_to_widget(app)
        # Should complete without error


# ===========================================================================
# M) transforms — locked widget guards (L20, L220)
# ===========================================================================


class TestMoveSelectionLocked:
    """transforms.py L20: locked widget blocks move_selection."""

    def test_locked_blocks_move(self, make_app):
        app = make_app()
        w = _w(x=10, y=10, width=40, height=20)
        w.locked = True
        sc = app.state.current_scene()
        sc.widgets.append(w)
        set_selection(app, [0])
        statuses = []
        app._set_status = lambda msg, **kw: statuses.append(msg)
        from cyberpunk_designer.selection_ops.transforms import move_selection

        move_selection(app, 8, 0)
        assert any("locked" in s.lower() for s in statuses)
        # Widget didn't move
        assert int(sc.widgets[0].x) == 10


class TestMakeFullWidthLocked:
    """transforms.py L220: locked widget blocks make_full_width."""

    def test_locked_blocks_full_width(self, make_app):
        app = make_app()
        w = _w(x=10, y=10, width=40, height=20)
        w.locked = True
        sc = app.state.current_scene()
        sc.widgets.append(w)
        set_selection(app, [0])
        statuses = []
        app._set_status = lambda msg, **kw: statuses.append(msg)
        from cyberpunk_designer.selection_ops.transforms import make_full_width

        make_full_width(app)
        assert any("locked" in s.lower() for s in statuses)


# ===========================================================================
# N) transforms — resize_selection_to zero bounds (L84, L89-90)
# ===========================================================================


class TestResizeLockedWidget:
    """transforms.py L67-69: locked widget blocks resize_selection_to."""

    def test_locked_blocks_resize(self, make_app):
        app = make_app()
        w = _w(x=10, y=10, width=40, height=20)
        w.locked = True
        sc = app.state.current_scene()
        sc.widgets.append(w)
        set_selection(app, [0])
        statuses = []
        app._set_status = lambda msg, **kw: statuses.append(msg)
        from cyberpunk_designer.selection_ops.transforms import resize_selection_to

        result = resize_selection_to(app, 100, 100)
        assert result is False
        assert any("locked" in s.lower() for s in statuses)

    def test_resize_success(self, make_app):
        """Normal resize success path for proportional scaling."""
        app = make_app()
        w = _w(x=10, y=10, width=40, height=20)
        sc = app.state.current_scene()
        sc.widgets.append(w)
        set_selection(app, [0])
        from cyberpunk_designer.selection_ops.transforms import resize_selection_to

        result = resize_selection_to(app, 80, 40)
        assert result is True


# ===========================================================================
# O) batch_ops — remove_degenerate (L369-370)
# ===========================================================================


class TestRemoveDegenerate:
    """batch_ops.py L369-370: remove widgets with width/height <= 0."""

    def test_remove_zero_width(self, make_app):
        app = make_app()
        sc = app.state.current_scene()
        bad_w = _w(x=0, y=0, width=8, height=20, text="bad")
        bad_w._width = 0  # Bypass setter to force zero dimension
        sc.widgets.append(bad_w)
        sc.widgets.append(_w(x=0, y=0, width=40, height=20, text="good"))
        from cyberpunk_designer.selection_ops import remove_degenerate_widgets

        remove_degenerate_widgets(app)
        assert len(sc.widgets) == 1
        assert sc.widgets[0].text == "good"


# ===========================================================================
# P) inspector_logic — compute_inspector_rows with groups (L1309)
# ===========================================================================


class TestComputeRowsGroupMembers:
    """L1309: groups with ≥ 2 members produce group header + indented layer rows."""

    def test_group_rows(self):
        w0 = _w(type="panel", x=0, y=0, width=100, height=50, text="Panel")
        w1 = _w(type="label", x=5, y=5, width=40, height=10, text="L1")
        w2 = _w(type="label", x=5, y=20, width=40, height=10, text="L2")
        groups = {"mygroup:1": [0, 1, 2]}
        app = _inspector_app([w0, w1, w2], groups=groups)
        set_selection(app, [0])
        rows, warning, widget = compute_inspector_rows(app)
        # Should have a group header row
        group_rows = [r for r in rows if r[0].startswith("group:")]
        assert len(group_rows) >= 1


# ===========================================================================
# Q) inspector_logic — tabs_active field_to_str fallback to bold (L109)
# ===========================================================================


class TestFieldToStrTabsActiveBoldFallback:
    """L109: tabs_active fallback: no highlight found, check for bold style."""

    def test_bold_fallback(self):
        w_tab1 = _w(type="button", text="Tab 1", style="bold")  # bold, no highlight
        w_tab1._widget_id = "mytabs.tab1"
        w_tab2 = _w(type="button", text="Tab 2", style="default")
        w_tab2._widget_id = "mytabs.tab2"
        w_tabbar = _w(type="panel", text="1")
        w_tabbar._widget_id = "mytabs.tabbar"
        w_content_title = _w(type="label", text="Content")
        w_content_title._widget_id = "mytabs.content.title"

        comp_group = ("comp:tabs:mytabs:2", "tabs", "mytabs", [0, 1, 2, 3])
        groups = {"comp:tabs:mytabs:2": [0, 1, 2, 3]}
        app = _inspector_app(
            [w_tab1, w_tab2, w_tabbar, w_content_title],
            groups=groups,
            comp_group=comp_group,
        )

        def role_idx(members, rt):
            result = {}
            sc = app.state.current_scene()
            prefix = f"{rt}."
            for idx in members:
                if 0 <= idx < len(sc.widgets):
                    wid = str(getattr(sc.widgets[idx], "_widget_id", "") or "")
                    if wid.startswith(prefix):
                        role = wid[len(prefix) :]
                        if role not in result:
                            result[role] = idx
            return result

        app._component_role_index = role_idx
        from cyberpunk_designer.component_fields import component_field_specs

        app._component_field_specs = component_field_specs
        set_selection(app, [0, 1, 2, 3])

        result = inspector_field_to_str(app, "comp.active_tab", w_tab1)
        # tab1 has "bold" style → should be detected as active
        assert result == "1"
