"""Tests targeting uncovered branches in focus_nav, transforms, layout, batch_ops."""

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

def _make_save_raise(app):
    app.designer._save_state = MagicMock(side_effect=TypeError("boom"))

# ---------------------------------------------------------------------------
# focus_nav.py — L216, L264, L363, L412, L430, L474
# ---------------------------------------------------------------------------

class TestFocusNavEdges:
    """Cover uncovered branches in focus_nav.py."""

    def test_activate_focused_checkbox(self, make_app):
        """L474+: activate_focused dispatches on checkbox type."""
        from cyberpunk_designer.focus_nav import activate_focused, set_focus

        app = make_app(
            widgets=[_w(type="checkbox", checked=False)],
        )
        app.sim_input_mode = True
        set_focus(app, 0)
        activate_focused(app)
        assert app.state.current_scene().widgets[0].checked is True

    def test_activate_focused_slider(self, make_app):
        """L474+: activate_focused dispatches on slider type."""
        from cyberpunk_designer.focus_nav import activate_focused, set_focus

        app = make_app(
            widgets=[_w(type="slider", value=50, min_value=0, max_value=100)],
        )
        set_focus(app, 0)
        app.focus_edit_value = False
        activate_focused(app)
        assert app.focus_edit_value is True

    def test_activate_focused_button(self, make_app):
        """L474+: activate_focused dispatches on button (default path)."""
        from cyberpunk_designer.focus_nav import activate_focused, set_focus

        app = make_app(
            widgets=[_w(type="button", text="OK")],
        )
        set_focus(app, 0)
        activate_focused(app)

    def test_focus_move_direction_single_focusable(self, make_app):
        """L363: focus_move_direction with only 1 focusable → early return."""
        from cyberpunk_designer.focus_nav import focus_move_direction, set_focus

        app = make_app(
            widgets=[_w(type="button")],
        )
        set_focus(app, 0)
        focus_move_direction(app, "down")

    def test_apply_sim_listmodel_missing_slot(self, make_app):
        """L216: _apply_sim_listmodel when btn_idx is None for a slot."""
        from cyberpunk_designer.focus_nav import (
            _apply_sim_listmodel,
            _SimListModel,
        )

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", _widget_id="mylist.item0", text="A"))
        # item1 does NOT exist → L216 continue
        m = _SimListModel(count=3, active=0, offset=0)
        _apply_sim_listmodel(app, sc, "mylist", m, visible=2)

    def test_sim_try_scroll_count_le_visible(self, make_app):
        """L264: _sim_try_scroll_list returns False when model.count <= visible."""
        from cyberpunk_designer.focus_nav import _sim_try_scroll_list, set_focus

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", _widget_id="nav.item0", text="A"))
        sc.widgets.append(_w(type="button", _widget_id="nav.item1", text="B"))
        sc.widgets.append(_w(type="label", _widget_id="nav.scroll", text="1/2"))
        app.sim_input_mode = True
        set_focus(app, 0)
        result = _sim_try_scroll_list(app, "down")
        assert result is False

    def test_focus_move_direction_gap0_vertical(self, make_app):
        """L412: gap=0 in vertical movement with zero-width widget."""
        from cyberpunk_designer.focus_nav import focus_move_direction, set_focus

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=20, height=20))
        sc.widgets.append(_w(type="button", x=15, y=50, width=0, height=20))
        set_focus(app, 0)
        focus_move_direction(app, "down")

    def test_focus_move_direction_gap0_horizontal(self, make_app):
        """L430: gap=0 in horizontal movement with zero-height widget."""
        from cyberpunk_designer.focus_nav import focus_move_direction, set_focus

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=20, height=20))
        sc.widgets.append(_w(type="button", x=50, y=15, width=20, height=0))
        set_focus(app, 0)
        focus_move_direction(app, "right")

# ---------------------------------------------------------------------------
# transforms.py — L20, L67, L148, L220
# ---------------------------------------------------------------------------

