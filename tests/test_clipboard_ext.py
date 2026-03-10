"""Extended tests for cyberpunk_designer/selection_ops/clipboard.py — targeting
uncovered lines to push coverage from 76% to 90%+."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pygame

from cyberpunk_designer.constants import GRID
from cyberpunk_designer.selection_ops import selection_bounds, set_selection
from cyberpunk_designer.selection_ops.clipboard import (
    broadcast_to_all_scenes,
    copy_selection,
    copy_to_next_scene,
    duplicate_below,
    duplicate_right,
    duplicate_selection,
    export_selection_json,
    extract_to_new_scene,
    paste_clipboard,
    paste_in_place,
    quick_clone,
)
from cyberpunk_designer.state import EditorState
from ui_designer import SceneConfig, UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=24, height=16, text="w")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _app(widgets: Optional[List[WidgetConfig]] = None, *, snap: bool = False,
         extra_scenes: Optional[dict] = None):
    designer = UIDesigner(256, 128)
    designer.create_scene("main")
    sc = designer.scenes["main"]
    for w in (widgets or []):
        sc.widgets.append(w)
    if extra_scenes:
        for name, sw in extra_scenes.items():
            designer.scenes[name] = SceneConfig(
                name=name, width=256, height=128, widgets=list(sw),
            )
    layout = MagicMock()
    layout.canvas_rect = pygame.Rect(0, 0, 256, 128)
    state = EditorState(designer, layout)
    app = SimpleNamespace(
        designer=designer,
        state=state,
        snap_enabled=snap,
        clipboard=[],
        pointer_pos=(0, 0),
        scene_rect=pygame.Rect(0, 0, 256, 128),
        layout=layout,
        _dirty=False,
        _set_status=MagicMock(),
        _mark_dirty=lambda: setattr(app, "_dirty", True),
        _primary_group_for_index=lambda idx: None,
        _group_members=lambda name: [],
        _selection_bounds=lambda indices: selection_bounds(app, indices),
        _move_selection=MagicMock(),
        _set_selection=lambda indices, anchor_idx=None: set_selection(app, indices, anchor_idx),
    )
    app._mark_dirty = lambda: setattr(app, "_dirty", True)
    return app


# ---------------------------------------------------------------------------
# paste_clipboard
# ---------------------------------------------------------------------------


class TestPasteClipboard:
    def test_empty_clipboard_status(self):
        app = _app([_w()])
        paste_clipboard(app)
        app._set_status.assert_called()
        assert "empty" in app._set_status.call_args[0][0].lower()

    def test_paste_basic(self):
        app = _app([_w(text="orig")])
        app.clipboard = [_w(text="copied", x=8, y=8)]
        paste_clipboard(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2
        assert sc.widgets[-1].text == "copied"

    def test_paste_with_pointer_inside_scene(self):
        app = _app()
        app.clipboard = [_w(text="p", x=0, y=0)]
        app.pointer_pos = (100, 50)
        paste_clipboard(app)
        sc = app.state.current_scene()
        w = sc.widgets[-1]
        # Pointer inside scene_rect → x/y adjusted to pointer
        assert w.x >= 0
        assert w.y >= 0

    def test_paste_with_pointer_outside_scene(self):
        app = _app()
        app.clipboard = [_w(text="o", x=0, y=0)]
        app.pointer_pos = (9999, 9999)
        paste_clipboard(app)
        sc = app.state.current_scene()
        # Pointer outside → uses GRID*2 offset
        assert len(sc.widgets) == 1

    def test_paste_with_snap_enabled(self):
        app = _app(snap=True)
        app.clipboard = [_w(text="s", x=3, y=3)]
        app.pointer_pos = (0, 0)
        paste_clipboard(app)
        sc = app.state.current_scene()
        nw = sc.widgets[-1]
        assert nw.x % GRID == 0
        assert nw.y % GRID == 0

    def test_paste_clamps_to_scene(self):
        app = _app()
        app.clipboard = [_w(text="big", x=0, y=0, width=24, height=16)]
        app.pointer_pos = (255, 127)
        paste_clipboard(app)
        sc = app.state.current_scene()
        nw = sc.widgets[-1]
        assert int(nw.x) + int(nw.width) <= sc.width
        assert int(nw.y) + int(nw.height) <= sc.height

    def test_paste_sets_selection(self):
        app = _app([_w()])
        app.clipboard = [_w(text="a"), _w(text="b")]
        paste_clipboard(app)
        assert len(app.state.selected) == 2
        assert app.state.selected_idx == app.state.selected[0]

    def test_paste_no_scene_rect(self):
        app = _app()
        app.clipboard = [_w(text="x")]
        app.scene_rect = None
        paste_clipboard(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 1

    def test_paste_scene_rect_no_collidepoint(self):
        app = _app()
        app.clipboard = [_w(text="x")]
        app.scene_rect = SimpleNamespace(x=0, y=0)  # no collidepoint
        paste_clipboard(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 1

    def test_paste_multiple_widgets(self):
        app = _app()
        app.clipboard = [_w(text="a", x=0, y=0), _w(text="b", x=24, y=16)]
        paste_clipboard(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2
        assert app.state.selected == [0, 1]


# ---------------------------------------------------------------------------
# copy_to_next_scene
# ---------------------------------------------------------------------------


class TestCopyToNextScene:
    def test_nothing_selected(self):
        app = _app([_w()])
        copy_to_next_scene(app)
        app._set_status.assert_called()
        assert "nothing" in app._set_status.call_args[0][0].lower()

    def test_only_one_scene(self):
        app = _app([_w()])
        set_selection(app, [0])
        copy_to_next_scene(app)
        assert "one scene" in app._set_status.call_args[0][0].lower()

    def test_copies_to_next_scene(self):
        app = _app([_w(text="orig")], extra_scenes={"second": []})
        set_selection(app, [0])
        copy_to_next_scene(app)
        target = app.designer.scenes["second"]
        assert len(target.widgets) == 1
        assert target.widgets[0].text == "orig"
        assert app._dirty

    def test_copies_multiple_to_next(self):
        app = _app([_w(text="a"), _w(text="b")], extra_scenes={"s2": []})
        set_selection(app, [0, 1])
        copy_to_next_scene(app)
        target = app.designer.scenes["s2"]
        assert len(target.widgets) == 2

    def test_wraps_to_first_scene(self):
        # When current is last scene, wraps to first
        app = _app([], extra_scenes={"second": []})
        sc = app.state.current_scene()
        sc.widgets.append(_w(text="w"))
        app.designer.current_scene = "second"
        # But we need to use a different approach: create app with second as current
        app2 = _app([], extra_scenes={"alpha": [], "beta": []})
        # Manually set current scene to last
        names = list(app2.designer.scenes.keys())
        last_name = names[-1]
        app2.designer.current_scene = last_name
        app2.designer.scenes[last_name].widgets.append(_w(text="wrap"))
        app2.state.selected = [0]
        app2.state.selected_idx = 0
        copy_to_next_scene(app2)
        first_name = names[0]
        target = app2.designer.scenes[first_name]
        assert any(w.text == "wrap" for w in target.widgets)

    def test_out_of_range_index_skipped(self):
        app = _app([_w(text="ok")], extra_scenes={"s2": []})
        app.state.selected = [0, 99]
        app.state.selected_idx = 0
        copy_to_next_scene(app)
        target = app.designer.scenes["s2"]
        assert len(target.widgets) == 1


# ---------------------------------------------------------------------------
# paste_in_place
# ---------------------------------------------------------------------------


class TestPasteInPlace:
    def test_empty_clipboard(self):
        app = _app()
        paste_in_place(app)
        assert "empty" in app._set_status.call_args[0][0].lower()

    def test_paste_at_original_position(self):
        app = _app([_w(text="orig", x=40, y=32)])
        app.clipboard = [_w(text="cp", x=40, y=32)]
        paste_in_place(app)
        sc = app.state.current_scene()
        pasted = sc.widgets[-1]
        assert pasted.text == "cp"
        assert int(pasted.x) == 40
        assert int(pasted.y) == 32
        assert app._dirty

    def test_paste_clamps_to_scene(self):
        app = _app()
        app.clipboard = [_w(text="far", x=999, y=999, width=24, height=16)]
        paste_in_place(app)
        sc = app.state.current_scene()
        nw = sc.widgets[-1]
        assert int(nw.x) + max(1, int(nw.width)) <= sc.width
        assert int(nw.y) + max(1, int(nw.height)) <= sc.height

    def test_paste_sets_selection(self):
        app = _app()
        app.clipboard = [_w(text="a"), _w(text="b")]
        paste_in_place(app)
        assert len(app.state.selected) == 2


# ---------------------------------------------------------------------------
# broadcast_to_all_scenes
# ---------------------------------------------------------------------------


class TestBroadcastToAllScenes:
    def test_nothing_selected(self):
        app = _app([_w()])
        broadcast_to_all_scenes(app)
        assert "nothing" in app._set_status.call_args[0][0].lower()

    def test_only_one_scene(self):
        app = _app([_w()])
        set_selection(app, [0])
        broadcast_to_all_scenes(app)
        assert "one scene" in app._set_status.call_args[0][0].lower()

    def test_broadcasts_to_all_other_scenes(self):
        app = _app(
            [_w(text="src")],
            extra_scenes={"s2": [], "s3": []},
        )
        set_selection(app, [0])
        broadcast_to_all_scenes(app)
        assert len(app.designer.scenes["s2"].widgets) == 1
        assert len(app.designer.scenes["s3"].widgets) == 1
        assert app.designer.scenes["s2"].widgets[0].text == "src"
        assert app._dirty
        # Check status mentions count
        status_msg = app._set_status.call_args[0][0]
        assert "2 scene" in status_msg

    def test_skips_current_scene(self):
        app = _app([_w(text="x")], extra_scenes={"other": []})
        set_selection(app, [0])
        broadcast_to_all_scenes(app)
        # Current scene should still have just 1 widget
        assert len(app.state.current_scene().widgets) == 1
        # Other scene should have the copy
        assert len(app.designer.scenes["other"].widgets) == 1

    def test_out_of_range_index_skipped(self):
        app = _app([_w()], extra_scenes={"s2": []})
        app.state.selected = [0, 99]
        app.state.selected_idx = 0
        broadcast_to_all_scenes(app)
        assert len(app.designer.scenes["s2"].widgets) == 1


# ---------------------------------------------------------------------------
# quick_clone
# ---------------------------------------------------------------------------


class TestQuickClone:
    def test_nothing_selected(self):
        app = _app([_w()])
        quick_clone(app)
        assert "nothing" in app._set_status.call_args[0][0].lower()

    def test_clones_with_grid_offset(self):
        app = _app([_w(text="q", x=0, y=0, width=24, height=16)])
        set_selection(app, [0])
        quick_clone(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2
        clone = sc.widgets[-1]
        assert clone.text == "q"
        assert int(clone.x) == GRID
        assert int(clone.y) == GRID
        assert app._dirty

    def test_clone_sets_selection_to_new(self):
        app = _app([_w(text="a"), _w(text="b")])
        set_selection(app, [0, 1])
        quick_clone(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 4
        # Selection should point to new widgets
        assert len(app.state.selected) == 2
        assert all(i >= 2 for i in app.state.selected)

    def test_clone_clamps_to_scene_bounds(self):
        # Widget near edge: x = 256 - 24 = 232
        app = _app([_w(text="edge", x=232, y=112, width=24, height=16)])
        set_selection(app, [0])
        quick_clone(app)
        sc = app.state.current_scene()
        clone = sc.widgets[-1]
        assert int(clone.x) + max(1, int(clone.width)) <= sc.width
        assert int(clone.y) + max(1, int(clone.height)) <= sc.height

    def test_out_of_range_index_skipped(self):
        app = _app([_w()])
        app.state.selected = [0, 99]
        app.state.selected_idx = 0
        quick_clone(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2  # only index 0 was cloned


# ---------------------------------------------------------------------------
# extract_to_new_scene
# ---------------------------------------------------------------------------


class TestExtractToNewScene:
    def test_nothing_selected(self):
        app = _app([_w()])
        extract_to_new_scene(app)
        assert "nothing" in app._set_status.call_args[0][0].lower()

    def test_extracts_to_new_scene(self):
        app = _app([_w(text="a"), _w(text="b"), _w(text="c")])
        set_selection(app, [0, 1])
        extract_to_new_scene(app)
        # Original scene should have only widget "c"
        orig_sc = app.designer.scenes["main"]
        assert len(orig_sc.widgets) == 1
        assert orig_sc.widgets[0].text == "c"
        # New scene should have "a" and "b"
        new_name = app.designer.current_scene
        assert new_name != "main"
        new_sc = app.designer.scenes[new_name]
        assert len(new_sc.widgets) == 2
        assert app._dirty

    def test_extract_switches_to_new_scene(self):
        app = _app([_w(text="x")])
        set_selection(app, [0])
        extract_to_new_scene(app)
        assert app.designer.current_scene.startswith("main_extract")

    def test_extract_deduplicates_name(self):
        app = _app([_w()], extra_scenes={"main_extract": []})
        set_selection(app, [0])
        extract_to_new_scene(app)
        # Should create main_extract_2 since main_extract already exists
        assert "main_extract_2" in app.designer.scenes

    def test_extract_sets_selection_to_moved_widgets(self):
        app = _app([_w(), _w()])
        set_selection(app, [0, 1])
        extract_to_new_scene(app)
        assert app.state.selected == [0, 1]
        assert app.state.selected_idx == 0

    def test_extract_all_out_of_range_returns_early(self):
        app = _app([_w()])
        app.state.selected = [99]
        app.state.selected_idx = 99
        extract_to_new_scene(app)
        # No new scene created, still just "main"
        assert len(app.designer.scenes) == 1


# ---------------------------------------------------------------------------
# duplicate_below
# ---------------------------------------------------------------------------


class TestDuplicateBelow:
    def test_nothing_selected(self):
        app = _app([_w()])
        duplicate_below(app)
        assert "nothing" in app._set_status.call_args[0][0].lower()

    def test_duplicates_below(self):
        app = _app([_w(text="top", x=0, y=0, width=24, height=16)])
        set_selection(app, [0])
        duplicate_below(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2
        dup = sc.widgets[-1]
        assert dup.text == "top"
        # Should be placed below: y = orig_y + height + GRID
        expected_y = 0 + 16 + GRID  # = 16 + GRID
        assert int(dup.y) == expected_y
        assert app._dirty

    def test_duplicate_below_multiple(self):
        app = _app([
            _w(text="a", x=0, y=0, width=24, height=16),
            _w(text="b", x=0, y=24, width=24, height=16),
        ])
        set_selection(app, [0, 1])
        duplicate_below(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 4
        # New selection is the duplicates
        assert len(app.state.selected) == 2
        assert all(i >= 2 for i in app.state.selected)

    def test_all_out_of_range_noop(self):
        app = _app([_w()])
        app.state.selected = [99]
        app.state.selected_idx = 99
        duplicate_below(app)
        assert len(app.state.current_scene().widgets) == 1


# ---------------------------------------------------------------------------
# duplicate_right
# ---------------------------------------------------------------------------


class TestDuplicateRight:
    def test_nothing_selected(self):
        app = _app([_w()])
        duplicate_right(app)
        assert "nothing" in app._set_status.call_args[0][0].lower()

    def test_duplicates_right(self):
        app = _app([_w(text="left", x=0, y=0, width=24, height=16)])
        set_selection(app, [0])
        duplicate_right(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2
        dup = sc.widgets[-1]
        assert dup.text == "left"
        # Should be placed right: x = orig_x + width + GRID
        expected_x = 0 + 24 + GRID
        assert int(dup.x) == expected_x
        assert app._dirty

    def test_duplicate_right_multiple(self):
        app = _app([
            _w(text="a", x=0, y=0, width=24, height=16),
            _w(text="b", x=32, y=0, width=24, height=16),
        ])
        set_selection(app, [0, 1])
        duplicate_right(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 4
        assert len(app.state.selected) == 2

    def test_all_out_of_range_noop(self):
        app = _app([_w()])
        app.state.selected = [99]
        app.state.selected_idx = 99
        duplicate_right(app)
        assert len(app.state.current_scene().widgets) == 1


# ---------------------------------------------------------------------------
# export_selection_json
# ---------------------------------------------------------------------------


class TestExportSelectionJson:
    def test_nothing_selected(self):
        app = _app([_w()])
        export_selection_json(app)
        assert "nothing" in app._set_status.call_args[0][0].lower()

    def test_exports_json_to_scrap(self):
        app = _app([_w(text="exp", x=8, y=8)])
        set_selection(app, [0])
        with patch("cyberpunk_designer.selection_ops.clipboard.pygame.scrap") as mock_scrap:
            export_selection_json(app)
            mock_scrap.init.assert_called_once()
            mock_scrap.put.assert_called_once()
            data = mock_scrap.put.call_args[0][1]
            parsed = json.loads(data.decode("utf-8"))
            assert len(parsed) == 1
            assert parsed[0]["text"] == "exp"

    def test_exports_multiple(self):
        app = _app([_w(text="a"), _w(text="b")])
        set_selection(app, [0, 1])
        with patch("cyberpunk_designer.selection_ops.clipboard.pygame.scrap") as mock_scrap:
            export_selection_json(app)
            data = mock_scrap.put.call_args[0][1]
            parsed = json.loads(data.decode("utf-8"))
            assert len(parsed) == 2

    def test_out_of_range_indices_skipped(self):
        app = _app([_w(text="ok")])
        app.state.selected = [0, 99]
        app.state.selected_idx = 0
        with patch("cyberpunk_designer.selection_ops.clipboard.pygame.scrap") as mock_scrap:
            export_selection_json(app)
            data = mock_scrap.put.call_args[0][1]
            parsed = json.loads(data.decode("utf-8"))
            assert len(parsed) == 1

    def test_scrap_exception_handled(self):
        app = _app([_w(text="ok")])
        set_selection(app, [0])
        with patch("cyberpunk_designer.selection_ops.clipboard.pygame.scrap") as mock_scrap:
            mock_scrap.init.side_effect = RuntimeError("no display")
            # Should not raise
            export_selection_json(app)

    def test_all_out_of_range_returns_early(self):
        app = _app([_w()])
        app.state.selected = [99]
        app.state.selected_idx = 99
        export_selection_json(app)
        # No crash, status was set for "nothing selected" — but 99 is still in selected
        # The function will find 0 valid widgets and return early


# ---------------------------------------------------------------------------
# copy_selection — edge cases
# ---------------------------------------------------------------------------


class TestCopySelectionEdge:
    def test_out_of_range_index_skipped(self):
        app = _app([_w(text="ok")])
        app.state.selected = [0, 99]
        app.state.selected_idx = 0
        copy_selection(app)
        assert len(app.clipboard) == 1
        assert app.clipboard[0].text == "ok"


# ---------------------------------------------------------------------------
# duplicate_selection — edge cases
# ---------------------------------------------------------------------------


class TestDuplicateSelectionEdge:
    def test_duplicate_clamps_to_scene(self):
        app = _app([_w(text="edge", x=240, y=120, width=24, height=16)])
        set_selection(app, [0])
        duplicate_selection(app)
        sc = app.state.current_scene()
        dup = sc.widgets[-1]
        assert int(dup.x) + int(dup.width) <= sc.width
        assert int(dup.y) + int(dup.height) <= sc.height

    def test_duplicate_marks_dirty(self):
        app = _app([_w()])
        set_selection(app, [0])
        duplicate_selection(app)
        assert app._dirty

    def test_out_of_range_index_skipped(self):
        app = _app([_w(text="ok")])
        app.state.selected = [0, 99]
        app.state.selected_idx = 0
        duplicate_selection(app)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2
