"""Tests for cyberpunk_designer/layout_tools.py — alignment, distribution,
size matching, centering, and guide snapping."""

from __future__ import annotations

from types import SimpleNamespace
from typing import List, Optional
from unittest.mock import MagicMock

import pygame

from cyberpunk_designer.layout_tools import (
    _any_locked,
    _clamp_xy_in_scene,
    _scene_size,
    _selected_widgets,
    align_selection,
    center_selection_in_scene,
    clear_active_guides,
    distribute_selection,
    match_size_selection,
    snap_drag_to_guides,
)
from cyberpunk_designer.selection_ops import selection_bounds, set_selection
from cyberpunk_designer.state import EditorState
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=20, height=10, text="w")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _app(widgets: Optional[List[WidgetConfig]] = None, *, snap: bool = False):
    designer = UIDesigner(256, 128)
    designer.create_scene("main")
    sc = designer.scenes["main"]
    for w in (widgets or []):
        sc.widgets.append(w)
    layout = MagicMock()
    layout.canvas_rect = pygame.Rect(0, 0, 256, 128)
    state = EditorState(designer, layout)
    app = SimpleNamespace(
        designer=designer,
        state=state,
        snap_enabled=snap,
        _dirty=False,
        _set_status=MagicMock(),
        _mark_dirty=lambda: None,
        _selection_bounds=lambda indices: selection_bounds(app, indices),
        _move_selection=MagicMock(),
    )
    app._mark_dirty = lambda: setattr(app, "_dirty", True)
    return app


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


class TestSelectedWidgets:
    def test_returns_indexed_pairs(self):
        app = _app([_w(text="a"), _w(text="b")])
        set_selection(app, [0, 1])
        items = _selected_widgets(app)
        assert len(items) == 2
        assert items[0][0] == 0
        assert items[1][0] == 1

    def test_filters_invalid_indices(self):
        app = _app([_w()])
        app.state.selected = [0, 99]
        items = _selected_widgets(app)
        assert len(items) == 1


class TestAnyLocked:
    def test_none_locked(self):
        assert _any_locked([(0, _w()), (1, _w())]) is False

    def test_one_locked(self):
        assert _any_locked([(0, _w(locked=True)), (1, _w())]) is True


class TestSceneSize:
    def test_returns_scene_dims(self):
        app = _app()
        assert _scene_size(app) == (256, 128)


class TestClampXyInScene:
    def test_clamps_to_bounds(self):
        app = _app([_w(width=20, height=10)])
        app.snap_enabled = False
        w = app.state.current_scene().widgets[0]
        x, y = _clamp_xy_in_scene(app, 300, 200, w)
        assert x <= 256 - 20
        assert y <= 128 - 10

    def test_no_negative(self):
        app = _app([_w(width=20, height=10)])
        app.snap_enabled = False
        w = app.state.current_scene().widgets[0]
        x, y = _clamp_xy_in_scene(app, -50, -50, w)
        assert x >= 0
        assert y >= 0


# ---------------------------------------------------------------------------
# align_selection
# ---------------------------------------------------------------------------


class TestAlignSelection:
    def test_align_left_single(self):
        app = _app([_w(x=50, y=20, width=20, height=10)])
        app.snap_enabled = False
        set_selection(app, [0])
        align_selection(app, "left")
        assert app.state.current_scene().widgets[0].x == 0

    def test_align_right_single(self):
        app = _app([_w(x=10, y=20, width=20, height=10)])
        app.snap_enabled = False
        set_selection(app, [0])
        align_selection(app, "right")
        assert app.state.current_scene().widgets[0].x == 236  # 256 - 20

    def test_align_top_single(self):
        app = _app([_w(x=10, y=50, width=20, height=10)])
        app.snap_enabled = False
        set_selection(app, [0])
        align_selection(app, "top")
        assert app.state.current_scene().widgets[0].y == 0

    def test_align_bottom_single(self):
        app = _app([_w(x=10, y=10, width=20, height=10)])
        app.snap_enabled = False
        set_selection(app, [0])
        align_selection(app, "bottom")
        assert app.state.current_scene().widgets[0].y == 118  # 128 - 10

    def test_align_left_multi(self):
        app = _app([_w(x=10, y=0), _w(x=50, y=20)])
        app.snap_enabled = False
        set_selection(app, [0, 1])
        align_selection(app, "left")
        # Both should align to leftmost x in selection bounds (x=10)
        assert app.state.current_scene().widgets[1].x == 10

    def test_no_selection(self):
        app = _app([_w()])
        align_selection(app, "left")
        app._set_status.assert_called()

    def test_unknown_mode(self):
        app = _app([_w()])
        set_selection(app, [0])
        align_selection(app, "diagonal")
        app._set_status.assert_called()


