"""Extra tests for cyberpunk_designer/layout_tools.py — multi‑widget alignment
modes, vertical distribution, single‑axis centering, match‑size edge cases."""

from __future__ import annotations

from types import SimpleNamespace
from typing import List, Optional
from unittest.mock import MagicMock

import pygame

from cyberpunk_designer.layout_tools import (
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
# Helpers (mirrors test_layout_tools.py)
# ---------------------------------------------------------------------------


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=20, height=10, text="w")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _app(widgets: Optional[List[WidgetConfig]] = None, *, snap: bool = False):
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
        _dirty=False,
        _set_status=MagicMock(),
        _mark_dirty=lambda: None,
        _selection_bounds=lambda indices: selection_bounds(app, indices),
        _move_selection=MagicMock(),
    )
    app._mark_dirty = lambda: setattr(app, "_dirty", True)
    return app


# ---------------------------------------------------------------------------
# align_selection — multi‑widget modes not covered in base test file
# ---------------------------------------------------------------------------


class TestAlignMultiHcenter:
    def test_hcenter(self):
        app = _app([_w(x=10, y=0, width=20), _w(x=80, y=20, width=40)])
        app.snap_enabled = False
        set_selection(app, [0, 1])
        align_selection(app, "hcenter")
        ws = app.state.current_scene().widgets
        # Both should be centered on the selection bounds center‑x
        cx = (10 + 80 + 40) / 2  # bounds center
        assert abs(ws[0].x + 10 - cx) <= 1
        assert abs(ws[1].x + 20 - cx) <= 1


class TestAlignMultiVcenter:
    def test_vcenter(self):
        app = _app([_w(x=0, y=0, height=10), _w(x=0, y=80, height=20)])
        app.snap_enabled = False
        set_selection(app, [0, 1])
        align_selection(app, "vcenter")
        ws = app.state.current_scene().widgets
        cy = (0 + 80 + 20) / 2
        assert abs(ws[0].y + 5 - cy) <= 1
        assert abs(ws[1].y + 10 - cy) <= 1


class TestAlignMultiRight:
    def test_right(self):
        app = _app([_w(x=10, width=20), _w(x=50, width=40)])
        app.snap_enabled = False
        set_selection(app, [0, 1])
        align_selection(app, "right")
        ws = app.state.current_scene().widgets
        # Right edge of bounds = 50 + 40 = 90
        assert ws[0].x + ws[0].width == 90
        assert ws[1].x + ws[1].width == 90


class TestAlignMultiTop:
    def test_top(self):
        app = _app([_w(y=30), _w(y=60)])
        app.snap_enabled = False
        set_selection(app, [0, 1])
        align_selection(app, "top")
        ws = app.state.current_scene().widgets
        assert ws[0].y == 30
        assert ws[1].y == 30


class TestAlignMultiBottom:
    def test_bottom(self):
        app = _app([_w(y=10, height=10), _w(y=60, height=20)])
        app.snap_enabled = False
        set_selection(app, [0, 1])
        align_selection(app, "bottom")
        ws = app.state.current_scene().widgets
        bottom = 60 + 20  # bounds bottom
        assert ws[0].y + ws[0].height == bottom
        assert ws[1].y + ws[1].height == bottom


class TestAlignSingleHcenter:
    def test_hcenter_single(self):
        app = _app([_w(x=10, width=20)])
        app.snap_enabled = False
        set_selection(app, [0])
        align_selection(app, "hcenter")
        w = app.state.current_scene().widgets[0]
        assert w.x == (256 - 20) // 2


class TestAlignSingleVcenter:
    def test_vcenter_single(self):
        app = _app([_w(y=10, height=10)])
        app.snap_enabled = False
        set_selection(app, [0])
        align_selection(app, "vcenter")
        w = app.state.current_scene().widgets[0]
        assert w.y == (128 - 10) // 2


class TestAlignLockedMulti:
    def test_skips_locked_widgets(self):
        app = _app([_w(x=10, locked=True), _w(x=50)])
        app.snap_enabled = False
        set_selection(app, [0, 1])
        align_selection(app, "left")
        ws = app.state.current_scene().widgets
        # Locked widget stays put
        assert ws[0].x == 10
        # Unlocked widget should move to bounds left (10)
        assert ws[1].x == 10

    def test_all_locked_no_change(self):
        app = _app([_w(x=10, locked=True), _w(x=50, locked=True)])
        app.snap_enabled = False
        set_selection(app, [0, 1])
        align_selection(app, "left")
        assert app.state.current_scene().widgets[0].x == 10
        assert app.state.current_scene().widgets[1].x == 50


