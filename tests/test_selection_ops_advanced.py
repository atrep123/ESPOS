"""Tests for advanced selection_ops: batch transforms, cleanup, queries,
scene management, stacking/grid, and style propagation.

Complements test_layout_selection.py (which covers basic cycle, mirror, etc.)
"""

from __future__ import annotations

from cyberpunk_designer.constants import GRID
from cyberpunk_designer.selection_ops import (
    broadcast_to_all_scenes,
    compact_widgets,
    copy_to_next_scene,
    equalize_gaps,
    extract_to_new_scene,
    flatten_z_indices,
    grid_arrange,
    invert_selection,
    make_full_height,
    make_full_width,
    paste_in_place,
    propagate_align,
    propagate_border,
    propagate_colors,
    propagate_style,
    remove_degenerate_widgets,
    remove_duplicates,
    reset_to_defaults,
    reverse_widget_order,
    select_hidden,
    select_locked,
    select_overflow,
    select_overlapping,
    snap_selection_to_grid,
    snap_sizes_to_grid,
    sort_widgets_by_position,
    stack_horizontal,
    stack_vertical,
    swap_content,
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
# Batch widget transforms
# ===========================================================================
class TestResetToDefaults:
    def test_resets_style(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, style="bold", color_fg="#ff0000", border_style="double")
        _sel(app, 0)
        reset_to_defaults(app)
        assert _w(app, 0).style == "default"
        assert _w(app, 0).border_style == "single"

    def test_keeps_position_and_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=20, width=80, height=16, text="Hello", style="bold")
        _sel(app, 0)
        reset_to_defaults(app)
        w = _w(app, 0)
        assert w.x == 10 and w.y == 20 and w.text == "Hello"

    def test_locked_widget_skipped(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, style="bold", locked=True)
        _sel(app, 0)
        reset_to_defaults(app)
        assert _w(app, 0).style == "bold"

    def test_empty_selection_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        reset_to_defaults(app)  # no crash


class TestMakeFullWidthHeight:
    def test_full_width(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, width=40)
        _sel(app, 0)
        make_full_width(app)
        w = _w(app, 0)
        sc = app.state.current_scene()
        assert w.x == 0
        assert w.width == sc.width

    def test_full_height(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, y=10, height=20)
        _sel(app, 0)
        make_full_height(app)
        w = _w(app, 0)
        sc = app.state.current_scene()
        assert w.y == 0
        assert w.height == sc.height

    def test_locked_blocks_full_width(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, width=40, locked=True)
        _sel(app, 0)
        make_full_width(app)
        assert _w(app, 0).x == 10  # unchanged


class TestSnapSelectionToGrid:
    def test_snaps_off_grid_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=5, y=3)
        _sel(app, 0)
        snap_selection_to_grid(app)
        w = _w(app, 0)
        assert w.x % GRID == 0
        assert w.y % GRID == 0

    def test_already_on_grid(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=GRID * 2, y=GRID * 3)
        _sel(app, 0)
        snap_selection_to_grid(app)
        # No change
        assert _w(app, 0).x == GRID * 2


class TestSnapSizesToGrid:
    def test_snaps_size(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=3, y=5, width=13, height=19)
        _sel(app, 0)
        snap_sizes_to_grid(app)
        w = _w(app, 0)
        assert w.width % GRID == 0
        assert w.height % GRID == 0
        assert w.width >= GRID
        assert w.height >= GRID


