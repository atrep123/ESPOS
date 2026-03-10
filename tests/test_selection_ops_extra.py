"""Tests for remaining selection_ops functions not covered by
test_selection_ops_advanced.py or test_layout_selection.py.

Covers: transforms, clones, text utils, queries, visibility,
grayscale cycling, flipping, clearing, and scene naming.
"""

from __future__ import annotations

from cyberpunk_designer.constants import GRID
from cyberpunk_designer.selection_ops import (
    auto_name_scene,
    auto_rename,
    clear_margins,
    clear_padding,
    clone_text,
    cycle_gray_bg,
    cycle_gray_fg,
    duplicate_below,
    duplicate_right,
    enable_all_widgets,
    equalize_heights,
    equalize_widths,
    flip_horizontal,
    flip_vertical,
    hide_unselected,
    increment_text,
    move_selection_to_origin,
    normalize_sizes,
    outline_mode,
    quick_clone,
    select_all_panels,
    select_bordered,
    select_children,
    select_parent_panel,
    select_same_size,
    show_all_widgets,
    swap_dimensions,
    swap_positions,
    toggle_checked,
    unlock_all_widgets,
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
    return CyberpunkEditorApp(json_path, (256, 128))


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
# swap_dimensions
# ===========================================================================
class TestSwapDimensions:
    def test_swaps_width_height(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=80, height=16)
        _sel(app, 0)
        swap_dimensions(app)
        assert int(_w(app, 0).width) == 16
        assert int(_w(app, 0).height) == 80

    def test_skips_locked(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=80, height=16, locked=True)
        _sel(app, 0)
        swap_dimensions(app)
        # locked => no swap
        assert int(_w(app, 0).width) == 80
        assert int(_w(app, 0).height) == 16

    def test_noop_empty_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=80, height=16)
        swap_dimensions(app)  # no selection – no crash

    def test_multi_widget_swap(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=10)
        _add(app, width=60, height=20)
        _sel(app, 0, 1)
        swap_dimensions(app)
        assert int(_w(app, 0).width) == 10
        assert int(_w(app, 1).width) == 20


# ===========================================================================
# toggle_checked
# ===========================================================================
class TestToggleChecked:
    def test_toggles_checkbox(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="checkbox", checked=False)
        _sel(app, 0)
        toggle_checked(app)
        assert _w(app, 0).checked is True

    def test_toggles_back(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="checkbox", checked=True)
        _sel(app, 0)
        toggle_checked(app)
        assert _w(app, 0).checked is False

    def test_ignores_non_checkbox(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        toggle_checked(app)  # no crash, no change

    def test_skips_locked(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="checkbox", checked=False, locked=True)
        _sel(app, 0)
        toggle_checked(app)
        assert _w(app, 0).checked is False

    def test_radiobutton(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="radiobutton", checked=False)
        _sel(app, 0)
        toggle_checked(app)
        assert _w(app, 0).checked is True


# ===========================================================================
# equalize_widths / equalize_heights
# ===========================================================================
class TestEqualizeWidths:
    def test_sets_widest(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40)
        _add(app, width=80)
        _add(app, width=60)
        _sel(app, 0, 1, 2)
        equalize_widths(app)
        for i in range(3):
            assert int(_w(app, i).width) == 80

    def test_noop_single(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40)
        _sel(app, 0)
        equalize_widths(app)
        assert int(_w(app, 0).width) == 40


class TestEqualizeHeights:
    def test_sets_tallest(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, height=10)
        _add(app, height=30)
        _add(app, height=20)
        _sel(app, 0, 1, 2)
        equalize_heights(app)
        for i in range(3):
            assert int(_w(app, i).height) == 30

    def test_noop_single(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, height=10)
        _sel(app, 0)
        equalize_heights(app)
        assert int(_w(app, 0).height) == 10


# ===========================================================================
# swap_positions
# ===========================================================================
class TestSwapPositions:
    def test_swaps_xy(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=20)
        _add(app, x=100, y=50)
        _sel(app, 0, 1)
        swap_positions(app)
        assert int(_w(app, 0).x) == 100
        assert int(_w(app, 0).y) == 50
        assert int(_w(app, 1).x) == 10
        assert int(_w(app, 1).y) == 20

    def test_needs_exactly_two(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=20)
        _sel(app, 0)
        swap_positions(app)  # single – no crash

    def test_three_widgets_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0)
        _add(app, x=10, y=10)
        _add(app, x=20, y=20)
        _sel(app, 0, 1, 2)
        swap_positions(app)  # 3 widgets – no swap
        assert int(_w(app, 0).x) == 0


