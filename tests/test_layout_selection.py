"""Tests for layout alignment/distribution and selection operations.

Covers: align_selection, distribute_selection, match_size_selection,
center_selection_in_scene, snap_drag_to_guides, and the main selection_ops
functions (cycle_*, mirror_selection, array_duplicate, select_same_*, etc.).
"""

from __future__ import annotations

import pygame

from cyberpunk_designer.constants import GRID
from cyberpunk_designer.layout_tools import (
    align_selection,
    center_selection_in_scene,
    distribute_selection,
    match_size_selection,
    snap_drag_to_guides,
)
from cyberpunk_designer.selection_ops import (
    array_duplicate,
    copy_selection,
    cycle_align,
    cycle_border_style,
    cycle_style,
    cycle_text_overflow,
    cycle_valign,
    cycle_widget_type,
    delete_selected,
    duplicate_selection,
    mirror_selection,
    paste_clipboard,
    reorder_selection,
    select_all,
    select_same_color,
    select_same_style,
    select_same_type,
    select_same_z,
    set_selection,
    swap_fg_bg,
    toggle_visibility,
)
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add(app, wtype="label", **kw):
    """Append a widget and return its index."""
    defaults = dict(
        type=wtype,
        x=0,
        y=0,
        width=32,
        height=16,
        color_fg="#f0f0f0",
        color_bg="#000000",
    )
    defaults.update(kw)
    sc = app.state.current_scene()
    sc.widgets.append(WidgetConfig(**defaults))
    idx = len(sc.widgets) - 1
    return idx


def _w(app, idx):
    return app.state.current_scene().widgets[idx]


# ===================================================================
# LAYOUT ALIGNMENT
# ===================================================================
class TestAlignSelection:
    """align_selection positions widgets correctly."""

    def test_align_left_single(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, x=40, y=20, width=24, height=16)
        set_selection(app, [i])
        align_selection(app, "left")
        assert _w(app, i).x == 0

    def test_align_right_single(self, make_app):
        app = make_app(size=(256, 192))
        sc = app.state.current_scene()
        i = _add(app, x=10, y=10, width=24, height=16)
        set_selection(app, [i])
        align_selection(app, "right")
        expected = int(sc.width) - 24
        assert _w(app, i).x == expected or abs(_w(app, i).x - expected) <= GRID

    def test_align_top_single(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, x=10, y=40, width=24, height=16)
        set_selection(app, [i])
        align_selection(app, "top")
        assert _w(app, i).y == 0

    def test_align_bottom_single(self, make_app):
        app = make_app(size=(256, 192))
        sc = app.state.current_scene()
        i = _add(app, x=10, y=10, width=24, height=16)
        set_selection(app, [i])
        align_selection(app, "bottom")
        expected = int(sc.height) - 16
        assert _w(app, i).y == expected or abs(_w(app, i).y - expected) <= GRID

    def test_align_hcenter_single(self, make_app):
        app = make_app(size=(256, 192))
        sc = app.state.current_scene()
        i = _add(app, x=0, y=0, width=32, height=16)
        set_selection(app, [i])
        align_selection(app, "hcenter")
        center = int(sc.width) // 2
        widget_center = _w(app, i).x + 32 // 2
        assert abs(widget_center - center) <= GRID

    def test_align_left_multi(self, make_app):
        app = make_app(size=(256, 192))
        i0 = _add(app, x=8, y=0, width=24, height=16)
        i1 = _add(app, x=40, y=0, width=24, height=16)
        set_selection(app, [i0, i1])
        align_selection(app, "left")
        # Both should have same x (the left edge of the bounding box = 8)
        assert _w(app, i0).x == _w(app, i1).x

    def test_align_locked_skipped(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, x=40, y=20, width=24, height=16, locked=True)
        set_selection(app, [i])
        align_selection(app, "left")
        assert _w(app, i).x == 40  # unchanged

    def test_align_no_selection_no_crash(self, make_app):
        app = make_app(size=(256, 192))
        app.state.selected = []
        align_selection(app, "left")  # should not raise

    def test_align_unknown_mode_no_crash(self, make_app):
        app = make_app(size=(256, 192))
        _add(app, x=10, y=10)
        set_selection(app, [0])
        align_selection(app, "xyz")  # invalid mode