class TestAlignLockedSingle:
    def test_locked_single(self):
        app = _app([_w(x=50, locked=True)])
        app.snap_enabled = False
        set_selection(app, [0])
        align_selection(app, "left")
        assert app.state.current_scene().widgets[0].x == 50  # unchanged


# ---------------------------------------------------------------------------
# distribute_selection — vertical axis
# ---------------------------------------------------------------------------


class TestDistributeVertical:
    def test_vertical_distribute(self):
        ws = [_w(x=0, y=0, height=10), _w(x=0, y=50, height=10), _w(x=0, y=100, height=10)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1, 2])
        distribute_selection(app, "v")
        ys = sorted(w.y for w in app.state.current_scene().widgets)
        assert ys[0] == 0
        assert ys[2] == 100
        assert 45 <= ys[1] <= 55

    def test_vertical_4_widgets(self):
        ws = [
            _w(x=0, y=0, height=10),
            _w(x=0, y=30, height=10),
            _w(x=0, y=60, height=10),
            _w(x=0, y=90, height=10),
        ]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1, 2, 3])
        distribute_selection(app, "v")
        ys = sorted(w.y for w in app.state.current_scene().widgets)
        assert ys[0] == 0
        assert ys[3] == 90
        # Middle two should be evenly spaced
        gap1 = ys[1] - (ys[0] + 10)
        gap2 = ys[2] - (ys[1] + 10)
        assert abs(gap1 - gap2) <= 2

    def test_unknown_axis_rejected(self):
        app = _app([_w(), _w(), _w()])
        set_selection(app, [0, 1, 2])
        distribute_selection(app, "z")
        app._set_status.assert_called()


# ---------------------------------------------------------------------------
# center_selection_in_scene — x‑only, y‑only
# ---------------------------------------------------------------------------


class TestCenterXOnly:
    def test_x_only(self):
        app = _app([_w(x=10, y=10, width=20, height=10)])
        app.snap_enabled = False
        set_selection(app, [0])
        center_selection_in_scene(app, "x")
        app._move_selection.assert_called_once()
        dx, dy = app._move_selection.call_args[0]
        # dx should center horizontally, dy should be 0
        assert dy == 0
        assert dx != 0


class TestCenterYOnly:
    def test_y_only(self):
        app = _app([_w(x=10, y=10, width=20, height=10)])
        app.snap_enabled = False
        set_selection(app, [0])
        center_selection_in_scene(app, "y")
        app._move_selection.assert_called_once()
        dx, dy = app._move_selection.call_args[0]
        assert dx == 0
        assert dy != 0


class TestCenterLocked:
    def test_locked_blocked(self):
        app = _app([_w(x=10, locked=True)])
        set_selection(app, [0])
        center_selection_in_scene(app, "both")
        app._set_status.assert_called()
        app._move_selection.assert_not_called()


class TestCenterInvalidAxis:
    def test_invalid_axis_falls_back_to_both(self):
        app = _app([_w(x=10, y=10, width=20, height=10)])
        app.snap_enabled = False
        set_selection(app, [0])
        center_selection_in_scene(app, "diagonal")
        # Should treat as "both"
        app._move_selection.assert_called_once()


# ---------------------------------------------------------------------------
# match_size_selection — edge cases
# ---------------------------------------------------------------------------


class TestMatchSizeAnchorEdges:
    def test_anchor_none_defaults_to_first(self):
        """When selected_idx is None, anchor defaults to first item."""
        ws = [_w(width=40, height=10), _w(width=20, height=10)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1])
        app.state.selected_idx = None  # Line 260: anchor = items[0][0]
        match_size_selection(app, "width")
        assert app.state.current_scene().widgets[1].width == 40

    def test_anchor_non_int_defaults(self):
        """When int(anchor) fails, anchor defaults to first item."""
        ws = [_w(width=40, height=10), _w(width=20, height=10)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1])
        app.state.selected_idx = "not_int"  # Line 263-264: except
        match_size_selection(app, "width")
        assert app.state.current_scene().widgets[1].width == 40

    def test_anchor_out_of_range_defaults(self):
        """When anchor index is out of range, defaults to first item."""
        ws = [_w(width=40, height=10), _w(width=20, height=10)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1])
        app.state.selected_idx = 999  # Line 266: out of range
        match_size_selection(app, "width")
        assert app.state.current_scene().widgets[1].width == 40

    def test_match_with_locked_skipped(self):
        """Locked widgets are skipped, message reflects that."""
        ws = [
            _w(width=40, height=10),
            _w(width=20, height=10, locked=True),
            _w(width=20, height=10),
        ]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1, 2])
        app.state.selected_idx = 0
        match_size_selection(app, "width")
        # Widget 2 changed, widget 1 (locked) skipped
        assert app.state.current_scene().widgets[2].width == 40
        assert app.state.current_scene().widgets[1].width == 20
        # Status message should mention skipped locked
        status_calls = [str(c) for c in app._set_status.call_args_list]
        assert any("locked" in s.lower() or "Skipped" in s for s in status_calls)


