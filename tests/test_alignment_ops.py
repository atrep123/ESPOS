"""Tests for cyberpunk_designer.selection_ops.alignment module.

Covers all 15 alignment functions: snap_selection_to_grid, center_in_scene,
align_to_scene_top/bottom/left/right, center_horizontal/vertical,
center_in_parent, align_h/v_centers, align_left/top/right/bottom_edges.
"""

from __future__ import annotations

from cyberpunk_designer.constants import GRID
from cyberpunk_designer.selection_ops import (
    align_bottom_edges,
    align_h_centers,
    align_left_edges,
    align_right_edges,
    align_to_scene_bottom,
    align_to_scene_left,
    align_to_scene_right,
    align_to_scene_top,
    align_top_edges,
    align_v_centers,
    center_horizontal,
    center_in_parent,
    center_in_scene,
    center_vertical,
    snap_selection_to_grid,
)
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
    app = CyberpunkEditorApp(json_path, (256, 128))
    if not hasattr(app, "_save_undo_state"):
        app._save_undo_state = lambda: None
    return app


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
# snap_selection_to_grid
# ===========================================================================

class TestSnapSelectionToGrid:
    def test_snaps_misaligned_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=5, y=13)
        _sel(app, 0)
        snap_selection_to_grid(app)
        assert _w(app, 0).x == GRID  # 5 → 8
        assert _w(app, 0).y == 2 * GRID  # 13 → 16

    def test_already_aligned_no_change(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=16, y=24)
        _sel(app, 0)
        snap_selection_to_grid(app)
        assert _w(app, 0).x == 16
        assert _w(app, 0).y == 24

    def test_empty_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=5, y=5)
        _sel(app)
        snap_selection_to_grid(app)
        assert _w(app, 0).x == 5  # unchanged

    def test_multiple_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=3, y=7)
        _add(app, x=11, y=19)
        _sel(app, 0, 1)
        snap_selection_to_grid(app)
        assert _w(app, 0).x == 0  # 3 → 0
        assert _w(app, 0).y == 8  # 7 → 8
        assert _w(app, 1).x == 8  # 11 → 8
        assert _w(app, 1).y == 16  # 19 → 16

    def test_invalid_index_skipped(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=5, y=5)
        _sel(app, 0, 99)
        snap_selection_to_grid(app)  # no crash
        assert _w(app, 0).x == 8


# ===========================================================================
# center_in_scene
# ===========================================================================

class TestCenterInScene:
    def test_centers_single_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=80, height=16)
        _sel(app, 0)
        center_in_scene(app)
        w = _w(app, 0)
        # scene 256x128, widget 80x16
        assert w.x == (256 - 80) // 2
        assert w.y == (128 - 16) // 2

    def test_centers_widget_group(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=40, height=10)
        _add(app, x=40, y=10, width=40, height=10)
        _sel(app, 0, 1)
        center_in_scene(app)
        # group bounding box: 0,0 to 80,20 → 80x20
        # dx = (256 - 80)//2 - 0 = 88
        # dy = (128 - 20)//2 - 0 = 54
        assert _w(app, 0).x == 88
        assert _w(app, 0).y == 54
        assert _w(app, 1).x == 128
        assert _w(app, 1).y == 64

    def test_empty_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10)
        _sel(app)
        center_in_scene(app)
        assert _w(app, 0).x == 10  # unchanged


# ===========================================================================
# align_to_scene_top
# ===========================================================================

class TestAlignToSceneTop:
    def test_moves_to_y_zero(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=50)
        _sel(app, 0)
        align_to_scene_top(app)
        assert _w(app, 0).y == 0
        assert _w(app, 0).x == 10  # x unchanged

    def test_multiple_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=20)
        _add(app, y=40)
        _sel(app, 0, 1)
        align_to_scene_top(app)
        assert _w(app, 0).y == 0
        assert _w(app, 1).y == 0

    def test_empty_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=30)
        _sel(app)
        align_to_scene_top(app)
        assert _w(app, 0).y == 30


# ===========================================================================
# align_to_scene_bottom
# ===========================================================================

class TestAlignToSceneBottom:
    def test_moves_bottom_edge_to_128(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=10, height=20)
        _sel(app, 0)
        align_to_scene_bottom(app)
        assert _w(app, 0).y == 128 - 20

    def test_multiple_different_heights(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=0, height=16)
        _add(app, y=0, height=24)
        _sel(app, 0, 1)
        align_to_scene_bottom(app)
        assert _w(app, 0).y == 128 - 16
        assert _w(app, 1).y == 128 - 24

    def test_empty_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=10, height=20)
        _sel(app)
        align_to_scene_bottom(app)
        assert _w(app, 0).y == 10


