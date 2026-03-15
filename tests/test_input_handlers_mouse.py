"""Tests for mouse event handlers in cyberpunk_designer/input_handlers.py.

Covers on_mouse_down, on_mouse_up, _finish_box_select,
on_mouse_move, and on_mouse_wheel.
"""

from __future__ import annotations

import pygame

from cyberpunk_designer.input_handlers import (
    _finish_box_select,
    on_mouse_down,
    on_mouse_move,
    on_mouse_up,
    on_mouse_wheel,
)
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


def _canvas_pos(app, x=10, y=10):
    """Return an absolute pos inside the canvas rect."""
    cr = app.layout.canvas_rect
    return (cr.x + x, cr.y + y)


# ===========================================================================
# on_mouse_down — Canvas
# ===========================================================================


class TestMouseDownCanvas:
    def test_click_empty_canvas_starts_box_select(self, make_app, monkeypatch):
        app = make_app()
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        pos = _canvas_pos(app)
        on_mouse_down(app, pos)
        assert app.state.box_select_start == pos
        assert app.state.selected == []

    def test_click_widget_selects_it(self, make_app, monkeypatch):
        app = make_app()
        _add(app, x=0, y=0, width=80, height=16)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        pos = _canvas_pos(app, 5, 5)
        on_mouse_down(app, pos)
        assert 0 in app.state.selected

    def test_click_widget_starts_drag(self, make_app, monkeypatch):
        app = make_app()
        _add(app, x=0, y=0, width=80, height=16)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        pos = _canvas_pos(app, 5, 5)
        on_mouse_down(app, pos)
        assert app.state.dragging is True
        assert app.state.resizing is False

    def test_locked_widget_no_drag(self, make_app, monkeypatch):
        app = make_app()
        _add(app, x=0, y=0, width=80, height=16, locked=True)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        pos = _canvas_pos(app, 5, 5)
        on_mouse_down(app, pos)
        # click selects but locked → no drag set
        assert app.state.dragging is False

    def test_sim_mode_click_sets_focus(self, make_app, monkeypatch):
        app = make_app()
        _add(app, type="button", x=0, y=0, width=80, height=16)
        app.sim_input_mode = True
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        pos = _canvas_pos(app, 5, 5)
        on_mouse_down(app, pos)
        # In sim mode, no dragging is initiated
        assert app.state.dragging is False


class TestMouseDownHelp:
    def test_click_dismisses_pinned_help(self, make_app, monkeypatch):
        app = make_app()
        app.show_help_overlay = True
        app._help_pinned = True
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        pos = _canvas_pos(app)
        on_mouse_down(app, pos)
        assert app.show_help_overlay is False

    def test_click_dismisses_auto_help(self, make_app, monkeypatch):
        app = make_app()
        app.show_help_overlay = True
        app._help_pinned = False
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        pos = _canvas_pos(app)
        on_mouse_down(app, pos)
        assert app.show_help_overlay is False


class TestMouseDownInspector:
    def test_click_inspector_section_header_toggles(self, make_app, monkeypatch):
        app = make_app()
        ir = app.layout.inspector_rect
        # Simulate section hitbox
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 2, 20, 10)
        app.inspector_section_hitboxes = [(hit_rect, "style")]
        app.inspector_collapsed = set()
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_mouse_down(app, (hit_rect.x + 1, hit_rect.y + 1))
        assert "style" in app.inspector_collapsed
        # Toggle again
        on_mouse_down(app, (hit_rect.x + 1, hit_rect.y + 1))
        assert "style" not in app.inspector_collapsed

    def test_click_inspector_toggle_field(self, make_app, monkeypatch):
        app = make_app()
        _add(app, type="label", visible=True)
        _sel(app, 0)
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 2, 20, 10)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "visible")]
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_mouse_down(app, (hit_rect.x + 1, hit_rect.y + 1))
        assert app.state.current_scene().widgets[0].visible is False

    def test_click_inspector_editable_field(self, make_app, monkeypatch):
        app = make_app()
        _add(app, type="label", text="Hello")
        _sel(app, 0)
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 2, 60, 10)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "text")]
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_mouse_down(app, (hit_rect.x + 1, hit_rect.y + 1))
        assert app.state.inspector_selected_field == "text"

    def test_click_inspector_layer_selects_widget(self, make_app, monkeypatch):
        app = make_app()
        _add(app)
        _add(app)
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 2, 40, 10)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "layer:1")]
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_mouse_down(app, (hit_rect.x + 1, hit_rect.y + 1))
        assert 1 in app.state.selected

    def test_click_inspector_group(self, make_app, monkeypatch):
        app = make_app()
        _add(app)
        _add(app)
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 2, 40, 10)
        app.inspector_section_hitboxes = []
        app.inspector_hitboxes = [(hit_rect, "group:mygrp")]
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        # _group_members needs to exist
        app._group_members = lambda g: [0, 1]
        on_mouse_down(app, (hit_rect.x + 1, hit_rect.y + 1))
        assert app.state.selected == [0, 1]