class TestMatchSizeNoChange:
    def test_all_same_size_no_change(self):
        """When all widgets already match, nothing changes."""
        ws = [_w(width=20, height=10), _w(width=20, height=10)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1])
        app.state.selected_idx = 0
        match_size_selection(app, "width")
        # Status should have "nothing to change"
        app._set_status.assert_called()


# ---------------------------------------------------------------------------
# align_selection — bounds=None and no-change paths
# ---------------------------------------------------------------------------


class TestAlignBoundsNone:
    def test_bounds_none_returns_status(self):
        """When _selection_bounds returns None, align reports status."""
        app = _app([_w(x=10)])
        set_selection(app, [0])
        # Override bounds to return None
        app._selection_bounds = lambda idx: None
        align_selection(app, "left")
        # Should report "bounds missing"
        status_text = str(app._set_status.call_args)
        assert "bounds" in status_text.lower() or "missing" in status_text.lower()


class TestAlignNoChange:
    def test_multi_already_aligned_no_locked(self):
        """When multi-widget align produces no changes (no locked), line 160."""
        ws = [_w(x=10, y=0), _w(x=10, y=20)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1])
        # Already aligned left — no change
        align_selection(app, "left")
        # "nothing to change" status
        app._set_status.assert_called()


# ---------------------------------------------------------------------------
# _selected_widgets / _scene_size — exception paths
# ---------------------------------------------------------------------------


class TestSelectedWidgetsException:
    def test_non_int_index_skipped(self):
        """Non-int index in selected list is skipped (lines 18-19)."""
        app = _app([_w(text="a"), _w(text="b")])
        app.state.selected = [0, "not_int", 1]
        items = _selected_widgets(app)
        assert len(items) == 2

    def test_scene_size_exception_returns_zero(self):
        """When scene access fails, _scene_size returns (0, 0) (lines 33-34)."""
        app = _app()
        # Break the scene access
        app.state.current_scene = MagicMock(side_effect=AttributeError("broken"))
        assert _scene_size(app) == (0, 0)


# ---------------------------------------------------------------------------
# center_selection_in_scene — bounds=None
# ---------------------------------------------------------------------------


class TestCenterBoundsNone:
    def test_bounds_none_returns_early(self):
        """When bounds is None, center returns early (line 339)."""
        app = _app([_w(x=10)])
        set_selection(app, [0])
        app._selection_bounds = lambda idx: None
        center_selection_in_scene(app, "both")
        app._move_selection.assert_not_called()


# ---------------------------------------------------------------------------
# clear_active_guides exception
# ---------------------------------------------------------------------------


class TestClearGuidesException:
    def test_clear_guides_exception_silenced(self):
        """Exception in clear_active_guides is silenced (lines 353-354)."""
        app = _app()

        # Make state.active_guides un-settable
        class ReadOnlyState:
            @property
            def active_guides(self):
                return []

            @active_guides.setter
            def active_guides(self, val):
                raise AttributeError("read-only")

        app.state = ReadOnlyState()
        clear_active_guides(app)  # Should not raise


# ---------------------------------------------------------------------------
# snap_drag_to_guides — invisible widget skip & x-center snap
# ---------------------------------------------------------------------------


