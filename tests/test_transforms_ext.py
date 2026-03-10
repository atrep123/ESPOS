"""Extended tests for cyberpunk_designer/selection_ops/transforms.py.

Covers uncovered functions: mirror_scene_horizontal, mirror_scene_vertical,
move_to_origin, make_square, scale_up, scale_down, and guard branches
(locked widgets, snap behavior, empty selection, etc.) in existing functions.
"""

from __future__ import annotations

from cyberpunk_designer.selection_ops.transforms import (
    flip_horizontal,
    flip_vertical,
    make_full_height,
    make_full_width,
    make_square,
    mirror_scene_horizontal,
    mirror_scene_vertical,
    mirror_selection,
    move_selection,
    move_selection_to_origin,
    move_to_origin,
    resize_selection_to,
    scale_down,
    scale_up,
    swap_content,
    swap_dimensions,
    swap_fg_bg,
    swap_positions,
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
    app.snap_enabled = False
    return app


def _add(app, **kw):
    defaults = dict(type="label", x=0, y=0, width=20, height=10, text="W")
    defaults.update(kw)
    w = WidgetConfig(**defaults)
    sc = app.state.current_scene()
    sc.widgets.append(w)
    return w


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None
    if indices:
        app.designer.selected_widget = indices[0]


# ===========================================================================
# mirror_scene_horizontal
# ===========================================================================


class TestMirrorSceneHorizontal:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=0, width=20, height=10)
        sc = app.state.current_scene()
        mirror_scene_horizontal(app)
        assert sc.widgets[0].x == 256 - 10 - 20  # sw - x - w

    def test_multiple_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=20, height=10)
        _add(app, x=100, y=0, width=30, height=10)
        sc = app.state.current_scene()
        mirror_scene_horizontal(app)
        assert sc.widgets[0].x == 256 - 0 - 20
        assert sc.widgets[1].x == 256 - 100 - 30

    def test_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        mirror_scene_horizontal(app)  # no crash


# ===========================================================================
# mirror_scene_vertical
# ===========================================================================


class TestMirrorSceneVertical:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=10, width=20, height=10)
        sc = app.state.current_scene()
        mirror_scene_vertical(app)
        assert sc.widgets[0].y == 128 - 10 - 10  # sh - y - h

    def test_multiple_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=20, height=10)
        _add(app, x=0, y=50, width=20, height=20)
        sc = app.state.current_scene()
        mirror_scene_vertical(app)
        assert sc.widgets[0].y == 128 - 0 - 10
        assert sc.widgets[1].y == 128 - 50 - 20

    def test_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        mirror_scene_vertical(app)  # no crash


# ===========================================================================
# move_to_origin
# ===========================================================================


class TestMoveToOrigin:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=20, y=30, width=10, height=10)
        _sel(app, 0)
        move_to_origin(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].x == 0
        assert sc.widgets[0].y == 0

    def test_multiple_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=20, y=30, width=10, height=10)
        _add(app, x=40, y=50, width=10, height=10)
        _sel(app, 0, 1)
        move_to_origin(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].x == 0
        assert sc.widgets[0].y == 0
        assert sc.widgets[1].x == 20  # offset preserved
        assert sc.widgets[1].y == 20

    def test_already_at_origin(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=10, height=10)
        _sel(app, 0)
        move_to_origin(app)  # noop — status says "Already at origin."
        sc = app.state.current_scene()
        assert sc.widgets[0].x == 0
        assert sc.widgets[0].y == 0

    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=20, y=30)
        _sel(app)
        move_to_origin(app)  # no crash


# ===========================================================================
# make_square
# ===========================================================================


class TestMakeSquare:
    def test_wider_than_tall(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=20)
        _sel(app, 0)
        make_square(app)
        w = app.state.current_scene().widgets[0]
        assert w.width == 40
        assert w.height == 40

    def test_taller_than_wide(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=10, height=30)
        _sel(app, 0)
        make_square(app)
        w = app.state.current_scene().widgets[0]
        assert w.width == 30
        assert w.height == 30

    def test_already_square(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=20, height=20)
        _sel(app, 0)
        make_square(app)
        w = app.state.current_scene().widgets[0]
        assert w.width == 20
        assert w.height == 20

    def test_multiple_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=10)
        _add(app, width=8, height=24)
        _sel(app, 0, 1)
        make_square(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width == 40 and sc.widgets[0].height == 40
        assert sc.widgets[1].width == 24 and sc.widgets[1].height == 24

    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=10)
        _sel(app)
        make_square(app)  # no crash

    def test_invalid_index(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=10)
        app.state.selected = [99]
        make_square(app)  # invalid index — skipped