class TestTransformsEdges:
    """Cover uncovered branches in selection_ops/transforms.py."""

    def test_move_selection_locked(self, make_app):
        """L20: move_selection with locked widget."""
        from cyberpunk_designer.selection_ops.transforms import move_selection

        app = make_app(widgets=[_w(locked=True)])
        app.state.selected = [0]
        move_selection(app, 8, 0)

    def test_resize_selection_locked(self, make_app):
        """L67: resize_selection_to with locked widget."""
        from cyberpunk_designer.selection_ops.transforms import resize_selection_to

        app = make_app(widgets=[_w(locked=True, width=40, height=20)])
        app.state.selected = [0]
        assert resize_selection_to(app, 80, 40) is False

    def test_mirror_selection_bounds_none(self, make_app):
        """L148: mirror_selection with OOB indices → bounds is None."""
        from cyberpunk_designer.selection_ops.transforms import mirror_selection

        app = make_app()
        app.state.selected = [999]
        mirror_selection(app, "h")

    def test_make_full_height_locked(self, make_app):
        """L220: make_full_height with locked widget."""
        from cyberpunk_designer.selection_ops.transforms import make_full_height

        app = make_app(widgets=[_w(locked=True)])
        app.state.selected = [0]
        make_full_height(app)

    def test_make_full_width_locked(self, make_app):
        from cyberpunk_designer.selection_ops.transforms import make_full_width

        app = make_app(widgets=[_w(locked=True)])
        app.state.selected = [0]
        make_full_width(app)

# ---------------------------------------------------------------------------
# layout.py (selection_ops) — L280, L283-284, L317, L321-322, L347, L351-352,
# L375, L418, L433, L452, L467
# ---------------------------------------------------------------------------

class TestLayoutEdges:
    """Cover uncovered branches in selection_ops/layout.py."""

    def test_auto_flow_layout_oob(self, make_app):
        """L280: auto_flow_layout with OOB indices."""
        from cyberpunk_designer.selection_ops.layout import auto_flow_layout

        app = make_app()
        app.state.selected = [999, 1000]
        auto_flow_layout(app)

    def test_auto_flow_layout_save_raise(self, make_app):
        """L283-284: auto_flow_layout _save_state exception."""
        from cyberpunk_designer.selection_ops.layout import auto_flow_layout

        app = make_app(widgets=[_w(x=0), _w(x=40)])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        auto_flow_layout(app)

    def test_space_evenly_h_oob(self, make_app):
        """L317: filtered < 3."""
        from cyberpunk_designer.selection_ops.layout import space_evenly_h

        app = make_app(widgets=[_w()])
        app.state.selected = [0, 999, 1000]
        space_evenly_h(app)

    def test_space_evenly_h_save_raise(self, make_app):
        """L321-322"""
        from cyberpunk_designer.selection_ops.layout import space_evenly_h

        app = make_app(
            widgets=[_w(x=0), _w(x=40), _w(x=80)],
        )
        app.state.selected = [0, 1, 2]
        _make_save_raise(app)
        space_evenly_h(app)

    def test_space_evenly_v_oob(self, make_app):
        """L347"""
        from cyberpunk_designer.selection_ops.layout import space_evenly_v

        app = make_app(widgets=[_w()])
        app.state.selected = [0, 999, 1000]
        space_evenly_v(app)

    def test_space_evenly_v_save_raise(self, make_app):
        """L351-352"""
        from cyberpunk_designer.selection_ops.layout import space_evenly_v

        app = make_app(
            widgets=[_w(y=0), _w(y=40), _w(y=80)],
        )
        app.state.selected = [0, 1, 2]
        _make_save_raise(app)
        space_evenly_v(app)

    def test_shrink_to_content_no_children(self, make_app):
        """L375"""
        from cyberpunk_designer.selection_ops.layout import shrink_to_content

        app = make_app(
            widgets=[_w(type="panel", x=0, y=0, width=100, height=100)],
        )
        app.state.selected = [0]
        shrink_to_content(app)

    def test_distribute_columns_oob(self, make_app):
        """L418"""
        from cyberpunk_designer.selection_ops.layout import distribute_columns

        app = make_app()
        app.state.selected = [999, 1000]
        distribute_columns(app)

    def test_distribute_columns_oob_widget(self, make_app):
        """L433"""
        from cyberpunk_designer.selection_ops.layout import distribute_columns

        app = make_app(widgets=[_w(x=0), _w(x=40)])
        app.state.selected = [0, 1, 999]
        distribute_columns(app)

    def test_distribute_rows_oob(self, make_app):
        """L452"""
        from cyberpunk_designer.selection_ops.layout import distribute_rows

        app = make_app()
        app.state.selected = [999, 1000]
        distribute_rows(app)

    def test_distribute_rows_oob_widget(self, make_app):
        """L467"""
        from cyberpunk_designer.selection_ops.layout import distribute_rows

        app = make_app(widgets=[_w(y=0), _w(y=40)])
        app.state.selected = [0, 1, 999]
        distribute_rows(app)

# ---------------------------------------------------------------------------
# batch_ops.py — empty scene, locked, OOB, and save_state guards
# ---------------------------------------------------------------------------