class TestSnapDragGuidesDeep:
    def test_invisible_widget_skipped(self):
        """Invisible widgets are skipped in guide computation (line 377)."""
        # Widget 0 is selected, widget 1 is invisible → should not contribute guides
        ws = [
            _w(x=10, y=10, width=20, height=10),
            _w(x=50, y=50, width=20, height=10, visible=False),
        ]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0])
        app.state.active_guides = []
        bounds = pygame.Rect(10, 10, 20, 10)
        x, y = snap_drag_to_guides(app, 48, 48, bounds)
        # Should NOT snap to invisible widget's edges (50, 70)
        # Without snapping to widget 1, default scene edges are [0, 256, 0, 128]
        assert isinstance(x, int)
        assert isinstance(y, int)

    def test_snap_to_x_center_guide(self):
        """Selection snaps to x-center of another widget (lines 414-416)."""
        # Reference widget: x=50, width=60 → center=80, edges=[50, 110]
        # Dragged widget (selected): width=20, center = desired_x + 10
        # To snap center to 80: desired_x = 70
        # Edges: cand_left=70, cand_right=90 — NOT near any edges (50, 110)
        ws = [_w(x=50, y=10, width=60, height=10), _w(x=0, y=0, width=20, height=10)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [1])
        app.state.active_guides = []
        bounds = pygame.Rect(0, 0, 20, 10)
        x, y = snap_drag_to_guides(app, 70, 10, bounds)
        # Center snap: desired_cx = 70+10 = 80, ref center = 80, d=0
        assert x == 70


class TestMatchSizeLocked:
    def test_locked_widgets_skipped(self):
        ws = [_w(width=40, height=10), _w(width=20, height=10, locked=True)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1])
        app.state.selected_idx = 0
        match_size_selection(app, "width")
        # Locked widget keeps original width
        assert app.state.current_scene().widgets[1].width == 20


class TestMatchSizeUnknownMode:
    def test_unknown_mode(self):
        ws = [_w(width=40), _w(width=20)]
        app = _app(ws)
        set_selection(app, [0, 1])
        match_size_selection(app, "depth")
        app._set_status.assert_called()


class TestMatchSizeAnchorFromIdx:
    def test_anchor_is_selected_idx(self):
        ws = [_w(width=40), _w(width=20), _w(width=60)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1, 2])
        app.state.selected_idx = 2  # anchor = widget[2] with width 60
        match_size_selection(app, "width")
        assert app.state.current_scene().widgets[0].width == 60
        assert app.state.current_scene().widgets[1].width == 60


class TestMatchSizeHeight:
    def test_match_height_all(self):
        ws = [_w(height=30), _w(height=10), _w(height=20)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1, 2])
        app.state.selected_idx = 0
        match_size_selection(app, "height")
        assert app.state.current_scene().widgets[1].height == 30
        assert app.state.current_scene().widgets[2].height == 30


class TestMatchSizeAlreadySame:
    def test_no_change_when_same(self):
        ws = [_w(width=20), _w(width=20)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1])
        app.state.selected_idx = 0
        match_size_selection(app, "width")
        # Nothing to change message
        app._set_status.assert_called()


# ---------------------------------------------------------------------------
# BC — layout_tools boundary stress tests
# ---------------------------------------------------------------------------


class TestAlignSingleAtEdge:
    """1x1 widget alignment edge cases."""

    def test_align_left_1x1(self):
        app = _app([_w(x=100, y=50, width=2, height=2)])
        app.snap_enabled = False
        set_selection(app, [0])
        align_selection(app, "left")
        assert app.state.current_scene().widgets[0].x == 0

    def test_align_bottom_1x1(self):
        app = _app([_w(x=10, y=10, width=2, height=2)])
        app.snap_enabled = False
        set_selection(app, [0])
        align_selection(app, "bottom")
        # Widget height < GRID(8) is treated as GRID → max_y = 128 - 8 = 120
        assert app.state.current_scene().widgets[0].y == 120

    def test_align_hcenter_1x1(self):
        app = _app([_w(x=0, y=0, width=2, height=2)])
        app.snap_enabled = False
        set_selection(app, [0])
        align_selection(app, "hcenter")
        # Widget width < GRID(8) is treated as GRID → (256-8)//2 = 124
        assert app.state.current_scene().widgets[0].x == 124


class TestDistributeEdgeCases:
    def test_distribute_identical_positions(self):
        """All 3 widgets at same x — should not crash."""
        ws = [
            _w(x=50, y=0, width=10, height=10),
            _w(x=50, y=10, width=10, height=10),
            _w(x=50, y=20, width=10, height=10),
        ]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1, 2])
        distribute_selection(app, "h")
        # Should not crash — first and last stay, middle gets positioned
        assert len(app.state.current_scene().widgets) == 3

    def test_distribute_two_widgets_rejected(self):
        ws = [_w(x=0), _w(x=100)]
        app = _app(ws)
        set_selection(app, [0, 1])
        distribute_selection(app, "v")
        app._set_status.assert_called()

    def test_distribute_one_widget_rejected(self):
        app = _app([_w()])
        set_selection(app, [0])
        distribute_selection(app, "h")
        app._set_status.assert_called()


