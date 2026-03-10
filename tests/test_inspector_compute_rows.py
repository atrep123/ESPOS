"""Tests for compute_inspector_rows in cyberpunk_designer/inspector_logic.py.

Covers the three main paths: no selection, single widget, multi-selection.
"""

from types import SimpleNamespace
from typing import List, Optional
from unittest.mock import MagicMock

import pygame

from cyberpunk_designer.inspector_logic import compute_inspector_rows
from cyberpunk_designer.selection_ops import selection_bounds, set_selection
from cyberpunk_designer.state import EditorState
from ui_designer import UIDesigner, WidgetConfig


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=40, height=12, text="hi")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _app(widgets: Optional[List[WidgetConfig]] = None,
         profile: str = "esp32os_256x128_gray4"):
    designer = UIDesigner(256, 128)
    designer.create_scene("main")
    sc = designer.scenes["main"]
    for w in (widgets or []):
        sc.widgets.append(w)
    layout = MagicMock()
    layout.canvas_rect = pygame.Rect(0, 0, 256, 128)
    state = EditorState(designer, layout)
    app = SimpleNamespace(
        designer=designer,
        state=state,
        hardware_profile=profile,
        snap_enabled=False,
        show_grid=False,
        panels_collapsed=False,
        live_preview_port=None,
        live_preview_baud=0,
        clipboard=[],
        layout=layout,
        _mark_dirty=MagicMock(),
        _set_status=MagicMock(),
        _selection_bounds=lambda indices: selection_bounds(app, indices),
        _set_selection=lambda indices, anchor_idx=None: set_selection(app, indices, anchor_idx),
        _selected_component_group=lambda: None,
        _selected_group_exact=lambda: None,
        _primary_group_for_index=lambda idx: None,
        _group_members=lambda name: [],
        _tri_state=lambda vals: "True" if all(vals) else ("False" if not any(vals) else "(mixed)"),
        _component_role_index=lambda members, root: {},
        _component_field_specs=lambda ctype: {},
    )
    return app


class TestNoSelection:
    def test_has_info_section(self):
        app = _app([])
        rows, warning, w = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert "_section:Info" in keys
        assert "profile" in keys
        assert "resources" in keys

    def test_returns_none_widget(self):
        app = _app([])
        rows, warning, w = compute_inspector_rows(app)
        assert w is None

    def test_selection_none_row(self):
        app = _app([_w()])
        rows, warning, w = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert "none" in keys


class TestSingleSelection:
    def test_basic_fields(self):
        app = _app([_w(type="label", x=10, y=20, width=40, height=12, text="hello")])
        set_selection(app, [0])
        rows, warning, w = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert "type" in keys
        assert "x" in keys
        assert "y" in keys
        assert "width" in keys
        assert "height" in keys
        assert "text" in keys
        assert w is not None
        assert w.type == "label"

    def test_type_label_value(self):
        app = _app([_w(type="button")])
        set_selection(app, [0])
        rows, _, _ = compute_inspector_rows(app)
        row_dict = dict(rows)
        assert "button" in row_dict["type"]

    def test_chart_extra_fields(self):
        app = _app([_w(type="chart", data_points=[1, 2, 3], style="bar")])
        set_selection(app, [0])
        rows, _, _ = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert "chart_mode" in keys
        assert "data_points" in keys
        assert "points" in keys

    def test_checkbox_shows_checked(self):
        app = _app([_w(type="checkbox", checked=True)])
        set_selection(app, [0])
        rows, _, _ = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert "checked" in keys

    def test_slider_shows_value(self):
        app = _app([_w(type="slider", value=42, min_value=0, max_value=100)])
        set_selection(app, [0])
        rows, _, _ = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert "value" in keys
        assert "min_value" in keys
        assert "max_value" in keys

    def test_z_index_present(self):
        app = _app([_w(z_index=3)])
        set_selection(app, [0])
        rows, _, _ = compute_inspector_rows(app)
        row_dict = dict(rows)
        assert "3" in row_dict["z_index"]


class TestMultiSelection:
    def test_multi_shows_count(self):
        app = _app([_w(), _w(), _w()])
        set_selection(app, [0, 1, 2])
        rows, _, _ = compute_inspector_rows(app)
        row_dict = dict(rows)
        assert "3" in row_dict.get("selection", "")

    def test_multi_shows_type_multiple(self):
        app = _app([_w(), _w()])
        set_selection(app, [0, 1])
        rows, _, _ = compute_inspector_rows(app)
        row_dict = dict(rows)
        assert "multiple" in row_dict.get("type", "").lower()

    def test_multi_shows_bounds(self):
        app = _app([_w(x=10, y=20, width=30, height=10),
                     _w(x=50, y=60, width=20, height=15)])
        set_selection(app, [0, 1])
        rows, _, _ = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert "x" in keys
        assert "width" in keys

    def test_multi_mixed_colors(self):
        app = _app([_w(color_fg="#aaa"), _w(color_fg="#bbb")])
        set_selection(app, [0, 1])
        rows, _, _ = compute_inspector_rows(app)
        row_dict = dict(rows)
        assert "mixed" in row_dict.get("color_fg", "").lower()

    def test_multi_same_colors(self):
        app = _app([_w(color_fg="#aaa"), _w(color_fg="#aaa")])
        set_selection(app, [0, 1])
        rows, _, _ = compute_inspector_rows(app)
        row_dict = dict(rows)
        assert "#aaa" in row_dict.get("color_fg", "")


class TestInfoSection:
    def test_profile_shown(self):
        app = _app([], profile="esp32os_256x128_gray4")
        rows, _, _ = compute_inspector_rows(app)
        row_dict = dict(rows)
        assert "profile" in row_dict

    def test_no_profile(self):
        app = _app([], profile="")
        rows, _, _ = compute_inspector_rows(app)
        row_dict = dict(rows)
        assert "none" in row_dict.get("profile", "").lower()

    def test_snap_grid_shown(self):
        app = _app([])
        rows, _, _ = compute_inspector_rows(app)
        row_dict = dict(rows)
        assert "snap" in row_dict.get("snapgrid", "").lower()

    def test_live_off(self):
        app = _app([])
        rows, _, _ = compute_inspector_rows(app)
        row_dict = dict(rows)
        assert "off" in row_dict.get("live", "").lower()


class TestLayersSection:
    def test_layers_present_with_widgets(self):
        app = _app([_w(), _w()])
        rows, _, _ = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert "_section:Layers" in keys

    def test_no_layers_when_empty(self):
        app = _app([])
        rows, _, _ = compute_inspector_rows(app)
        keys = [r[0] for r in rows]
        assert "_section:Layers" not in keys