class TestBatchOpsEmptyAndLocked:
    """Cover empty/locked guards in batch_ops.py."""

    def test_reset_to_defaults_locked(self, make_app):
        """L64"""
        from cyberpunk_designer.selection_ops import reset_to_defaults

        app = make_app(widgets=[_w(locked=True)])
        app.state.selected = [0]
        reset_to_defaults(app)

    def test_widget_info_oob(self, make_app):
        """L98"""
        from cyberpunk_designer.selection_ops import widget_info

        app = make_app()
        app.state.selected = [999]
        widget_info(app)

    def test_reset_to_defaults_oob(self, make_app):
        from cyberpunk_designer.selection_ops import reset_to_defaults

        app = make_app()
        app.state.selected = [999]
        reset_to_defaults(app)

    def test_remove_degenerate_empty(self, make_app):
        """L358"""
        from cyberpunk_designer.selection_ops import remove_degenerate_widgets

        app = make_app()
        app.state.current_scene().widgets.clear()
        remove_degenerate_widgets(app)

    def test_enable_all_empty(self, make_app):
        """L385"""
        from cyberpunk_designer.selection_ops import enable_all_widgets

        app = make_app()
        app.state.current_scene().widgets.clear()
        enable_all_widgets(app)

class TestBatchOpsSaveRaise:
    """Cover _save_state exception branches in batch_ops."""

    def _app1(self, make_app, **kw):
        app = make_app(widgets=[_w(**kw)])
        app.state.selected = [0]
        _make_save_raise(app)
        return app

    def _app2(self, make_app):
        app = make_app(widgets=[_w(x=0), _w(x=40)])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        return app

    def test_reset_to_defaults(self, make_app):
        from cyberpunk_designer.selection_ops import reset_to_defaults

        reset_to_defaults(self._app1(make_app))

    def test_flatten_z_indices(self, make_app):
        """L503"""
        from cyberpunk_designer.selection_ops import flatten_z_indices

        flatten_z_indices(self._app2(make_app))

    def test_reverse_widget_order(self, make_app):
        """L533"""
        from cyberpunk_designer.selection_ops import reverse_widget_order

        reverse_widget_order(self._app2(make_app))

    def test_normalize_sizes(self, make_app):
        """L555"""
        from cyberpunk_designer.selection_ops import normalize_sizes

        normalize_sizes(self._app2(make_app))

    def test_increment_text(self, make_app):
        from cyberpunk_designer.selection_ops import increment_text

        increment_text(self._app1(make_app, text="Item 1"))

    def test_replace_text(self, make_app):
        """L710"""
        from cyberpunk_designer.selection_ops import replace_text_in_scene

        app = make_app(widgets=[_w(text="hello")])
        _make_save_raise(app)
        # First call: sets _replace_buf
        replace_text_in_scene(app)
        # Set buffer and call again to hit the save_state except branch
        app._replace_buf = "hello|goodbye"
        replace_text_in_scene(app)

    def test_remove_degenerate(self, make_app):
        """L369"""
        from cyberpunk_designer.selection_ops import remove_degenerate_widgets

        app = make_app(widgets=[_w(width=0, height=0)])
        _make_save_raise(app)
        remove_degenerate_widgets(app)

    def test_auto_rename(self, make_app):
        from cyberpunk_designer.selection_ops import auto_rename

        auto_rename(self._app1(make_app, text="hello"))

    def test_enable_all(self, make_app):
        from cyberpunk_designer.selection_ops import enable_all_widgets

        app = make_app(widgets=[_w(enabled=False)])
        _make_save_raise(app)
        enable_all_widgets(app)