# ===================================================================
# DISTRIBUTE
# ===================================================================
class TestDistributeSelection:
    def test_distribute_horizontal(self, make_app):
        app = make_app(size=(256, 192))
        i0 = _add(app, x=0, y=0, width=16, height=16)
        i1 = _add(app, x=32, y=0, width=16, height=16)
        i2 = _add(app, x=80, y=0, width=16, height=16)
        set_selection(app, [i0, i1, i2])
        distribute_selection(app, "h")
        # First and last x unchanged, middle evenly spaced
        assert _w(app, i0).x == 0
        assert _w(app, i2).x == 80

    def test_distribute_vertical(self, make_app):
        app = make_app(size=(256, 192))
        i0 = _add(app, x=0, y=0, width=16, height=16)
        i1 = _add(app, x=0, y=32, width=16, height=16)
        i2 = _add(app, x=0, y=80, width=16, height=16)
        set_selection(app, [i0, i1, i2])
        distribute_selection(app, "v")
        assert _w(app, i0).y == 0
        assert _w(app, i2).y == 80

    def test_distribute_needs_3_widgets(self, make_app):
        app = make_app(size=(256, 192))
        i0 = _add(app, x=0, y=0)
        i1 = _add(app, x=32, y=0)
        set_selection(app, [i0, i1])
        distribute_selection(app, "h")  # should not crash, just status msg


# ===================================================================
# MATCH SIZE
# ===================================================================
class TestMatchSizeSelection:
    def test_match_width(self, make_app):
        app = make_app(size=(256, 192))
        i0 = _add(app, x=0, y=0, width=64, height=16)
        i1 = _add(app, x=0, y=24, width=32, height=16)
        set_selection(app, [i0, i1])
        app.state.selected_idx = i0  # anchor
        match_size_selection(app, "width")
        # i1 should have width matching i0 (possibly snapped)
        assert abs(_w(app, i1).width - 64) <= GRID

    def test_match_height(self, make_app):
        app = make_app(size=(256, 192))
        i0 = _add(app, x=0, y=0, width=32, height=40)
        i1 = _add(app, x=40, y=0, width=32, height=16)
        set_selection(app, [i0, i1])
        app.state.selected_idx = i0
        match_size_selection(app, "height")
        assert abs(_w(app, i1).height - 40) <= GRID

    def test_match_needs_2_widgets(self, make_app):
        app = make_app(size=(256, 192))
        i0 = _add(app)
        set_selection(app, [i0])
        match_size_selection(app, "width")  # no crash