# ===========================================================================
# move_selection_to_origin
# ===========================================================================
class TestMoveSelectionToOrigin:
    def test_moves_to_origin(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=40, y=60)
        _add(app, x=80, y=100)
        _sel(app, 0, 1)
        move_selection_to_origin(app)
        assert int(_w(app, 0).x) == 0
        assert int(_w(app, 0).y) == 0
        assert int(_w(app, 1).x) == 40
        assert int(_w(app, 1).y) == 40

    def test_already_at_origin(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0)
        _sel(app, 0)
        move_selection_to_origin(app)
        assert int(_w(app, 0).x) == 0
        assert int(_w(app, 0).y) == 0

    def test_noop_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=40, y=60)
        move_selection_to_origin(app)  # no crash


# ===========================================================================
# duplicate_below / duplicate_right
# ===========================================================================
class TestDuplicateBelow:
    def test_creates_clone_below(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10, width=40, height=20)
        _sel(app, 0)
        duplicate_below(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2
        clone = sc.widgets[1]
        assert int(clone.x) == 10
        assert int(clone.y) == 10 + 20 + GRID  # y + height + GRID

    def test_noop_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        duplicate_below(app)  # no crash


class TestDuplicateRight:
    def test_creates_clone_right(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10, width=40, height=20)
        _sel(app, 0)
        duplicate_right(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2
        clone = sc.widgets[1]
        assert int(clone.y) == 10
        assert int(clone.x) == 10 + 40 + GRID  # x + width + GRID

    def test_noop_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        duplicate_right(app)  # no crash


# ===========================================================================
# quick_clone
# ===========================================================================
class TestQuickClone:
    def test_clones_with_offset(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10, width=40, height=20)
        _sel(app, 0)
        quick_clone(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2
        clone = sc.widgets[1]
        assert int(clone.x) == 10 + GRID
        assert int(clone.y) == 10 + GRID

    def test_clones_multiple(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10)
        _add(app, x=50, y=10)
        _sel(app, 0, 1)
        quick_clone(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 4

    def test_selection_moves_to_clones(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10)
        _sel(app, 0)
        quick_clone(app)
        assert 1 in app.state.selected  # clone is selected

    def test_noop_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        quick_clone(app)  # no crash


# ===========================================================================
# cycle_gray_fg / cycle_gray_bg
# ===========================================================================
class TestCycleGrayFg:
    def test_cycles_from_default(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="")
        _sel(app, 0)
        cycle_gray_fg(app)
        fg = str(_w(app, 0).color_fg).lower()
        assert fg.startswith("#")  # should be a hex color

    def test_cycles_from_known(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="#000000")
        _sel(app, 0)
        cycle_gray_fg(app)
        assert str(_w(app, 0).color_fg).lower() == "#111111"

    def test_wraps_from_last(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="#ffffff")
        _sel(app, 0)
        cycle_gray_fg(app)
        assert str(_w(app, 0).color_fg).lower() == "#000000"

    def test_applies_to_all_selected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="#000000")
        _add(app, color_fg="#555555")
        _sel(app, 0, 1)
        cycle_gray_fg(app)
        assert str(_w(app, 0).color_fg) == str(_w(app, 1).color_fg)


class TestCycleGrayBg:
    def test_cycles_from_known(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_bg="#000000")
        _sel(app, 0)
        cycle_gray_bg(app)
        assert str(_w(app, 0).color_bg).lower() == "#111111"

    def test_noop_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_bg="#000000")
        cycle_gray_bg(app)  # no selection => no crash


# ===========================================================================
# clear_margins / clear_padding
# ===========================================================================
class TestClearMargins:
    def test_clears(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, margin_x=4, margin_y=6)
        _sel(app, 0)
        clear_margins(app)
        assert int(getattr(_w(app, 0), "margin_x", 0) or 0) == 0
        assert int(getattr(_w(app, 0), "margin_y", 0) or 0) == 0

    def test_noop_already_zero(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app, 0)
        clear_margins(app)  # no crash

    def test_noop_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, margin_x=4)
        clear_margins(app)  # no selection => no crash


class TestClearPadding:
    def test_clears(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, padding_x=4, padding_y=6)
        _sel(app, 0)
        clear_padding(app)
        assert int(getattr(_w(app, 0), "padding_x", 0) or 0) == 0
        assert int(getattr(_w(app, 0), "padding_y", 0) or 0) == 0

    def test_noop_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        clear_padding(app)  # no crash


# ===========================================================================
# hide_unselected / show_all_widgets / unlock_all_widgets / enable_all_widgets
# ===========================================================================
class TestHideUnselected:
    def test_hides_non_selected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="A")
        _add(app, text="B")
        _add(app, text="C")
        _sel(app, 1)
        hide_unselected(app)
        assert getattr(_w(app, 0), "visible", True) is False
        assert getattr(_w(app, 1), "visible", True) is True
        assert getattr(_w(app, 2), "visible", True) is False

    def test_noop_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        hide_unselected(app)  # no crash