class TestBatchOpsOobGuards:
    """Cover OOB index continue/return guards in batch_ops."""

    def test_snap_sizes_oob(self, make_app):
        """L434"""
        from cyberpunk_designer.selection_ops import snap_sizes_to_grid

        app = make_app(widgets=[_w(width=37)])
        app.state.selected = [0, 999]
        snap_sizes_to_grid(app)

    def test_reverse_widget_order_oob(self, make_app):
        """L530"""
        from cyberpunk_designer.selection_ops import reverse_widget_order

        app = make_app(widgets=[_w()])
        app.state.selected = [0, 999]
        reverse_widget_order(app)

    def test_normalize_sizes_oob(self, make_app):
        """L552"""
        from cyberpunk_designer.selection_ops import normalize_sizes

        app = make_app(widgets=[_w()])
        app.state.selected = [0, 999]
        normalize_sizes(app)

    def test_increment_text_oob(self, make_app):
        """L626"""
        from cyberpunk_designer.selection_ops import increment_text

        app = make_app()
        app.state.selected = [999]
        increment_text(app)

    def test_measure_selection_oob(self, make_app):
        """L652"""
        from cyberpunk_designer.selection_ops import measure_selection

        app = make_app()
        app.state.selected = [999]
        measure_selection(app)

    def test_zoom_to_selection_oob(self, make_app):
        """L730"""
        from cyberpunk_designer.selection_ops import zoom_to_selection

        app = make_app()
        app.state.selected = [999]
        zoom_to_selection(app)

    def test_zoom_to_selection_no_layout(self, make_app):
        """L742"""
        from cyberpunk_designer.selection_ops import zoom_to_selection

        app = make_app(widgets=[_w()])
        app.state.selected = [0]
        app.layout = None
        zoom_to_selection(app)

    def test_inset_widgets_oob(self, make_app):
        """L841"""
        from cyberpunk_designer.selection_ops import inset_widgets

        app = make_app(widgets=[_w()])
        app.state.selected = [0, 999]
        inset_widgets(app)

    def test_outset_widgets_oob(self, make_app):
        """L868"""
        from cyberpunk_designer.selection_ops import outset_widgets

        app = make_app(widgets=[_w()])
        app.state.selected = [0, 999]
        outset_widgets(app)

    def test_tile_fill_scene_oob(self, make_app):
        """L931"""
        from cyberpunk_designer.selection_ops import tile_fill_scene

        app = make_app()
        app.state.selected = [999]
        tile_fill_scene(app)

    def test_match_first_width_oob(self, make_app):
        """L968"""
        from cyberpunk_designer.selection_ops import match_first_width

        app = make_app()
        app.state.selected = [999, 1000]
        match_first_width(app)

    def test_match_first_height_oob(self, make_app):
        """L988"""
        from cyberpunk_designer.selection_ops import match_first_height

        app = make_app()
        app.state.selected = [999, 1000]
        match_first_height(app)

    def test_scatter_random_oob(self, make_app):
        """L1011"""
        from cyberpunk_designer.selection_ops import scatter_random

        app = make_app(widgets=[_w()])
        app.state.selected = [0, 999]
        scatter_random(app)

    def test_toggle_all_checked_oob(self, make_app):
        """L1034"""
        from cyberpunk_designer.selection_ops import toggle_all_checked

        app = make_app(widgets=[_w(type="checkbox")])
        app.state.selected = [0, 999]
        toggle_all_checked(app)

    def test_reset_all_values_oob(self, make_app):
        """L1058"""
        from cyberpunk_designer.selection_ops import reset_all_values

        app = make_app(widgets=[_w(type="slider", value=50)])
        app.state.selected = [0, 999]
        reset_all_values(app)

    def test_clone_to_grid_oob(self, make_app):
        """L1132"""
        from cyberpunk_designer.selection_ops import clone_to_grid

        app = make_app()
        app.state.selected = [999]
        clone_to_grid(app)

    def test_clamp_to_scene_oob(self, make_app):
        """L1182"""
        from cyberpunk_designer.selection_ops import clamp_to_scene

        app = make_app(widgets=[_w()])
        app.state.selected = [0, 999]
        clamp_to_scene(app)

    def test_snap_all_to_grid_oob(self, make_app):
        """L1215"""
        from cyberpunk_designer.selection_ops import snap_all_to_grid

        app = make_app(widgets=[_w()])
        app.state.selected = [0, 999]
        snap_all_to_grid(app)

    def test_size_to_text_oob(self, make_app):
        """L1237"""
        from cyberpunk_designer.selection_ops import size_to_text

        app = make_app(widgets=[_w()])
        app.state.selected = [0, 999]
        size_to_text(app)

    def test_fill_parent_oob(self, make_app):
        """L1264"""
        from cyberpunk_designer.selection_ops import fill_parent

        app = make_app(widgets=[_w()])
        app.state.selected = [0, 999]
        fill_parent(app)

    def test_fill_parent_no_panel(self, make_app):
        """L1275: no enclosing panel found."""
        from cyberpunk_designer.selection_ops import fill_parent

        app = make_app(
            widgets=[_w(x=10, y=10, width=20, height=20)],
        )
        app.state.selected = [0]
        fill_parent(app)

    def test_clear_all_text_oob(self, make_app):
        """L1308"""
        from cyberpunk_designer.selection_ops import clear_all_text

        app = make_app(widgets=[_w()])
        app.state.selected = [0, 999]
        clear_all_text(app)

    def test_reset_padding_oob(self, make_app):
        """L1373"""
        from cyberpunk_designer.selection_ops import reset_padding

        app = make_app(widgets=[_w()])
        app.state.selected = [0, 999]
        reset_padding(app)

    def test_reset_colors_oob(self, make_app):
        """L1396"""
        from cyberpunk_designer.selection_ops import reset_colors

        app = make_app(widgets=[_w()])
        app.state.selected = [0, 999]
        reset_colors(app)