# ===========================================================================
# scale_up
# ===========================================================================


class TestScaleUp:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=20, height=10)
        _sel(app, 0)
        scale_up(app)
        w = app.state.current_scene().widgets[0]
        assert w.width == 40
        assert w.height == 20

    def test_multiple_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=10, height=8)
        _add(app, width=20, height=16)
        _sel(app, 0, 1)
        scale_up(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width == 20 and sc.widgets[0].height == 16
        assert sc.widgets[1].width == 40 and sc.widgets[1].height == 32

    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=20, height=10)
        _sel(app)
        scale_up(app)  # no crash

    def test_invalid_index(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=20, height=10)
        app.state.selected = [99]
        scale_up(app)  # skipped


# ===========================================================================
# scale_down
# ===========================================================================


class TestScaleDown:
    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=48, height=32)
        _sel(app, 0)
        scale_down(app)
        w = app.state.current_scene().widgets[0]
        # snap(48//2) = snap(24) = 24, snap(32//2) = snap(16) = 16 (GRID=8)
        assert w.width == 24
        assert w.height == 16

    def test_minimum_size(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=4, height=4)  # GRID minimum
        _sel(app, 0)
        scale_down(app)
        w = app.state.current_scene().widgets[0]
        assert w.width >= 4  # can't go below GRID
        assert w.height >= 4

    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=20)
        _sel(app)
        scale_down(app)  # no crash

    def test_invalid_index(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=20)
        app.state.selected = [99]
        scale_down(app)  # skipped


# ===========================================================================
# move_selection — guard branches
# ===========================================================================


class TestMoveSelectionGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10)
        _sel(app)
        move_selection(app, 5, 5)  # no crash, no change
        assert app.state.current_scene().widgets[0].x == 10

    def test_locked_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10, locked=True)
        _sel(app, 0)
        move_selection(app, 5, 5)
        # locked widget — no movement
        assert app.state.current_scene().widgets[0].x == 10

    def test_snap_enabled(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.snap_enabled = True
        _add(app, x=0, y=0, width=20, height=10)
        _sel(app, 0)
        move_selection(app, 5, 5)
        w = app.state.current_scene().widgets[0]
        # snapped to grid — should be multiple of 4
        assert w.x % 4 == 0
        assert w.y % 4 == 0

    def test_clamp_to_scene_bounds(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=240, y=120, width=20, height=10)
        _sel(app, 0)
        move_selection(app, 100, 100)
        w = app.state.current_scene().widgets[0]
        sc = app.state.current_scene()
        assert w.x + w.width <= sc.width
        assert w.y + w.height <= sc.height

    def test_zero_movement(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=20, height=10)
        _sel(app, 0)
        move_selection(app, 0, 0)
        assert app.state.current_scene().widgets[0].x == 0


# ===========================================================================
# resize_selection_to — guard branches
# ===========================================================================


class TestResizeSelectionGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=20, height=10)
        _sel(app)
        assert resize_selection_to(app, 40, 20) is False

    def test_locked_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=20, height=10, locked=True)
        _sel(app, 0)
        assert resize_selection_to(app, 40, 20) is False

    def test_snap_enabled(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.snap_enabled = True
        _add(app, x=0, y=0, width=20, height=10)
        _sel(app, 0)
        assert resize_selection_to(app, 42, 18) is True
        w = app.state.current_scene().widgets[0]
        assert w.width % 4 == 0
        assert w.height % 4 == 0

    def test_multiple_widgets_scale(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=20, height=10)
        _add(app, x=20, y=0, width=20, height=10)
        _sel(app, 0, 1)
        assert resize_selection_to(app, 80, 20) is True

    def test_clamp_to_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=200, y=100, width=20, height=10)
        _sel(app, 0)
        assert resize_selection_to(app, 1000, 1000) is True
        w = app.state.current_scene().widgets[0]
        sc = app.state.current_scene()
        assert w.width <= sc.width


# ===========================================================================
# mirror_selection — guard branches
# ===========================================================================


class TestMirrorSelectionGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10)
        _sel(app)
        mirror_selection(app, "h")  # no crash

    def test_horizontal(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=20, height=10)
        _add(app, x=40, y=0, width=20, height=10)
        _sel(app, 0, 1)
        mirror_selection(app, "h")
        sc = app.state.current_scene()
        # positions should be swapped
        assert sc.widgets[0].x == 40
        assert sc.widgets[1].x == 0

    def test_vertical(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=20, height=10)
        _add(app, x=0, y=40, width=20, height=10)
        _sel(app, 0, 1)
        mirror_selection(app, "v")
        sc = app.state.current_scene()
        assert sc.widgets[0].y == 40
        assert sc.widgets[1].y == 0