class TestShowAllWidgets:
    def test_shows_hidden(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, visible=False)
        _add(app, visible=False)
        show_all_widgets(app)
        assert getattr(_w(app, 0), "visible", True) is True
        assert getattr(_w(app, 1), "visible", True) is True

    def test_noop_all_visible(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        show_all_widgets(app)  # no crash

    def test_noop_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        show_all_widgets(app)  # no crash


class TestUnlockAllWidgets:
    def test_unlocks(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, locked=True)
        _add(app, locked=True)
        unlock_all_widgets(app)
        assert getattr(_w(app, 0), "locked", False) is False
        assert getattr(_w(app, 1), "locked", False) is False

    def test_noop_none_locked(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        unlock_all_widgets(app)  # no crash

    def test_noop_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        unlock_all_widgets(app)  # no crash


class TestEnableAllWidgets:
    def test_enables(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, enabled=False)
        _add(app, enabled=False)
        enable_all_widgets(app)
        assert getattr(_w(app, 0), "enabled", True) is True
        assert getattr(_w(app, 1), "enabled", True) is True

    def test_noop_all_enabled(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        enable_all_widgets(app)  # no crash


# ===========================================================================
# select_bordered
# ===========================================================================
class TestSelectBordered:
    def test_selects_bordered(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, border=True)
        _add(app, border=False)
        _add(app, border=True)
        select_bordered(app)
        assert 0 in app.state.selected
        assert 2 in app.state.selected
        assert 1 not in app.state.selected

    def test_toggle_selects_unbordered(self, tmp_path, monkeypatch):
        """When all selected are bordered, it flips to selecting unbordered."""
        app = _make_app(tmp_path, monkeypatch)
        _add(app, border=True)
        _add(app, border=False)
        _add(app, border=True)
        _sel(app, 0, 2)  # both bordered
        select_bordered(app)
        assert 1 in app.state.selected  # unbordered one
        assert 0 not in app.state.selected

    def test_noop_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        select_bordered(app)  # no crash


# ===========================================================================
# select_same_size
# ===========================================================================
class TestSelectSameSize:
    def test_selects_matching(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=20)
        _add(app, width=40, height=20)
        _add(app, width=80, height=16)
        _sel(app, 0)
        select_same_size(app)
        assert 0 in app.state.selected
        assert 1 in app.state.selected
        assert 2 not in app.state.selected

    def test_noop_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=20)
        select_same_size(app)  # no crash


# ===========================================================================
# select_all_panels
# ===========================================================================
class TestSelectAllPanels:
    def test_selects_panels(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="panel", width=120, height=60)
        _add(app, type="label")
        _add(app, type="panel", width=100, height=50)
        select_all_panels(app)
        assert 0 in app.state.selected
        assert 2 in app.state.selected
        assert 1 not in app.state.selected

    def test_no_panels(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        select_all_panels(app)
        # no panels => empty or status msg


# ===========================================================================
# select_parent_panel / select_children
# ===========================================================================
class TestSelectParentPanel:
    def test_finds_enclosing_panel(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="panel", x=0, y=0, width=200, height=100)
        _add(app, type="label", x=10, y=10, width=40, height=16)
        _sel(app, 1)
        select_parent_panel(app)
        assert 0 in app.state.selected

    def test_finds_smallest_enclosing(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="panel", x=0, y=0, width=250, height=120)  # big
        _add(app, type="panel", x=5, y=5, width=100, height=50)  # small
        _add(app, type="label", x=10, y=10, width=40, height=16)
        _sel(app, 2)
        select_parent_panel(app)
        assert 1 in app.state.selected  # smaller panel

    def test_no_parent(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label", x=10, y=10, width=40, height=16)
        _sel(app, 0)
        select_parent_panel(app)  # no enclosing panel => no crash


class TestSelectChildren:
    def test_selects_children(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="panel", x=0, y=0, width=200, height=100)
        _add(app, type="label", x=10, y=10, width=40, height=16)
        _add(app, type="button", x=60, y=10, width=40, height=16)
        _add(app, type="label", x=250, y=0, width=40, height=16)  # outside
        _sel(app, 0)
        select_children(app)
        assert 1 in app.state.selected
        assert 2 in app.state.selected
        assert 3 not in app.state.selected

    def test_non_panel_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        select_children(app)  # not a panel => no crash

    def test_empty_panel(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="panel", x=0, y=0, width=50, height=50)
        _sel(app, 0)
        select_children(app)  # no children => no crash


# ===========================================================================
# flip_vertical / flip_horizontal
# ===========================================================================
class TestFlipVertical:
    def test_mirrors_y(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=40, height=20)
        _add(app, x=0, y=40, width=40, height=20)
        _sel(app, 0, 1)
        flip_vertical(app)
        # After flip: widget that was at top should be at bottom and vice versa
        assert int(_w(app, 0).y) == 40
        assert int(_w(app, 1).y) == 0

    def test_noop_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        flip_vertical(app)  # no crash


class TestFlipHorizontal:
    def test_mirrors_x(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=40, height=20)
        _add(app, x=60, y=0, width=40, height=20)
        _sel(app, 0, 1)
        flip_horizontal(app)
        assert int(_w(app, 0).x) == 60
        assert int(_w(app, 1).x) == 0

    def test_noop_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        flip_horizontal(app)  # no crash


# ===========================================================================
# normalize_sizes
# ===========================================================================
class TestNormalizeSizes:
    def test_sets_average(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=20)
        _add(app, width=80, height=40)
        _sel(app, 0, 1)
        normalize_sizes(app)
        # avg_w = (40+80)//2 = 60, avg_h = (20+40)//2 = 30
        assert int(_w(app, 0).width) == 60
        assert int(_w(app, 0).height) == 30
        assert int(_w(app, 1).width) == 60
        assert int(_w(app, 1).height) == 30

    def test_noop_single(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=20)
        _sel(app, 0)
        normalize_sizes(app)  # needs 2+

    def test_minimum_grid(self, tmp_path, monkeypatch):
        """Average below GRID should be clamped to GRID."""
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=GRID, height=GRID)
        _add(app, width=GRID, height=GRID)
        _sel(app, 0, 1)
        normalize_sizes(app)
        assert int(_w(app, 0).width) >= GRID
        assert int(_w(app, 0).height) >= GRID


# ===========================================================================
# increment_text
# ===========================================================================
class TestIncrementText:
    def test_appends_numbers(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="Item")
        _add(app, text="Item")
        _add(app, text="Item")
        _sel(app, 0, 1, 2)
        increment_text(app)
        assert _w(app, 0).text == "Item 1"
        assert _w(app, 1).text == "Item 2"
        assert _w(app, 2).text == "Item 3"

    def test_strips_existing_number(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="Line 99")
        _sel(app, 0)
        increment_text(app)
        assert _w(app, 0).text == "Line 1"

    def test_empty_text_gets_number(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="")
        _sel(app, 0)
        increment_text(app)
        assert _w(app, 0).text == "1"

    def test_noop_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        increment_text(app)  # no crash


# ===========================================================================
# auto_rename
# ===========================================================================
class TestAutoRename:
    def test_renames_by_type(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _add(app, type="button")
        _add(app, type="label")
        _sel(app, 0, 1, 2)
        auto_rename(app)
        assert _w(app, 0).id == "label_1"
        assert _w(app, 1).id == "button_1"
        assert _w(app, 2).id == "label_2"

    def test_noop_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        auto_rename(app)  # no crash


# ===========================================================================
# auto_name_scene
# ===========================================================================
class TestAutoNameScene:
    def test_names_all_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _add(app, type="button")
        _add(app, type="label")
        auto_name_scene(app)
        assert _w(app, 0).id == "label_1"
        assert _w(app, 1).id == "button_1"
        assert _w(app, 2).id == "label_2"

    def test_noop_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        auto_name_scene(app)  # no crash


# ===========================================================================
# outline_mode
# ===========================================================================
class TestOutlineMode:
    def test_sets_wireframe(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, border=False, color_bg="#ffffff")
        _sel(app, 0)
        outline_mode(app)
        assert _w(app, 0).border is True
        assert str(_w(app, 0).color_bg).lower() == "#000000"

    def test_multi_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, border=False)
        _add(app, border=False)
        _sel(app, 0, 1)
        outline_mode(app)
        assert _w(app, 0).border is True
        assert _w(app, 1).border is True

    def test_noop_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        outline_mode(app)  # no crash


# ===========================================================================
# clone_text
# ===========================================================================
class TestCloneText:
    def test_copies_text_from_first(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="Source")
        _add(app, text="Other")
        _add(app, text="Another")
        _sel(app, 0, 1, 2)
        clone_text(app)
        assert _w(app, 1).text == "Source"
        assert _w(app, 2).text == "Source"
        assert _w(app, 0).text == "Source"  # unchanged

    def test_noop_single(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="Solo")
        _sel(app, 0)
        clone_text(app)  # needs 2+


# ===========================================================================
# Integration: multi-step workflows
# ===========================================================================
class TestMultiStepWorkflows:
    def test_clone_then_flip(self, tmp_path, monkeypatch):
        """Clone a widget then flip the group horizontally."""
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10, width=40, height=20)
        _sel(app, 0)
        quick_clone(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2
        _sel(app, 0, 1)
        flip_horizontal(app)
        # positions should be mirrored

    def test_hide_show_cycle(self, tmp_path, monkeypatch):
        """Hide unselected, then show all brings them back."""
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="A")
        _add(app, text="B")
        _sel(app, 0)
        hide_unselected(app)
        assert getattr(_w(app, 1), "visible", True) is False
        show_all_widgets(app)
        assert getattr(_w(app, 1), "visible", True) is True

    def test_lock_unlock_cycle(self, tmp_path, monkeypatch):
        """Lock some widgets, unlock all restores them."""
        app = _make_app(tmp_path, monkeypatch)
        _add(app, locked=True)
        _add(app, locked=True)
        unlock_all_widgets(app)
        assert getattr(_w(app, 0), "locked", False) is False
        assert getattr(_w(app, 1), "locked", False) is False

    def test_rename_then_increment(self, tmp_path, monkeypatch):
        """Auto-rename, then increment text for labeling."""
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label", text="Item")
        _add(app, type="label", text="Item")
        _sel(app, 0, 1)
        auto_rename(app)
        assert _w(app, 0).id == "label_1"
        assert _w(app, 1).id == "label_2"
        increment_text(app)
        assert _w(app, 0).text == "Item 1"
        assert _w(app, 1).text == "Item 2"

    def test_normalize_then_equalize(self, tmp_path, monkeypatch):
        """Normalize sizes then equalize heights (should be no-op after normalize)."""
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=20)
        _add(app, width=80, height=40)
        _sel(app, 0, 1)
        normalize_sizes(app)
        h_after = int(_w(app, 0).height)
        equalize_heights(app)
        assert int(_w(app, 0).height) == h_after  # already equal

    def test_duplicate_below_then_move_to_origin(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=50, y=50, width=40, height=20)
        _sel(app, 0)
        duplicate_below(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2
        _sel(app, 0, 1)
        move_selection_to_origin(app)
        assert int(_w(app, 0).x) == 0
        assert int(_w(app, 0).y) == 0

    def test_cycle_gray_both(self, tmp_path, monkeypatch):
        """Cycle fg and bg independently."""
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="#000000", color_bg="#000000")
        _sel(app, 0)
        cycle_gray_fg(app)
        cycle_gray_bg(app)
        assert str(_w(app, 0).color_fg).lower() == "#111111"
        assert str(_w(app, 0).color_bg).lower() == "#111111"

    def test_clear_margins_and_padding(self, tmp_path, monkeypatch):
        """Clear both margins and padding in sequence."""
        app = _make_app(tmp_path, monkeypatch)
        _add(app, margin_x=4, margin_y=2, padding_x=3, padding_y=5)
        _sel(app, 0)
        clear_margins(app)
        clear_padding(app)
        assert int(getattr(_w(app, 0), "margin_x", 0) or 0) == 0
        assert int(getattr(_w(app, 0), "padding_x", 0) or 0) == 0

    def test_select_panels_then_children(self, tmp_path, monkeypatch):
        """Select all panels, then select children of the first one."""
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="panel", x=0, y=0, width=200, height=100)
        _add(app, type="label", x=10, y=10, width=40, height=16)
        _add(app, type="label", x=60, y=10, width=40, height=16)
        select_all_panels(app)
        assert 0 in app.state.selected
        _sel(app, 0)
        select_children(app)
        assert 1 in app.state.selected
        assert 2 in app.state.selected