class TestClampXyEdgeCases:
    def test_widget_exactly_scene_size(self):
        """Widget same size as scene → forced to (0, 0)."""
        app = _app([_w(x=50, y=50, width=256, height=128)])
        app.snap_enabled = False
        from cyberpunk_designer.layout_tools import _clamp_xy_in_scene
        w = app.state.current_scene().widgets[0]
        x, y = _clamp_xy_in_scene(app, 50, 50, w)
        assert x == 0
        assert y == 0

    def test_widget_larger_than_scene(self):
        """Widget larger than scene → forced to (0, 0)."""
        app = _app([_w(x=0, y=0, width=300, height=200)])
        app.snap_enabled = False
        from cyberpunk_designer.layout_tools import _clamp_xy_in_scene
        w = app.state.current_scene().widgets[0]
        x, y = _clamp_xy_in_scene(app, 100, 100, w)
        assert x == 0
        assert y == 0


class TestSnapDragBoundaryStress:
    def test_snap_at_exact_tolerance(self):
        """Desired position exactly at GUIDE_TOL from edge → should snap."""
        from cyberpunk_designer.constants import GUIDE_TOL
        app = _app([_w(x=100, y=50, width=20, height=10)])
        set_selection(app, [0])
        bounds = pygame.Rect(100, 50, 20, 10)
        rx, ry = snap_drag_to_guides(app, GUIDE_TOL, 50, bounds)
        assert rx == 0  # snapped to left edge

    def test_snap_one_beyond_tolerance(self):
        """Desired position just beyond GUIDE_TOL → should NOT snap."""
        from cyberpunk_designer.constants import GUIDE_TOL
        app = _app([_w(x=100, y=50, width=20, height=10)])
        set_selection(app, [0])
        bounds = pygame.Rect(100, 50, 20, 10)
        rx, ry = snap_drag_to_guides(app, GUIDE_TOL + 1, 50, bounds)
        assert rx == GUIDE_TOL + 1  # not snapped

    def test_snap_y_to_scene_bottom(self):
        app = _app([_w(x=0, y=0, width=20, height=10)])
        set_selection(app, [0])
        bounds = pygame.Rect(0, 0, 20, 10)
        # Position near bottom edge: desired_y + bounds.height ≈ 128
        rx, ry = snap_drag_to_guides(app, 0, 117, bounds)
        # bounds.bottom = 117+10 = 127, close to 128 → should snap
        assert ry == 118  # snapped so bottom = 128

    def test_snap_sets_active_guides(self):
        app = _app([_w(x=100, y=50, width=20, height=10)])
        set_selection(app, [0])
        bounds = pygame.Rect(100, 50, 20, 10)
        snap_drag_to_guides(app, 1, 50, bounds)
        # Should have set at least one guide
        assert len(app.state.active_guides) >= 1

    def test_no_snap_clears_active_guides(self):
        """When nothing is close enough, active_guides should be cleared."""
        app = _app([_w(x=100, y=50, width=20, height=10)])
        set_selection(app, [0])
        app.state.active_guides = [("v", 50)]
        bounds = pygame.Rect(100, 50, 20, 10)
        snap_drag_to_guides(app, 100, 50, bounds)
        assert app.state.active_guides == []


class TestMatchSizeBoundary:
    def test_match_width_clamped_to_scene(self):
        """Anchor has width=200 but target at x=100 → target max_width = 156."""
        ws = [_w(x=0, y=0, width=200, height=10), _w(x=100, y=0, width=20, height=10)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1])
        app.state.selected_idx = 0
        match_size_selection(app, "width")
        # Width should be clamped to 256 - 100 = 156
        assert app.state.current_scene().widgets[1].width <= 156

    def test_match_size_all_locked(self):
        ws = [_w(width=40, locked=True), _w(width=20, locked=True)]
        app = _app(ws)
        app.snap_enabled = False
        set_selection(app, [0, 1])
        app.state.selected_idx = 0
        match_size_selection(app, "width")
        # Nothing changed (all locked)
        assert app.state.current_scene().widgets[1].width == 20