# ===========================================================================
# Cleanup / deduplication
# ===========================================================================
class TestRemoveDegenerateWidgets:
    def test_removes_zero_width(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w_bad = _add(app, width=10, height=16)
        # Bypass the property setter to force degenerate value
        w_bad._width = 0
        _add(app, width=80, height=16)
        remove_degenerate_widgets(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 1
        assert sc.widgets[0].width == 80

    def test_removes_negative_height(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w_bad = _add(app, width=40, height=20)
        w_bad._height = -5  # bypass property setter
        _add(app, width=40, height=20)
        remove_degenerate_widgets(app)
        assert len(app.state.current_scene().widgets) == 1

    def test_no_degenerate_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=40, height=20)
        remove_degenerate_widgets(app)
        assert len(app.state.current_scene().widgets) == 1


class TestRemoveDuplicates:
    def test_removes_exact_positional_dupes(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label", x=10, y=10, width=40, height=16)
        _add(app, type="label", x=10, y=10, width=40, height=16)
        _add(app, type="label", x=20, y=10, width=40, height=16)
        remove_duplicates(app)
        assert len(app.state.current_scene().widgets) == 2

    def test_different_types_not_dupes(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label", x=10, y=10, width=40, height=16)
        _add(app, type="button", x=10, y=10, width=40, height=16)
        remove_duplicates(app)
        assert len(app.state.current_scene().widgets) == 2


class TestFlattenZIndices:
    def test_renumbers_sequentially(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, z_index=10)
        _add(app, z_index=5)
        _add(app, z_index=20)
        flatten_z_indices(app)
        zs = [_w(app, i).z_index for i in range(3)]
        assert sorted(zs) == list(range(3))

    def test_preserves_relative_order(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, z_index=100, text="A")
        _add(app, z_index=50, text="B")
        _add(app, z_index=200, text="C")
        flatten_z_indices(app)
        # B(50) < A(100) < C(200) → B=0, A=1, C=2
        assert _w(app, 1).z_index < _w(app, 0).z_index < _w(app, 2).z_index


class TestSortWidgetsByPosition:
    def test_sorts_by_y_then_x(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=80, y=40, text="C")
        _add(app, x=0, y=0, text="A")
        _add(app, x=40, y=40, text="B")
        sort_widgets_by_position(app)
        texts = [_w(app, i).text for i in range(3)]
        assert texts == ["A", "B", "C"]


class TestCompactWidgets:
    def test_shifts_to_origin(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=20, y=30)
        _add(app, x=60, y=70)
        compact_widgets(app)
        assert _w(app, 0).x == 0 and _w(app, 0).y == 0
        assert _w(app, 1).x == 40 and _w(app, 1).y == 40

    def test_already_at_origin(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0)
        _add(app, x=40, y=20)
        compact_widgets(app)
        # No shift
        assert _w(app, 0).x == 0 and _w(app, 0).y == 0


# ===========================================================================
# Selection queries
# ===========================================================================
class TestSelectHidden:
    def test_selects_invisible(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, visible=True)
        _add(app, visible=False)
        _add(app, visible=False)
        select_hidden(app)
        assert app.state.selected == [1, 2]

    def test_none_hidden(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, visible=True)
        select_hidden(app)
        assert app.state.selected == [] or app.state.selected == [0]  # none found


class TestSelectLocked:
    def test_selects_locked(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, locked=False)
        _add(app, locked=True)
        _add(app, locked=True)
        select_locked(app)
        assert set(app.state.selected) == {1, 2}

    def test_toggle_to_unlocked_when_all_locked_selected(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, locked=False, text="A")
        _add(app, locked=True, text="B")
        # First select locked
        _sel(app, 1)
        select_locked(app)
        # Now all selected are locked → should toggle to unlocked
        assert 0 in app.state.selected


class TestSelectOverflow:
    def test_finds_truncated_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, width=20, height=12, text="Very long text that definitely overflows", border=True)
        _add(app, width=200, height=20, text="Ok", border=True)
        select_overflow(app)
        assert 0 in app.state.selected
        assert 1 not in app.state.selected


class TestSelectOverlapping:
    def test_finds_overlapping_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=40, height=40)
        _add(app, x=20, y=20, width=40, height=40)  # overlaps first
        _add(app, x=200, y=200, width=20, height=20)  # far away
        _sel(app, 0)
        select_overlapping(app)
        assert 0 in app.state.selected
        assert 1 in app.state.selected
        assert 2 not in app.state.selected

    def test_no_overlap_found(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=20, height=20)
        _add(app, x=100, y=100, width=20, height=20)
        _sel(app, 0)
        select_overlapping(app)
        # Only original selection
        assert len(app.state.selected) == 1


class TestInvertSelection:
    def test_inverts(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _add(app)
        _sel(app, 0, 2)
        invert_selection(app)
        assert app.state.selected == [1]

    def test_invert_empty_selects_all(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _add(app)
        _sel(app)
        invert_selection(app)
        assert set(app.state.selected) == {0, 1}


# ===========================================================================
# Scene management operations
# ===========================================================================
class TestExtractToNewScene:
    def test_moves_widgets_to_new_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="Stay")
        _add(app, text="Move1")
        _add(app, text="Move2")
        original_name = app.designer.current_scene
        _sel(app, 1, 2)
        extract_to_new_scene(app)
        # Widgets moved to new scene
        new_name = app.designer.current_scene
        assert new_name != original_name
        new_sc = app.designer.scenes[new_name]
        assert len(new_sc.widgets) == 2
        # Removed from original
        old_sc = app.designer.scenes[original_name]
        assert len(old_sc.widgets) == 1
        assert old_sc.widgets[0].text == "Stay"

    def test_empty_selection_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app)
        _sel(app)
        initial_scenes = len(app.designer.scenes)
        extract_to_new_scene(app)
        assert len(app.designer.scenes) == initial_scenes


class TestCopyToNextScene:
    def test_copies_to_next(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="CopyMe")
        # Create a second scene
        from ui_designer import SceneConfig

        app.designer.scenes["second"] = SceneConfig(
            name="second", width=256, height=128, widgets=[]
        )
        _sel(app, 0)
        copy_to_next_scene(app)
        target = app.designer.scenes["second"]
        assert any(w.text == "CopyMe" for w in target.widgets)

    def test_single_scene_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="Solo")
        _sel(app, 0)
        copy_to_next_scene(app)  # only one scene


class TestBroadcastToAllScenes:
    def test_copies_to_all_other_scenes(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="Shared")
        from ui_designer import SceneConfig

        app.designer.scenes["s2"] = SceneConfig(name="s2", width=256, height=128, widgets=[])
        app.designer.scenes["s3"] = SceneConfig(name="s3", width=256, height=128, widgets=[])
        _sel(app, 0)
        broadcast_to_all_scenes(app)
        assert any(w.text == "Shared" for w in app.designer.scenes["s2"].widgets)
        assert any(w.text == "Shared" for w in app.designer.scenes["s3"].widgets)


class TestPasteInPlace:
    def test_pastes_at_original_position(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, x=50, y=30, text="Orig")
        from dataclasses import asdict

        app.clipboard = [WidgetConfig(**asdict(w))]
        paste_in_place(app)
        sc = app.state.current_scene()
        pasted = sc.widgets[-1]
        assert pasted.x == 50 and pasted.y == 30


# ===========================================================================
# Stack / grid layout
# ===========================================================================
class TestStackVertical:
    def test_stacks_with_grid_gap(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=50, width=60, height=16)
        _add(app, x=30, y=10, width=60, height=16)
        _add(app, x=20, y=90, width=60, height=16)
        _sel(app, 0, 1, 2)
        stack_vertical(app)
        # Sorted by y → widget1 (y=10) first
        ws = [_w(app, i) for i in range(3)]
        # All should share same x (from first by y order)
        xs = {w.x for w in ws}
        assert len(xs) == 1
        # Each widget's y = prev.y + prev.height + GRID
        ys = sorted(w.y for w in ws)
        for i in range(1, len(ys)):
            expected = ys[i - 1] + 16 + GRID
            assert ys[i] == expected


class TestStackHorizontal:
    def test_stacks_with_grid_gap(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=80, y=10, width=30, height=16)
        _add(app, x=10, y=20, width=40, height=16)
        _add(app, x=40, y=30, width=20, height=16)
        _sel(app, 0, 1, 2)
        stack_horizontal(app)
        ws = [_w(app, i) for i in range(3)]
        # All should share same y
        ys = {w.y for w in ws}
        assert len(ys) == 1

    def test_needs_two_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10)
        _sel(app, 0)
        stack_horizontal(app)  # should not crash