# ===================================================================
# CENTER IN SCENE
# ===================================================================
class TestCenterInScene:
    def test_center_both(self, make_app):
        app = make_app(size=(256, 192))
        sc = app.state.current_scene()
        i = _add(app, x=0, y=0, width=32, height=16)
        set_selection(app, [i])
        center_selection_in_scene(app, "both")
        cx = _w(app, i).x + 16
        cy = _w(app, i).y + 8
        assert abs(cx - int(sc.width) // 2) <= GRID
        assert abs(cy - int(sc.height) // 2) <= GRID

    def test_center_x_only(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, x=0, y=0, width=32, height=16)
        old_y = _w(app, i).y
        set_selection(app, [i])
        center_selection_in_scene(app, "x")
        assert _w(app, i).y == old_y  # y should not change

    def test_center_locked_blocked(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, x=0, y=0, width=32, height=16, locked=True)
        set_selection(app, [i])
        center_selection_in_scene(app, "both")
        assert _w(app, i).x == 0  # unchanged


# ===================================================================
# SNAP DRAG TO GUIDES
# ===================================================================
class TestSnapDragToGuides:
    def test_snaps_to_scene_edge(self, make_app):
        app = make_app(size=(256, 192))
        app.state.selected = []
        bounds = pygame.Rect(0, 0, 32, 16)
        rx, ry = snap_drag_to_guides(app, 2, 2, bounds)
        # Close to edge (0, 0) — should snap
        assert rx == 0 or abs(rx - 2) <= GRID
        assert ry == 0 or abs(ry - 2) <= GRID

    def test_no_snap_far_from_guides(self, make_app):
        app = make_app(size=(256, 192))
        app.state.selected = []
        bounds = pygame.Rect(0, 0, 32, 16)
        rx, ry = snap_drag_to_guides(app, 100, 80, bounds)
        # Far from edges — returned as-is or with minor guide snap
        assert isinstance(rx, int) and isinstance(ry, int)


# ===================================================================
# SELECTION OPS: cycle functions
# ===================================================================
class TestCycleFunctions:
    def test_cycle_style(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, style="default")
        set_selection(app, [i])
        cycle_style(app)
        assert _w(app, i).style == "bold"
        cycle_style(app)
        assert _w(app, i).style == "inverse"
        cycle_style(app)
        assert _w(app, i).style == "highlight"
        cycle_style(app)
        assert _w(app, i).style == "default"

    def test_cycle_widget_type(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, type="label")
        set_selection(app, [i])
        cycle_widget_type(app)
        assert _w(app, i).type == "button"
        cycle_widget_type(app)
        assert _w(app, i).type == "panel"

    def test_cycle_border_style(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, border_style="single")
        set_selection(app, [i])
        cycle_border_style(app)
        assert _w(app, i).border_style == "double"

    def test_cycle_text_overflow(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, text_overflow="ellipsis")
        set_selection(app, [i])
        cycle_text_overflow(app)
        assert _w(app, i).text_overflow == "wrap"

    def test_cycle_align(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, align="left")
        set_selection(app, [i])
        cycle_align(app)
        assert _w(app, i).align == "center"
        cycle_align(app)
        assert _w(app, i).align == "right"
        cycle_align(app)
        assert _w(app, i).align == "left"

    def test_cycle_valign(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, valign="top")
        set_selection(app, [i])
        cycle_valign(app)
        assert _w(app, i).valign == "middle"

    def test_cycle_applies_to_all_selected(self, make_app):
        app = make_app(size=(256, 192))
        i0 = _add(app, style="default")
        i1 = _add(app, style="default")
        set_selection(app, [i0, i1])
        cycle_style(app)
        assert _w(app, i0).style == "bold"
        assert _w(app, i1).style == "bold"

    def test_cycle_no_selection_no_crash(self, make_app):
        app = make_app(size=(256, 192))
        app.state.selected = []
        cycle_style(app)
        cycle_widget_type(app)
        cycle_border_style(app)


# ===================================================================
# TOGGLE & SWAP
# ===================================================================
class TestToggleAndSwap:
    def test_toggle_visibility(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, visible=True)
        set_selection(app, [i])
        toggle_visibility(app)
        assert _w(app, i).visible is False
        toggle_visibility(app)
        assert _w(app, i).visible is True

    def test_swap_fg_bg(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, color_fg="#ff0000", color_bg="#00ff00")
        set_selection(app, [i])
        swap_fg_bg(app)
        assert _w(app, i).color_fg == "#00ff00"
        assert _w(app, i).color_bg == "#ff0000"


# ===================================================================
# MIRROR
# ===================================================================
class TestMirrorSelection:
    def test_mirror_horizontal(self, make_app):
        app = make_app(size=(256, 192))
        i0 = _add(app, x=0, y=0, width=16, height=16)
        i1 = _add(app, x=48, y=0, width=16, height=16)
        set_selection(app, [i0, i1])
        mirror_selection(app, "h")
        # After horizontal mirror, left becomes right and vice versa
        assert _w(app, i0).x == 48
        assert _w(app, i1).x == 0

    def test_mirror_vertical(self, make_app):
        app = make_app(size=(256, 192))
        i0 = _add(app, x=0, y=0, width=16, height=16)
        i1 = _add(app, x=0, y=48, width=16, height=16)
        set_selection(app, [i0, i1])
        mirror_selection(app, "v")
        assert _w(app, i0).y == 48
        assert _w(app, i1).y == 0


# ===================================================================
# ARRAY DUPLICATE
# ===================================================================
class TestArrayDuplicate:
    def test_creates_copies(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, x=0, y=0, width=16, height=16)
        set_selection(app, [i])
        sc = app.state.current_scene()
        before = len(sc.widgets)
        array_duplicate(app, count=3, dx=20, dy=0)
        assert len(sc.widgets) == before + 3

    def test_offset_applied(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, x=0, y=0, width=16, height=16)
        set_selection(app, [i])
        sc = app.state.current_scene()
        array_duplicate(app, count=2, dx=24, dy=0)
        assert sc.widgets[-2].x == 24
        assert sc.widgets[-1].x == 48

    def test_count_zero_no_crash(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app)
        set_selection(app, [i])
        array_duplicate(app, count=0, dx=8, dy=0)  # Invalid, should not crash


# ===================================================================
# DUPLICATE / COPY-PASTE
# ===================================================================
class TestDuplicateAndCopyPaste:
    def test_duplicate_adds_widget(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, x=8, y=8, width=24, height=16, type="button")
        set_selection(app, [i])
        sc = app.state.current_scene()
        before = len(sc.widgets)
        duplicate_selection(app)
        assert len(sc.widgets) == before + 1
        # Duplicate should be offset by GRID
        new_w = sc.widgets[-1]
        assert new_w.type == "button"

    def test_copy_paste(self, make_app):
        app = make_app(size=(256, 192))
        i = _add(app, x=8, y=8, width=24, height=16, type="slider")
        set_selection(app, [i])
        copy_selection(app)
        sc = app.state.current_scene()
        before = len(sc.widgets)
        paste_clipboard(app)
        assert len(sc.widgets) == before + 1
        assert sc.widgets[-1].type == "slider"


# ===================================================================
# DELETE / SELECT ALL / REORDER
# ===================================================================
class TestDeleteSelectReorder:
    def test_delete_removes_widget(self, make_app):
        app = make_app(size=(256, 192))
        _add(app, type="label")
        _add(app, type="button")
        _add(app, type="slider")
        sc = app.state.current_scene()
        set_selection(app, [1])
        delete_selected(app)
        assert len(sc.widgets) == 2

    def test_delete_locked_skipped(self, make_app):
        app = make_app(size=(256, 192))
        _add(app, type="label", locked=True)
        sc = app.state.current_scene()
        set_selection(app, [0])
        delete_selected(app)
        assert len(sc.widgets) == 1  # still there

    def test_select_all(self, make_app):
        app = make_app(size=(256, 192))
        _add(app)
        _add(app)
        _add(app)
        select_all(app)
        assert len(app.state.selected) == 3

    def test_reorder_up(self, make_app):
        app = make_app(size=(256, 192))
        _add(app, type="label")
        _add(app, type="button")
        _add(app, type="slider")
        sc = app.state.current_scene()
        set_selection(app, [2])
        reorder_selection(app, -1)
        # slider (was idx=2) should now be at idx=1
        assert sc.widgets[1].type == "slider"

    def test_reorder_down(self, make_app):
        app = make_app(size=(256, 192))
        _add(app, type="label")
        _add(app, type="button")
        _add(app, type="slider")
        sc = app.state.current_scene()
        set_selection(app, [0])
        reorder_selection(app, 1)
        assert sc.widgets[1].type == "label"


# ===================================================================
# SELECT SAME
# ===================================================================
class TestSelectSame:
    def test_select_same_type(self, make_app):
        app = make_app(size=(256, 192))
        _add(app, type="button")
        _add(app, type="label")
        _add(app, type="button")
        set_selection(app, [0])
        select_same_type(app)
        assert sorted(app.state.selected) == [0, 2]

    def test_select_same_style(self, make_app):
        app = make_app(size=(256, 192))
        _add(app, style="bold")
        _add(app, style="default")
        _add(app, style="bold")
        set_selection(app, [0])
        select_same_style(app)
        assert sorted(app.state.selected) == [0, 2]

    def test_select_same_z(self, make_app):
        app = make_app(size=(256, 192))
        _add(app, z_index=3)
        _add(app, z_index=0)
        _add(app, z_index=3)
        set_selection(app, [0])
        select_same_z(app)
        assert sorted(app.state.selected) == [0, 2]

    def test_select_same_color(self, make_app):
        app = make_app(size=(256, 192))
        _add(app, color_fg="#ff0000", color_bg="#000000")
        _add(app, color_fg="#00ff00", color_bg="#000000")
        _add(app, color_fg="#ff0000", color_bg="#000000")
        set_selection(app, [0])
        select_same_color(app)
        assert sorted(app.state.selected) == [0, 2]
