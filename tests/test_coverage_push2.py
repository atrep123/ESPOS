"""Tests targeting uncovered lines in creators, alignment, focus_nav, and drawing modules."""

from __future__ import annotations

from unittest.mock import MagicMock

from ui_models import WidgetConfig

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=60, height=20, text="hello")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _make_app(tmp_path, monkeypatch, *, widgets=None, snap=False):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    from cyberpunk_editor import CyberpunkEditorApp

    json_path = tmp_path / "scene.json"
    app = CyberpunkEditorApp(json_path, (256, 128))
    if not hasattr(app, "_save_undo_state"):
        app._save_undo_state = lambda: None
    if widgets:
        sc = app.state.current_scene()
        for w in widgets:
            sc.widgets.append(w)
    app.snap_enabled = snap
    return app


# ===========================================================================
# selection_ops/creators.py — placement below selection (5 funcs × 3 lines each)
# ===========================================================================


class TestCreatorsPlaceBelowSelection:
    """When widgets are selected, new creators place items below them."""

    def test_slider_with_label_below_selection(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops.creators import create_slider_with_label

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10, width=40, height=20)])
        app.state.selected = [0]
        app.state.selected_idx = 0
        create_slider_with_label(app)
        assert len(app.state.current_scene().widgets) > 1

    def test_gauge_panel_below_selection(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops.creators import create_gauge_panel

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10, width=40, height=20)])
        app.state.selected = [0]
        app.state.selected_idx = 0
        create_gauge_panel(app)
        assert len(app.state.current_scene().widgets) > 1

    def test_progress_section_below_selection(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops.creators import create_progress_section

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10, width=40, height=20)])
        app.state.selected = [0]
        app.state.selected_idx = 0
        create_progress_section(app)
        assert len(app.state.current_scene().widgets) > 1

    def test_icon_button_row_below_selection(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops.creators import create_icon_button_row

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10, width=40, height=20)])
        app.state.selected = [0]
        app.state.selected_idx = 0
        create_icon_button_row(app)
        assert len(app.state.current_scene().widgets) > 1

    def test_card_layout_below_selection(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops.creators import create_card_layout

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10, width=40, height=20)])
        app.state.selected = [0]
        app.state.selected_idx = 0
        create_card_layout(app)
        assert len(app.state.current_scene().widgets) > 1

    def test_wrap_in_panel_no_bounds(self, tmp_path, monkeypatch):
        """wrap_in_panel returns when selection has no valid bounds (line 487)."""
        from cyberpunk_designer.selection_ops.creators import wrap_in_panel

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = [99]  # out-of-range
        wrap_in_panel(app)
        assert len(app.state.current_scene().widgets) == 0


# ===========================================================================
# selection_ops/alignment.py — exception, early-return, locked-skip paths
# ===========================================================================