# ===========================================================================
# swap_fg_bg — guard branches
# ===========================================================================


class TestSwapFgBgGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="white", color_bg="black")
        _sel(app)
        swap_fg_bg(app)  # no crash
        assert app.state.current_scene().widgets[0].color_fg == "white"

    def test_basic_swap(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="white", color_bg="black")
        _sel(app, 0)
        swap_fg_bg(app)
        w = app.state.current_scene().widgets[0]
        assert w.color_fg == "black"
        assert w.color_bg == "white"


# ===========================================================================
# make_full_width — guard branches
# ===========================================================================


class TestMakeFullWidthGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        make_full_width(app)  # no crash

    def test_locked_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, width=20, locked=True)
        _sel(app, 0)
        make_full_width(app)
        assert app.state.current_scene().widgets[0].x == 10  # unchanged

    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, width=20)
        _sel(app, 0)
        make_full_width(app)
        w = app.state.current_scene().widgets[0]
        assert w.x == 0
        assert w.width == 256


# ===========================================================================
# make_full_height — guard branches
# ===========================================================================


class TestMakeFullHeightGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        make_full_height(app)  # no crash

    def test_locked_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=10, height=20, locked=True)
        _sel(app, 0)
        make_full_height(app)
        assert app.state.current_scene().widgets[0].y == 10  # unchanged

    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=10, height=20)
        _sel(app, 0)
        make_full_height(app)
        w = app.state.current_scene().widgets[0]
        assert w.y == 0
        assert w.height == 128


# ===========================================================================
# swap_dimensions — guard branches
# ===========================================================================


class TestSwapDimensionsGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=20)
        _sel(app)
        swap_dimensions(app)  # no crash
        assert app.state.current_scene().widgets[0].width == 40

    def test_locked_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=20, locked=True)
        _sel(app, 0)
        swap_dimensions(app)
        assert app.state.current_scene().widgets[0].width == 40  # unchanged


# ===========================================================================
# move_selection_to_origin — guard branches
# ===========================================================================


class TestMoveSelectionToOriginGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=20, y=30)
        _sel(app)
        move_selection_to_origin(app)  # no crash
        assert app.state.current_scene().widgets[0].x == 20

    def test_basic(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=20, y=30, width=10, height=10)
        _sel(app, 0)
        move_selection_to_origin(app)
        w = app.state.current_scene().widgets[0]
        assert w.x == 0
        assert w.y == 0


# ===========================================================================
# swap_positions — guard branches
# ===========================================================================


class TestSwapPositionsGuards:
    def test_not_two_selected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=20)
        _sel(app, 0)
        swap_positions(app)  # needs exactly 2

    def test_basic_swap(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=20)
        _add(app, x=50, y=60)
        _sel(app, 0, 1)
        swap_positions(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].x == 50 and sc.widgets[0].y == 60
        assert sc.widgets[1].x == 10 and sc.widgets[1].y == 20

    def test_invalid_indices(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        app.state.selected = [0, 99]
        swap_positions(app)  # invalid index — no crash


# ===========================================================================
# flip_vertical — guard branches
# ===========================================================================


class TestFlipVerticalGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=10, height=20)
        _sel(app)
        flip_vertical(app)  # no crash

    def test_basic_flip(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=10, height=10)
        _add(app, x=0, y=40, width=10, height=10)
        _sel(app, 0, 1)
        flip_vertical(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].y == 40
        assert sc.widgets[1].y == 0


# ===========================================================================
# swap_content — guard branches
# ===========================================================================


class TestSwapContentGuards:
    def test_not_two_selected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="A")
        _sel(app, 0)
        swap_content(app)  # needs exactly 2

    def test_basic_swap(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="A", value=10)
        _add(app, text="B", value=20)
        _sel(app, 0, 1)
        swap_content(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].text == "B"
        assert sc.widgets[1].text == "A"
        assert sc.widgets[0].value == 20
        assert sc.widgets[1].value == 10

    def test_invalid_indices(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        app.state.selected = [0, 99]
        swap_content(app)  # no crash


# ===========================================================================
# flip_horizontal — guard branches
# ===========================================================================


class TestFlipHorizontalGuards:
    def test_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, width=20)
        _sel(app)
        flip_horizontal(app)  # no crash

    def test_basic_flip(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=10, height=10)
        _add(app, x=40, y=0, width=10, height=10)
        _sel(app, 0, 1)
        flip_horizontal(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].x == 40
        assert sc.widgets[1].x == 0