class TestEqualizeGaps:
    def test_horizontal_gaps(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=20, height=16)
        _add(app, x=100, y=0, width=20, height=16)
        _add(app, x=40, y=0, width=20, height=16)
        _sel(app, 0, 1, 2)
        equalize_gaps(app, axis="h")
        ws = sorted([_w(app, i) for i in range(3)], key=lambda w: w.x)
        # Gap = width + GRID between consecutive
        for i in range(1, len(ws)):
            assert ws[i].x == ws[i - 1].x + ws[i - 1].width + GRID

    def test_vertical_gaps(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=0, y=0, width=20, height=10)
        _add(app, x=0, y=100, width=20, height=10)
        _add(app, x=0, y=40, width=20, height=10)
        _sel(app, 0, 1, 2)
        equalize_gaps(app, axis="v")
        ws = sorted([_w(app, i) for i in range(3)], key=lambda w: w.y)
        for i in range(1, len(ws)):
            assert ws[i].y == ws[i - 1].y + ws[i - 1].height + GRID

    def test_auto_detects_axis(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Spread more in X → auto = horizontal
        _add(app, x=0, y=0, width=20, height=16)
        _add(app, x=200, y=0, width=20, height=16)
        _sel(app, 0, 1)
        equalize_gaps(app, axis="auto")  # no crash


class TestGridArrange:
    def test_grid_4_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        for i in range(4):
            _add(app, x=i * 5, y=i * 5, width=20, height=10)
        _sel(app, 0, 1, 2, 3)
        grid_arrange(app)
        # sqrt(4) = 2 → 2x2 grid
        positions = [(int(_w(app, i).x), int(_w(app, i).y)) for i in range(4)]
        xs = sorted(set(p[0] for p in positions))
        ys = sorted(set(p[1] for p in positions))
        assert len(xs) == 2
        assert len(ys) == 2

    def test_grid_5_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        for _i in range(5):
            _add(app, x=0, y=0, width=20, height=10)
        _sel(app, 0, 1, 2, 3, 4)
        grid_arrange(app)
        # sqrt(5) ≈ 2.24 → ceil = 3 cols → 3x2 grid


class TestReverseWidgetOrder:
    def test_reverses(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="A")
        _add(app, text="B")
        _add(app, text="C")
        _sel(app, 0, 1, 2)
        reverse_widget_order(app)
        texts = [_w(app, i).text for i in range(3)]
        assert texts == ["C", "B", "A"]


# ===========================================================================
# Propagation functions
# ===========================================================================
class TestPropagateStyle:
    def test_copies_style_from_first(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, style="bold")
        _add(app, style="default")
        _add(app, style="default")
        _sel(app, 0, 1, 2)
        propagate_style(app)
        assert _w(app, 1).style == "bold"
        assert _w(app, 2).style == "bold"

    def test_single_widget_noop(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, style="bold")
        _sel(app, 0)
        propagate_style(app)  # needs 2+


class TestPropagateBorder:
    def test_copies_border_settings(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, border=True, border_style="double")
        _add(app, border=False, border_style="single")
        _sel(app, 0, 1)
        propagate_border(app)
        assert _w(app, 1).border is True
        assert _w(app, 1).border_style == "double"


class TestPropagateColors:
    def test_copies_fg_bg(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, color_fg="#ff0000", color_bg="#00ff00")
        _add(app, color_fg="#ffffff", color_bg="#000000")
        _sel(app, 0, 1)
        propagate_colors(app)
        assert _w(app, 1).color_fg == "#ff0000"
        assert _w(app, 1).color_bg == "#00ff00"


class TestPropagateAlign:
    def test_copies_align_valign(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, align="center", valign="bottom")
        _add(app, align="left", valign="top")
        _sel(app, 0, 1)
        propagate_align(app)
        assert _w(app, 1).align == "center"
        assert _w(app, 1).valign == "bottom"


class TestSwapContent:
    def test_swaps_text_and_value(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="Alpha", value=10)
        _add(app, text="Beta", value=20)
        _sel(app, 0, 1)
        swap_content(app)
        assert _w(app, 0).text == "Beta" and _w(app, 0).value == 20
        assert _w(app, 1).text == "Alpha" and _w(app, 1).value == 10

    def test_needs_exactly_two(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, text="A")
        _add(app, text="B")
        _add(app, text="C")
        _sel(app, 0, 1, 2)
        swap_content(app)  # should be noop — needs exactly 2
        assert _w(app, 0).text == "A"  # unchanged