# ===========================================================================
# align_to_scene_left
# ===========================================================================

class TestAlignToSceneLeft:
    def test_moves_to_x_zero(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=50, y=10)
        _sel(app, 0)
        align_to_scene_left(app)
        assert _w(app, 0).x == 0
        assert _w(app, 0).y == 10

    def test_empty_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=50)
        _sel(app)
        align_to_scene_left(app)
        assert _w(app, 0).x == 50


# ===========================================================================
# align_to_scene_right
# ===========================================================================

class TestAlignToSceneRight:
    def test_moves_right_edge_to_256(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, width=60)
        _sel(app, 0)
        align_to_scene_right(app)
        assert _w(app, 0).x == 256 - 60

    def test_multiple_different_widths(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, width=40)
        _add(app, x=0, width=80)
        _sel(app, 0, 1)
        align_to_scene_right(app)
        assert _w(app, 0).x == 256 - 40
        assert _w(app, 1).x == 256 - 80

    def test_empty_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, width=60)
        _sel(app)
        align_to_scene_right(app)
        assert _w(app, 0).x == 10


# ===========================================================================
# center_horizontal
# ===========================================================================

class TestCenterHorizontal:
    def test_centers_each_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=10, width=80)
        _add(app, x=0, y=30, width=40)
        _sel(app, 0, 1)
        center_horizontal(app)
        assert _w(app, 0).x == (256 - 80) // 2
        assert _w(app, 1).x == (256 - 40) // 2
        # y unchanged
        assert _w(app, 0).y == 10
        assert _w(app, 1).y == 30

    def test_empty_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, width=80)
        _sel(app)
        center_horizontal(app)
        assert _w(app, 0).x == 10


# ===========================================================================
# center_vertical
# ===========================================================================

class TestCenterVertical:
    def test_centers_each_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=0, height=16)
        _add(app, x=20, y=0, height=32)
        _sel(app, 0, 1)
        center_vertical(app)
        assert _w(app, 0).y == (128 - 16) // 2
        assert _w(app, 1).y == (128 - 32) // 2
        # x unchanged
        assert _w(app, 0).x == 10
        assert _w(app, 1).x == 20

    def test_empty_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=10, height=16)
        _sel(app)
        center_vertical(app)
        assert _w(app, 0).y == 10


# ===========================================================================
# center_in_parent
# ===========================================================================