class TestAlignmentEdges:
    def test_snap_to_grid_save_state_exc(self, tmp_path, monkeypatch):
        """_save_state raising in snap_selection_to_grid (lines 14-15)."""
        from cyberpunk_designer.selection_ops.alignment import snap_selection_to_grid

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=3, y=5)])
        app.state.selected = [0]
        app.designer._save_state = MagicMock(side_effect=RuntimeError("fail"))
        snap_selection_to_grid(app)

    def test_center_in_scene_no_valid(self, tmp_path, monkeypatch):
        """center_in_scene with all out-of-range indices (line 39)."""
        from cyberpunk_designer.selection_ops.alignment import center_in_scene

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = [99]
        center_in_scene(app)

    def test_center_in_scene_save_state_exc(self, tmp_path, monkeypatch):
        """_save_state raising in center_in_scene (lines 42-43)."""
        from cyberpunk_designer.selection_ops.alignment import center_in_scene

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        app.state.selected = [0]
        app.designer._save_state = MagicMock(side_effect=RuntimeError("fail"))
        center_in_scene(app)

    def test_center_in_parent_out_of_range(self, tmp_path, monkeypatch):
        """center_in_parent with out-of-range idx (line 166)."""
        from cyberpunk_designer.selection_ops.alignment import center_in_parent

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0, 99]  # 99 is out of range
        center_in_parent(app)

    def test_center_in_parent_not_panel(self, tmp_path, monkeypatch):
        """center_in_parent where surrounding widget is not panel (line 177)."""
        from cyberpunk_designer.selection_ops.alignment import center_in_parent

        w1 = _w(x=10, y=10, width=20, height=20)
        w2 = _w(x=0, y=0, width=100, height=100, type="label")  # not a panel
        app = _make_app(tmp_path, monkeypatch, widgets=[w1, w2])
        app.state.selected = [0]
        center_in_parent(app)

    def test_align_h_centers_first_idx_oob(self, tmp_path, monkeypatch):
        """align_h_centers with first_idx out of range (line 209)."""
        from cyberpunk_designer.selection_ops.alignment import align_h_centers

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [99, 0]  # first out of range
        align_h_centers(app)

    def test_align_h_centers_secondary_oob(self, tmp_path, monkeypatch):
        """align_h_centers with secondary idx out of range (line 216)."""
        from cyberpunk_designer.selection_ops.alignment import align_h_centers

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w(x=50)])
        app.state.selected = [0, 99]  # second out of range
        align_h_centers(app)

    def test_align_v_centers_first_idx_oob(self, tmp_path, monkeypatch):
        """align_v_centers with first_idx out of range (line 233)."""
        from cyberpunk_designer.selection_ops.alignment import align_v_centers

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [99, 0]
        align_v_centers(app)

    def test_align_v_centers_secondary_oob(self, tmp_path, monkeypatch):
        """align_v_centers with secondary idx out of range (line 240)."""
        from cyberpunk_designer.selection_ops.alignment import align_v_centers

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w(y=50)])
        app.state.selected = [0, 99]
        align_v_centers(app)

    def test_align_left_oob(self, tmp_path, monkeypatch):
        """align_left_edges with oob first_idx (line 257)."""
        from cyberpunk_designer.selection_ops.alignment import align_left_edges

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [99, 0]
        align_left_edges(app)

    def test_align_left_secondary_oob(self, tmp_path, monkeypatch):
        """align_left_edges with secondary oob (line 263)."""
        from cyberpunk_designer.selection_ops.alignment import align_left_edges

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 99]
        align_left_edges(app)

    def test_align_top_oob(self, tmp_path, monkeypatch):
        """align_top_edges with oob first idx (line 278)."""
        from cyberpunk_designer.selection_ops.alignment import align_top_edges

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [99, 0]
        align_top_edges(app)

    def test_align_top_secondary_oob(self, tmp_path, monkeypatch):
        """align_top_edges secondary oob (line 284)."""
        from cyberpunk_designer.selection_ops.alignment import align_top_edges

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 99]
        align_top_edges(app)

    def test_align_right_oob(self, tmp_path, monkeypatch):
        """align_right_edges oob first (line 299)."""
        from cyberpunk_designer.selection_ops.alignment import align_right_edges

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [99, 0]
        align_right_edges(app)

    def test_align_right_secondary_oob(self, tmp_path, monkeypatch):
        """align_right_edges secondary oob (line 306)."""
        from cyberpunk_designer.selection_ops.alignment import align_right_edges

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 99]
        align_right_edges(app)

    def test_align_bottom_oob(self, tmp_path, monkeypatch):
        """align_bottom_edges oob first (line 323)."""
        from cyberpunk_designer.selection_ops.alignment import align_bottom_edges

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [99, 0]
        align_bottom_edges(app)

    def test_align_bottom_secondary_oob(self, tmp_path, monkeypatch):
        """align_bottom_edges secondary oob (line 330)."""
        from cyberpunk_designer.selection_ops.alignment import align_bottom_edges

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 99]
        align_bottom_edges(app)


# ===========================================================================
# focus_nav.py — edge cases and exception paths
# ===========================================================================