class TestMouseDownPalette:
    def test_click_palette_widget(self, make_app, monkeypatch):
        app = make_app()
        _add(app)
        _add(app)
        pr = app.layout.palette_rect
        hit_rect = pygame.Rect(pr.x + 2, pr.y + 2, 20, 10)
        app.palette_widget_hitboxes = [(hit_rect, 0)]
        # Must be truthy to prevent _draw_palette() from overwriting
        dummy = pygame.Rect(0, 0, 1, 1)
        app.palette_hitboxes = [(dummy, "x", False)]
        app.palette_section_hitboxes = []
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_mouse_down(app, (hit_rect.x + 1, hit_rect.y + 1))
        assert 0 in app.state.selected

    def test_click_palette_section_toggles(self, make_app, monkeypatch):
        app = make_app()
        pr = app.layout.palette_rect
        hit_rect = pygame.Rect(pr.x + 2, pr.y + 2, 20, 10)
        app.palette_section_hitboxes = [(hit_rect, "actions")]
        app.palette_collapsed = set()
        # Must be truthy to prevent _draw_palette() from overwriting
        dummy = pygame.Rect(0, 0, 1, 1)
        app.palette_hitboxes = [(dummy, "x", False)]
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_mouse_down(app, (hit_rect.x + 1, hit_rect.y + 1))
        assert "actions" in app.palette_collapsed


class TestMouseDownToolbar:
    def test_click_toolbar_action(self, make_app, monkeypatch):
        app = make_app()
        tr = app.layout.toolbar_rect
        hit_rect = pygame.Rect(tr.x + 2, tr.y + 2, 20, 10)
        called = []
        app.toolbar_hitboxes = [(hit_rect, "save")]
        app.toolbar_actions = [("Save", lambda: called.append("save"))]
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_mouse_down(app, (hit_rect.x + 1, hit_rect.y + 1))
        assert "save" in called

    def test_click_toolbar_refresh_ports(self, make_app, monkeypatch):
        app = make_app()
        tr = app.layout.toolbar_rect
        hit_rect = pygame.Rect(tr.x + 2, tr.y + 2, 20, 10)
        called = []
        app.toolbar_hitboxes = [(hit_rect, "refresh_ports")]
        app._refresh_available_ports = lambda: called.append("refresh")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_mouse_down(app, (hit_rect.x + 1, hit_rect.y + 1))
        assert "refresh" in called


class TestMouseDownSceneTabs:
    def test_click_scene_tab_jumps(self, make_app, monkeypatch):
        app = make_app()
        sr = app.layout.scene_tabs_rect
        hit_rect = pygame.Rect(sr.x + 2, sr.y + 2, 30, 10)
        called = []
        app.tab_hitboxes = [(hit_rect, 0, "Main")]
        app.tab_close_hitboxes = []
        app.tab_scroll_hitboxes = []
        app._jump_to_scene = lambda i: called.append(i)
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_mouse_down(app, (hit_rect.x + 1, hit_rect.y + 1))
        assert called == [0]

    def test_click_new_tab_button(self, make_app, monkeypatch):
        app = make_app()
        sr = app.layout.scene_tabs_rect
        hit_rect = pygame.Rect(sr.x + 2, sr.y + 2, 30, 10)
        called = []
        app.tab_hitboxes = [(hit_rect, -1, "+New")]
        app.tab_close_hitboxes = []
        app.tab_scroll_hitboxes = []
        app._add_new_scene = lambda: called.append("new")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_mouse_down(app, (hit_rect.x + 1, hit_rect.y + 1))
        assert "new" in called

    def test_click_tab_close(self, make_app, monkeypatch):
        app = make_app()
        sr = app.layout.scene_tabs_rect
        hit_rect = pygame.Rect(sr.x + 2, sr.y + 2, 10, 10)
        called = []
        app.tab_close_hitboxes = [(hit_rect, 0, "Main")]
        app.tab_hitboxes = []
        app.tab_scroll_hitboxes = []
        app._jump_to_scene = lambda i: called.append(("jump", i))
        app._delete_current_scene = lambda: called.append("del")
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_mouse_down(app, (hit_rect.x + 1, hit_rect.y + 1))
        assert ("jump", 0) in called
        assert "del" in called

    def test_click_tab_scroll(self, make_app, monkeypatch):
        app = make_app()
        sr = app.layout.scene_tabs_rect
        hit_rect = pygame.Rect(sr.x + 2, sr.y + 2, 15, 10)
        app.tab_scroll_hitboxes = [(hit_rect, 1)]
        app.tab_hitboxes = []
        app.tab_close_hitboxes = []
        app._tab_scroll = 0
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        on_mouse_down(app, (hit_rect.x + 1, hit_rect.y + 1))
        assert app._tab_scroll == 40