# ---------------------------------------------------------------------------
# distribute_selection
# ---------------------------------------------------------------------------


class TestDistributeSelection:
    def test_needs_3_widgets(self):
        app = _app([_w(), _w()])
        set_selection(app, [0, 1])
        distribute_selection(app, "h")
        app._set_status.assert_called()

    def test_horizontal_distribute(self):
        ws = [_w(x=0, y=0, width=10, height=10),
              _w(x=100, y=0, width=10, height=10),
              _w(x=200, y=0, width=10, height=10)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1, 2])
        distribute_selection(app, "h")
        xs = sorted(w.x for w in app.state.current_scene().widgets)
        # First stays at 0, last stays at 200
        assert xs[0] == 0
        assert xs[2] == 200
        # Middle should be roughly centered
        assert 90 <= xs[1] <= 110

    def test_locked_blocked(self):
        ws = [_w(x=0, locked=True), _w(x=50), _w(x=100)]
        app = _app(ws)
        set_selection(app, [0, 1, 2])
        distribute_selection(app, "h")
        app._set_status.assert_called()


# ---------------------------------------------------------------------------
# match_size_selection
# ---------------------------------------------------------------------------


class TestMatchSizeSelection:
    def test_match_width(self):
        ws = [_w(width=40, height=10), _w(width=20, height=10)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1])
        app.state.selected_idx = 0  # anchor
        match_size_selection(app, "width")
        # Second widget should match anchor's width
        assert app.state.current_scene().widgets[1].width == 40

    def test_match_height(self):
        ws = [_w(width=20, height=30), _w(width=20, height=10)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1])
        app.state.selected_idx = 0
        match_size_selection(app, "height")
        assert app.state.current_scene().widgets[1].height == 30

    def test_needs_2_widgets(self):
        app = _app([_w()])
        set_selection(app, [0])
        match_size_selection(app, "width")
        app._set_status.assert_called()


# ---------------------------------------------------------------------------
# center_selection_in_scene
# ---------------------------------------------------------------------------


class TestCenterSelectionInScene:
    def test_centers_both_axes(self):
        app = _app([_w(x=0, y=0, width=20, height=10)])
        app.snap_enabled = False
        set_selection(app, [0])
        center_selection_in_scene(app)
        app._move_selection.assert_called_once()

    def test_no_selection(self):
        app = _app([_w()])
        center_selection_in_scene(app)
        app._set_status.assert_called()


# ---------------------------------------------------------------------------
# clear_active_guides
# ---------------------------------------------------------------------------


class TestClearActiveGuides:
    def test_clears(self):
        app = _app()
        app.state.active_guides = [("v", 10)]
        clear_active_guides(app)
        assert app.state.active_guides == []


# ---------------------------------------------------------------------------
# snap_drag_to_guides
# ---------------------------------------------------------------------------


class TestSnapDragToGuides:
    def test_snaps_to_scene_edge(self):
        app = _app([_w(x=100, y=50, width=20, height=10)])
        set_selection(app, [0])
        bounds = pygame.Rect(100, 50, 20, 10)
        # Desired position near left edge (x=2, close to 0)
        rx, ry = snap_drag_to_guides(app, 2, 50, bounds)
        # Should snap to x=0 since it's within tolerance
        assert rx == 0

    def test_no_snap_when_far(self):
        app = _app([_w(x=100, y=50, width=20, height=10)])
        set_selection(app, [0])
        bounds = pygame.Rect(100, 50, 20, 10)
        rx, ry = snap_drag_to_guides(app, 100, 50, bounds)
        # No edge nearby, should stay at desired
        assert rx == 100