class TestFocusNavEdges:
    def test_sim_runtime_restore_broken_widget(self, tmp_path, monkeypatch):
        """sim_runtime_restore when widget attr restore raises (lines 53-54)."""
        from cyberpunk_designer.focus_nav import _SimWidgetSnapshot, sim_runtime_restore

        w = _w()
        w._widget_id = "w0"
        app = _make_app(tmp_path, monkeypatch, widgets=[w])
        # Set up snapshot
        snap_obj = _SimWidgetSnapshot(text="X", value=0, enabled=True, visible=True)
        app._sim_runtime_snapshot = {"w0": snap_obj}
        app._sim_listmodels = {}
        # Make text assignment raise
        type_obj = type(app.state.current_scene().widgets[0])
        orig_set = type_obj.__setattr__

        def _bad_set(self, name, value):
            if name == "text":
                raise RuntimeError("fail")
            orig_set(self, name, value)

        monkeypatch.setattr(type_obj, "__setattr__", _bad_set)
        sim_runtime_restore(app)

    def test_ensure_focus_from_selected_idx(self, tmp_path, monkeypatch):
        """ensure_focus falls through to selected_idx path (line 330-331)."""
        from cyberpunk_designer.focus_nav import ensure_focus

        w = _w(type="button")
        app = _make_app(tmp_path, monkeypatch, widgets=[w])
        app.focus_idx = None
        app.state.selected_idx = 0
        ensure_focus(app)
        assert app.focus_idx == 0

    def test_ensure_focus_from_focusables(self, tmp_path, monkeypatch):
        """ensure_focus when selected_idx is bad, uses first focusable (line 348-349)."""
        from cyberpunk_designer.focus_nav import ensure_focus

        w = _w(type="button")
        app = _make_app(tmp_path, monkeypatch, widgets=[w])
        app.focus_idx = None
        app.state.selected_idx = 99  # out of range
        ensure_focus(app)
        assert app.focus_idx == 0

    def test_ensure_focus_no_focusable(self, tmp_path, monkeypatch):
        """ensure_focus when no focusable widgets (line 363 — set to None)."""
        from cyberpunk_designer.focus_nav import ensure_focus

        # Icon widgets are not focusable
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(type="icon")])
        app.focus_idx = None
        app.state.selected_idx = None
        ensure_focus(app)

    def test_focus_move_direction_gap_zero_vertical(self, tmp_path, monkeypatch):
        """focus_move_direction gap=0 in vertical scoring (line 412)."""
        from cyberpunk_designer.focus_nav import focus_move_direction

        w1 = _w(type="button", x=10, y=10, width=40, height=20)
        w2 = _w(type="button", x=10, y=50, width=40, height=20)
        app = _make_app(tmp_path, monkeypatch, widgets=[w1, w2])
        app.focus_idx = 0
        focus_move_direction(app, "down")

    def test_focus_move_direction_gap_zero_horizontal(self, tmp_path, monkeypatch):
        """focus_move_direction gap=0 in horizontal scoring (line 430)."""
        from cyberpunk_designer.focus_nav import focus_move_direction

        w1 = _w(type="button", x=10, y=10, width=40, height=20)
        w2 = _w(type="button", x=80, y=10, width=40, height=20)
        app = _make_app(tmp_path, monkeypatch, widgets=[w1, w2])
        app.focus_idx = 0
        focus_move_direction(app, "right")

    def test_adjust_focused_value_bad_attrs(self, tmp_path, monkeypatch):
        """adjust_focused_value with non-int value attrs (lines 457-458)."""
        from cyberpunk_designer.focus_nav import adjust_focused_value

        w = _w(type="slider")
        w.value = "bad"
        w.min_value = "bad"
        w.max_value = "bad"
        app = _make_app(tmp_path, monkeypatch, widgets=[w])
        app.focus_idx = 0
        adjust_focused_value(app, 1)

    def test_adjust_focused_value_set_raises(self, tmp_path, monkeypatch):
        """adjust_focused_value when w.value = ... raises (lines 462-463)."""
        from cyberpunk_designer.focus_nav import adjust_focused_value

        w = _w(type="slider")
        w.value = 50
        w.min_value = 0
        w.max_value = 100
        app = _make_app(tmp_path, monkeypatch, widgets=[w])
        app.focus_idx = 0
        # Make value assignment raise
        orig_set = type(w).__setattr__

        def _bad(self, name, value):
            if name == "value" and isinstance(value, int):
                raise RuntimeError("fail")
            orig_set(self, name, value)

        monkeypatch.setattr(type(w), "__setattr__", _bad)
        adjust_focused_value(app, 1)

    def test_adjust_focused_no_focusable(self, tmp_path, monkeypatch):
        """adjust_focused_value when focus is None (line 474 via ensure_focus path)."""
        from cyberpunk_designer.focus_nav import adjust_focused_value

        app = _make_app(tmp_path, monkeypatch)
        app.focus_idx = None
        adjust_focused_value(app, 1)

    def test_activate_checkbox_exc(self, tmp_path, monkeypatch):
        """activate_focused on checkbox when checked = ... raises (lines 481-482)."""
        from cyberpunk_designer.focus_nav import activate_focused

        w = _w(type="checkbox")
        app = _make_app(tmp_path, monkeypatch, widgets=[w])
        app.focus_idx = 0
        # Make checked assignment raise
        orig_set = type(w).__setattr__

        def _bad(self, name, value):
            if name == "checked":
                raise RuntimeError("fail")
            orig_set(self, name, value)

        monkeypatch.setattr(type(w), "__setattr__", _bad)
        activate_focused(app)

    def test_sim_scroll_false_return(self, tmp_path, monkeypatch):
        """_sim_try_scroll_list returns False for non-list widget (line 264)."""
        from cyberpunk_designer.focus_nav import focus_move_direction

        w = _w(type="button")
        app = _make_app(tmp_path, monkeypatch, widgets=[w, _w(type="button", x=0, y=50)])
        app.focus_idx = 0
        app.sim_input_mode = True
        focus_move_direction(app, "down")


# ===========================================================================
# drawing/canvas.py — exception and edge paths
# ===========================================================================


class TestCanvasEdges:
    def test_import(self):
        import cyberpunk_designer.drawing.canvas as c

        assert hasattr(c, "draw_canvas")


# ===========================================================================
# drawing/text.py — edge cases
# ===========================================================================


class TestDrawTextEdges:
    def test_import(self):
        import cyberpunk_designer.drawing.text as t

        assert hasattr(t, "draw_text_in_rect")


# ===========================================================================
# drawing/panels.py — edge cases
# ===========================================================================


class TestDrawPanelsEdges:
    def test_import(self):
        import cyberpunk_designer.drawing.panels as p

        assert hasattr(p, "draw_inspector")