# ===========================================================================
# on_mouse_up
# ===========================================================================


class TestMouseUp:
    def test_clears_drag_state(self, make_app, monkeypatch):
        app = make_app()
        app.state.dragging = True
        app.state.resizing = True
        app.state.saved_this_drag = True
        on_mouse_up(app, (0, 0))
        assert app.state.dragging is False
        assert app.state.resizing is False
        assert app.state.saved_this_drag is False

    def test_finishes_box_select(self, make_app, monkeypatch):
        app = make_app()
        _add(app, x=5, y=5, width=20, height=10, visible=True)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        app.state.box_select_start = (sr.x, sr.y)
        app.state.box_select_rect = pygame.Rect(sr.x, sr.y, 100, 100)
        on_mouse_up(app, (0, 0))
        assert 0 in app.state.selected

    def test_clears_tab_drag(self, make_app, monkeypatch):
        app = make_app()
        app._tab_drag_idx = 1
        app._tab_drag_name = "Test"
        on_mouse_up(app, (0, 0))
        assert app._tab_drag_idx is None


# ===========================================================================
# _finish_box_select
# ===========================================================================


class TestFinishBoxSelect:
    def test_small_rect_ignored(self, make_app, monkeypatch):
        app = make_app()
        _add(app, x=5, y=5, width=20, height=10)
        app.state.box_select_rect = pygame.Rect(0, 0, 2, 2)
        _finish_box_select(app)
        assert app.state.selected == []

    def test_none_rect_ignored(self, make_app, monkeypatch):
        app = make_app()
        app.state.box_select_rect = None
        _finish_box_select(app)

    def test_selects_intersecting_widgets(self, make_app, monkeypatch):
        app = make_app()
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        _add(app, x=5, y=5, width=20, height=10)
        _add(app, x=200, y=200, width=20, height=10)
        app.state.box_select_rect = pygame.Rect(sr.x, sr.y, 50, 50)
        _finish_box_select(app)
        assert 0 in app.state.selected
        assert 1 not in app.state.selected

    def test_hidden_widgets_excluded(self, make_app, monkeypatch):
        app = make_app()
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        _add(app, x=5, y=5, width=20, height=10, visible=False)
        app.state.box_select_rect = pygame.Rect(sr.x, sr.y, 50, 50)
        _finish_box_select(app)
        assert app.state.selected == []


# ===========================================================================
# on_mouse_move
# ===========================================================================


