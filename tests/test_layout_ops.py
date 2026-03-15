"""Tests for cyberpunk_designer.selection_ops.layout module — untested functions.

Covers: auto_flow_layout, space_evenly_h, space_evenly_v, shrink_to_content,
distribute_columns, distribute_rows, pack_left, pack_top, cascade_arrange,
distribute_columns_3.
"""

from __future__ import annotations

from cyberpunk_designer.constants import GRID
from cyberpunk_designer.selection_ops import (
    auto_flow_layout,
    cascade_arrange,
    distribute_columns,
    distribute_columns_3,
    distribute_rows,
    pack_left,
    pack_top,
    shrink_to_content,
    space_evenly_h,
    space_evenly_v,
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


def _w(app, idx):
    return app.state.current_scene().widgets[idx]


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None


# ===========================================================================
# auto_flow_layout
# ===========================================================================


class TestAutoFlowLayout:
    def test_wraps_widgets(self, make_app):
        app = make_app()
        # 4 widgets of 80px wide in 256px scene → row can fit 3
        for _ in range(4):
            _add(app, x=0, y=0, width=80, height=16)
        _sel(app, 0, 1, 2, 3)
        auto_flow_layout(app)
        # First 3 should be in row 1, 4th should wrap
        assert _w(app, 3).y > _w(app, 0).y

    def test_preserves_order(self, make_app):
        app = make_app()
        _add(app, width=80, height=16)
        _add(app, width=80, height=16)
        _sel(app, 0, 1)
        auto_flow_layout(app)
        # Widget 0 should be to the left of widget 1
        assert _w(app, 0).x < _w(app, 1).x

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, x=50, y=50, width=80, height=16)
        _sel(app, 0)
        auto_flow_layout(app)
        assert _w(app, 0).x == 50  # unchanged

    def test_snaps_to_grid(self, make_app):
        app = make_app()
        _add(app, width=80, height=16)
        _add(app, width=80, height=16)
        _sel(app, 0, 1)
        auto_flow_layout(app)
        # Positions should be grid-snapped
        assert _w(app, 0).x % GRID == 0
        assert _w(app, 0).y % GRID == 0


# ===========================================================================
# space_evenly_h
# ===========================================================================


class TestSpaceEvenlyH:
    def test_spaces_three_widgets(self, make_app):
        app = make_app()
        _add(app, x=0, width=20, height=16)  # center = 10
        _add(app, x=50, width=20, height=16)  # center = 60
        _add(app, x=200, width=20, height=16)  # center = 210
        _sel(app, 0, 1, 2)
        space_evenly_h(app)
        # First and last centers are preserved; middle is spaced evenly
        # center0=10, center2=210, step=100
        # middle should center at 110 → x = snap(110 - 10) = snap(100) = 100
        from cyberpunk_designer.constants import snap

        expected_mid_x = snap(110 - 10)
        assert _w(app, 1).x == expected_mid_x

    def test_less_than_three_noop(self, make_app):
        app = make_app()
        _add(app, x=0, width=20)
        _add(app, x=100, width=20)
        _sel(app, 0, 1)
        space_evenly_h(app)
        assert _w(app, 0).x == 0  # unchanged

    def test_single_widget_noop(self, make_app):
        app = make_app()
        _add(app, x=10, width=20)
        _sel(app, 0)
        space_evenly_h(app)
        assert _w(app, 0).x == 10


# ===========================================================================
# space_evenly_v
# ===========================================================================


class TestSpaceEvenlyV:
    def test_spaces_three_widgets(self, make_app):
        app = make_app()
        _add(app, y=0, height=16)  # center = 8
        _add(app, y=30, height=16)  # center = 38
        _add(app, y=100, height=16)  # center = 108
        _sel(app, 0, 1, 2)
        space_evenly_v(app)
        # First center=8, last center=108, step=50
        # middle: snap(58 - 8) = snap(50) = 48
        from cyberpunk_designer.constants import snap

        expected_mid_y = snap(58 - 8)
        assert _w(app, 1).y == expected_mid_y

    def test_less_than_three_noop(self, make_app):
        app = make_app()
        _add(app, y=0, height=16)
        _add(app, y=100, height=16)
        _sel(app, 0, 1)
        space_evenly_v(app)
        assert _w(app, 0).y == 0


# ===========================================================================
# shrink_to_content
# ===========================================================================


class TestShrinkToContent:
    def test_shrinks_panel_to_children(self, make_app):
        app = make_app()
        _add(app, type="panel", x=0, y=0, width=200, height=100)
        _add(app, type="label", x=20, y=20, width=40, height=10)
        _add(app, type="label", x=80, y=30, width=30, height=10)
        _sel(app, 0)
        shrink_to_content(app)
        panel = _w(app, 0)
        pad = GRID // 2
        # Children: (20,20,40,10) and (80,30,30,10)
        # min_x=20, min_y=20, max_x=110, max_y=40
        assert panel.x == 20 - pad
        assert panel.y == 20 - pad
        assert panel.width == (110 - 20) + pad * 2
        assert panel.height == (40 - 20) + pad * 2

    def test_non_panel_ignored(self, make_app):
        app = make_app()
        _add(app, type="label", x=0, y=0, width=200, height=100)
        _add(app, type="label", x=20, y=20, width=40, height=10)
        _sel(app, 0)
        shrink_to_content(app)
        # Label is not a panel → no shrink
        assert _w(app, 0).width == 200

    def test_panel_with_no_children(self, make_app):
        app = make_app()
        _add(app, type="panel", x=0, y=0, width=200, height=100)
        _sel(app, 0)
        shrink_to_content(app)
        # No children inside → no shrink
        assert _w(app, 0).width == 200

    def test_empty_selection(self, make_app):
        app = make_app()
        _add(app, type="panel", x=0, y=0, width=200, height=100)
        _sel(app)
        shrink_to_content(app)  # no crash