class TestCenterInParent:
    def test_centers_in_enclosing_panel(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Panel at (0,0) size 100x60
        _add(app, type="panel", x=0, y=0, width=100, height=60)
        # Child label at (5,5) size 20x10 — inside the panel
        _add(app, type="label", x=5, y=5, width=20, height=10)
        _sel(app, 1)
        center_in_parent(app)
        w = _w(app, 1)
        # Center of 100x60 panel for 20x10 child:
        # x = snap(0 + (100 - 20) // 2) = snap(40) = 40
        # y = snap(0 + (60 - 10) // 2) = snap(25) = 24 (snap to 8)
        from cyberpunk_designer.constants import snap
        expected_x = snap(0 + (100 - 20) // 2)
        expected_y = snap(0 + (60 - 10) // 2)
        assert w.x == expected_x
        assert w.y == expected_y

    def test_no_enclosing_panel(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label", x=10, y=10, width=20, height=10)
        _sel(app, 0)
        center_in_parent(app)
        # No panel → no change
        assert _w(app, 0).x == 10
        assert _w(app, 0).y == 10

    def test_picks_smallest_enclosing_panel(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Large panel
        _add(app, type="panel", x=0, y=0, width=200, height=100)
        # Small panel (inside large)
        _add(app, type="panel", x=10, y=10, width=60, height=40)
        # Child inside small panel
        _add(app, type="label", x=15, y=15, width=10, height=8)
        _sel(app, 2)
        center_in_parent(app)
        # Should center in the small panel (10,10,60,40)
        from cyberpunk_designer.constants import snap
        expected_x = snap(10 + (60 - 10) // 2)
        expected_y = snap(10 + (40 - 8) // 2)
        assert _w(app, 2).x == expected_x
        assert _w(app, 2).y == expected_y

    def test_empty_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="panel", x=0, y=0, width=100, height=60)
        _sel(app)
        center_in_parent(app)  # no crash


# ===========================================================================
# align_h_centers
# ===========================================================================

class TestAlignHCenters:
    def test_aligns_to_first_center(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, width=80)   # center = 50
        _add(app, x=0, width=40)    # center = 20 → should become 30
        _sel(app, 0, 1)
        align_h_centers(app)
        from cyberpunk_designer.constants import snap
        ref_cx = 10 + 80 // 2  # 50
        expected_x = snap(ref_cx - 40 // 2)  # snap(30) = 32
        assert _w(app, 1).x == expected_x
        # First widget unchanged
        assert _w(app, 0).x == 10

    def test_less_than_two_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, width=80)
        _sel(app, 0)
        align_h_centers(app)  # not enough selection
        assert _w(app, 0).x == 10

    def test_three_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, width=80)   # ref center 50
        _add(app, x=0, width=20)
        _add(app, x=100, width=60)
        _sel(app, 0, 1, 2)
        align_h_centers(app)
        from cyberpunk_designer.constants import snap
        ref_cx = 50
        assert _w(app, 1).x == snap(ref_cx - 20 // 2)
        assert _w(app, 2).x == snap(ref_cx - 60 // 2)


# ===========================================================================
# align_v_centers
# ===========================================================================

class TestAlignVCenters:
    def test_aligns_to_first_center(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=20, height=40)   # center = 40
        _add(app, y=0, height=16)    # should align to center 40
        _sel(app, 0, 1)
        align_v_centers(app)
        from cyberpunk_designer.constants import snap
        ref_cy = 20 + 40 // 2  # 40
        expected_y = snap(ref_cy - 16 // 2)  # snap(32) = 32
        assert _w(app, 1).y == expected_y
        assert _w(app, 0).y == 20  # unchanged

    def test_less_than_two_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=20, height=40)
        _sel(app, 0)
        align_v_centers(app)
        assert _w(app, 0).y == 20


# ===========================================================================
# align_left_edges
# ===========================================================================

class TestAlignLeftEdges:
    def test_aligns_to_first_x(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=30)
        _add(app, x=50)
        _add(app, x=10)
        _sel(app, 0, 1, 2)
        align_left_edges(app)
        assert _w(app, 1).x == 30
        assert _w(app, 2).x == 30
        assert _w(app, 0).x == 30  # first stays

    def test_less_than_two_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=30)
        _sel(app, 0)
        align_left_edges(app)
        assert _w(app, 0).x == 30


# ===========================================================================
# align_top_edges
# ===========================================================================

class TestAlignTopEdges:
    def test_aligns_to_first_y(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=20)
        _add(app, y=50)
        _add(app, y=5)
        _sel(app, 0, 1, 2)
        align_top_edges(app)
        assert _w(app, 1).y == 20
        assert _w(app, 2).y == 20

    def test_less_than_two_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=20)
        _sel(app, 0)
        align_top_edges(app)
        assert _w(app, 0).y == 20


# ===========================================================================
# align_right_edges
# ===========================================================================

class TestAlignRightEdges:
    def test_aligns_right_edge_to_first(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=20, width=80)   # right = 100
        _add(app, x=50, width=40)   # right = 90 → x should become 60
        _sel(app, 0, 1)
        align_right_edges(app)
        ref_right = 20 + 80  # 100
        assert _w(app, 1).x == ref_right - 40  # 60
        assert _w(app, 0).x == 20  # unchanged

    def test_three_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, width=90)   # right = 100
        _add(app, x=0, width=30)    # → x = 70
        _add(app, x=0, width=50)    # → x = 50
        _sel(app, 0, 1, 2)
        align_right_edges(app)
        assert _w(app, 1).x == 70
        assert _w(app, 2).x == 50

    def test_less_than_two_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=20, width=80)
        _sel(app, 0)
        align_right_edges(app)
        assert _w(app, 0).x == 20


# ===========================================================================
# align_bottom_edges
# ===========================================================================

class TestAlignBottomEdges:
    def test_aligns_bottom_edge_to_first(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=10, height=40)   # bottom = 50
        _add(app, y=20, height=16)   # bottom = 36 → y should become 34
        _sel(app, 0, 1)
        align_bottom_edges(app)
        ref_bottom = 10 + 40  # 50
        assert _w(app, 1).y == ref_bottom - 16  # 34
        assert _w(app, 0).y == 10  # unchanged

    def test_less_than_two_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=10, height=40)
        _sel(app, 0)
        align_bottom_edges(app)
        assert _w(app, 0).y == 10