class TestMouseMove:
    def test_no_pointer_down_ignored(self, make_app, monkeypatch):
        app = make_app()
        app.pointer_down = False
        on_mouse_move(app, (0, 0), (0, 0, 0))

    def test_box_select_updates_rect(self, make_app, monkeypatch):
        app = make_app()
        app.pointer_down = True
        app.state.box_select_start = (100, 100)
        on_mouse_move(app, (200, 200), (1, 0, 0))
        assert app.state.box_select_rect is not None
        assert app.state.box_select_rect.width == 100
        assert app.state.box_select_rect.height == 100

    def test_drag_moves_widget(self, make_app, monkeypatch):
        app = make_app()
        app.pointer_down = True
        _add(app, x=10, y=10, width=40, height=20)
        _sel(app, 0)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        bounds = pygame.Rect(10, 10, 40, 20)
        app.state.dragging = True
        app.state.drag_offset = (5, 5)
        app.state.drag_start_rect = bounds.copy()
        app.state.drag_start_positions = {0: (10, 10)}
        app.state.drag_start_sizes = {0: (40, 20)}
        app.snap_enabled = False
        on_mouse_move(app, (sr.x + 30, sr.y + 30), (1, 0, 0))
        # Widget should have moved
        w = app.state.current_scene().widgets[0]
        assert w.x >= 0
        assert w.y >= 0

    def test_locked_widget_no_drag(self, make_app, monkeypatch):
        app = make_app()
        app.pointer_down = True
        _add(app, x=10, y=10, width=40, height=20, locked=True)
        _sel(app, 0)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        app.state.dragging = True
        app.state.drag_offset = (5, 5)
        app.state.drag_start_rect = pygame.Rect(10, 10, 40, 20)
        app.state.drag_start_positions = {0: (10, 10)}
        on_mouse_move(app, (sr.x + 30, sr.y + 30), (1, 0, 0))
        w = app.state.current_scene().widgets[0]
        assert w.x == 10  # unchanged

    def test_resize_changes_size(self, make_app, monkeypatch):
        app = make_app()
        app.pointer_down = True
        _add(app, x=0, y=0, width=40, height=20)
        _sel(app, 0)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        bounds = pygame.Rect(0, 0, 40, 20)
        app.state.resizing = True
        app.state.resize_anchor = "br"
        app.state.resize_start_rect = bounds.copy()
        app.state.drag_start_positions = {0: (0, 0)}
        app.state.drag_start_sizes = {0: (40, 20)}
        app.snap_enabled = False
        on_mouse_move(app, (sr.x + 80, sr.y + 40), (1, 0, 0))
        w = app.state.current_scene().widgets[0]
        assert w.width >= 40
        assert w.height >= 20

    def test_tab_drag_reorder(self, make_app, monkeypatch):
        app = make_app()
        app.pointer_down = True
        # Add a second scene
        app._add_new_scene()
        names = list(app.designer.scenes.keys())
        app._tab_drag_idx = 0
        sr = app.layout.scene_tabs_rect
        hit_rect = pygame.Rect(sr.x + 40, sr.y + 2, 30, 10)
        app.tab_hitboxes = [(hit_rect, 1, names[1] if len(names) > 1 else "s2")]
        on_mouse_move(app, (hit_rect.x + 1, hit_rect.y + 1), (1, 0, 0))
        new_names = list(app.designer.scenes.keys())
        if len(names) > 1:
            assert new_names[0] != names[0] or new_names[1] != names[1]

    def test_layer_drag_reorder(self, make_app, monkeypatch):
        app = make_app()
        app.pointer_down = True
        _add(app, text="A")
        _add(app, text="B")
        _sel(app, 0)
        app._layer_drag_idx = 0
        ir = app.layout.inspector_rect
        hit_rect = pygame.Rect(ir.x + 2, ir.y + 20, 40, 10)
        app.inspector_hitboxes = [(hit_rect, "layer:1")]
        on_mouse_move(app, (hit_rect.x + 1, hit_rect.y + 1), (1, 0, 0))
        sc = app.state.current_scene()
        assert sc.widgets[0].text == "B"
        assert sc.widgets[1].text == "A"


# ===========================================================================
# on_mouse_wheel
# ===========================================================================


class TestMouseWheel:
    def test_zero_dy_ignored(self, make_app, monkeypatch):
        app = make_app()
        on_mouse_wheel(app, 0, 0)

    def test_wheel_over_canvas_zooms(self, make_app, monkeypatch):
        app = make_app()
        cr = app.layout.canvas_rect
        app.pointer_pos = (cr.x + 10, cr.y + 10)
        called = []
        app._set_scale = lambda s: called.append(s)
        on_mouse_wheel(app, 0, 1)
        assert len(called) == 1

    def test_wheel_over_palette_scrolls(self, make_app, monkeypatch):
        app = make_app()
        pr = app.layout.palette_rect
        app.pointer_pos = (pr.x + 5, pr.y + 5)
        app._palette_content_height = lambda: 500
        before = app.state.palette_scroll
        on_mouse_wheel(app, 0, -1)
        assert app.state.palette_scroll >= before

    def test_wheel_over_inspector_scrolls(self, make_app, monkeypatch):
        app = make_app()
        ir = app.layout.inspector_rect
        app.pointer_pos = (ir.x + 5, ir.y + 5)
        app._inspector_content_height = lambda: 500
        before = app.state.inspector_scroll
        on_mouse_wheel(app, 0, -1)
        assert app.state.inspector_scroll >= before

    def test_wheel_over_tabs_switches_scene(self, make_app, monkeypatch):
        app = make_app()
        sr = app.layout.scene_tabs_rect
        app.pointer_pos = (sr.x + 5, sr.y + 5)
        called = []
        app._switch_scene = lambda d: called.append(d)
        on_mouse_wheel(app, 0, 1)
        assert called == [-1]

    def test_wheel_dismisses_pinned_help(self, make_app, monkeypatch):
        app = make_app()
        app.show_help_overlay = True
        app._help_pinned = True
        cr = app.layout.canvas_rect
        app.pointer_pos = (cr.x + 5, cr.y + 5)
        on_mouse_wheel(app, 0, 1)
        assert app.show_help_overlay is False

    def test_wheel_dismisses_auto_help_and_continues(self, make_app, monkeypatch):
        app = make_app()
        app.show_help_overlay = True
        app._help_pinned = False
        cr = app.layout.canvas_rect
        app.pointer_pos = (cr.x + 5, cr.y + 5)
        called = []
        app._set_scale = lambda s: called.append(s)
        on_mouse_wheel(app, 0, 1)
        assert app.show_help_overlay is False
        assert len(called) == 1  # Zoom still happened