# ===========================================================================
# distribute_columns
# ===========================================================================


class TestDistributeColumns:
    def test_distributes_into_two_columns(self, make_app):
        app = make_app()
        _add(app, x=10, y=10, width=40, height=16)
        _add(app, x=20, y=20, width=40, height=16)
        _add(app, x=30, y=30, width=40, height=16)
        _add(app, x=40, y=40, width=40, height=16)
        _sel(app, 0, 1, 2, 3)
        distribute_columns(app, col_count=2)
        # Widgets are arranged in 2 columns
        # Col 0: widgets 0, 2; Col 1: widgets 1, 3
        assert _w(app, 0).x == _w(app, 2).x
        assert _w(app, 1).x == _w(app, 3).x
        assert _w(app, 0).x != _w(app, 1).x

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, x=10, width=40)
        _sel(app, 0)
        distribute_columns(app)
        assert _w(app, 0).x == 10

    def test_sets_uniform_width(self, make_app):
        app = make_app()
        _add(app, x=0, y=0, width=30, height=16)
        _add(app, x=50, y=0, width=60, height=16)
        _sel(app, 0, 1)
        distribute_columns(app, col_count=2)
        # All widgets should have same column width
        assert _w(app, 0).width == _w(app, 1).width


# ===========================================================================
# distribute_rows
# ===========================================================================


class TestDistributeRows:
    def test_distributes_into_two_rows(self, make_app):
        app = make_app()
        _add(app, x=10, y=10, width=40, height=16)
        _add(app, x=20, y=20, width=40, height=16)
        _add(app, x=30, y=30, width=40, height=16)
        _add(app, x=40, y=40, width=40, height=16)
        _sel(app, 0, 1, 2, 3)
        distribute_rows(app, row_count=2)
        # Widgets arranged in 2 rows
        # All widgets get uniform height
        assert _w(app, 0).height == _w(app, 1).height

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, y=10, height=16)
        _sel(app, 0)
        distribute_rows(app)
        assert _w(app, 0).y == 10


# ===========================================================================
# pack_left
# ===========================================================================


class TestPackLeft:
    def test_packs_touching_edges(self, make_app):
        app = make_app()
        _add(app, x=10, width=30, height=16)
        _add(app, x=80, width=40, height=16)
        _add(app, x=200, width=20, height=16)
        _sel(app, 0, 1, 2)
        pack_left(app)
        assert _w(app, 0).x == 10
        assert _w(app, 1).x == 10 + 30  # 40
        assert _w(app, 2).x == 10 + 30 + 40  # 80

    def test_preserves_y(self, make_app):
        app = make_app()
        _add(app, x=10, y=20, width=30, height=16)
        _add(app, x=80, y=50, width=40, height=16)
        _sel(app, 0, 1)
        pack_left(app)
        assert _w(app, 0).y == 20
        assert _w(app, 1).y == 50

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, x=10, width=30)
        _sel(app, 0)
        pack_left(app)
        assert _w(app, 0).x == 10


# ===========================================================================
# pack_top
# ===========================================================================


class TestPackTop:
    def test_packs_touching_edges(self, make_app):
        app = make_app()
        _add(app, y=10, height=20)
        _add(app, y=80, height=30)
        _add(app, y=200, height=16)
        _sel(app, 0, 1, 2)
        pack_top(app)
        assert _w(app, 0).y == 10
        assert _w(app, 1).y == 10 + 20  # 30
        assert _w(app, 2).y == 10 + 20 + 30  # 60

    def test_preserves_x(self, make_app):
        app = make_app()
        _add(app, x=10, y=10, height=20)
        _add(app, x=50, y=80, height=30)
        _sel(app, 0, 1)
        pack_top(app)
        assert _w(app, 0).x == 10
        assert _w(app, 1).x == 50

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, y=10, height=20)
        _sel(app, 0)
        pack_top(app)
        assert _w(app, 0).y == 10


# ===========================================================================
# cascade_arrange
# ===========================================================================


class TestCascadeArrange:
    def test_diagonal_pattern(self, make_app):
        app = make_app()
        _add(app, x=10, y=10, width=40, height=16)
        _add(app, x=100, y=100, width=40, height=16)
        _add(app, x=200, y=50, width=40, height=16)
        _sel(app, 0, 1, 2)
        cascade_arrange(app)
        # Should cascade from (10,10) with step=GRID
        assert _w(app, 0).x == 10 and _w(app, 0).y == 10
        assert _w(app, 1).x == 10 + GRID and _w(app, 1).y == 10 + GRID
        assert _w(app, 2).x == 10 + 2 * GRID and _w(app, 2).y == 10 + 2 * GRID

    def test_less_than_two_noop(self, make_app):
        app = make_app()
        _add(app, x=10, y=10)
        _sel(app, 0)
        cascade_arrange(app)
        assert _w(app, 0).x == 10


# ===========================================================================
# distribute_columns_3
# ===========================================================================


class TestDistributeColumns3:
    def test_three_columns(self, make_app):
        app = make_app()
        for i in range(6):
            _add(app, x=i * 10, y=i * 10, width=30, height=16)
        _sel(app, 0, 1, 2, 3, 4, 5)
        distribute_columns_3(app)
        # Should be in 3 columns, 2 rows
        # Widgets in same column have same x
        assert _w(app, 0).x == _w(app, 3).x
        assert _w(app, 1).x == _w(app, 4).x
        assert _w(app, 2).x == _w(app, 5).x
