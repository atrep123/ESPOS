"""Tests for cyberpunk_designer/component_insert.py — _existing_roots,
_unique_root, and add_component."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pygame

from cyberpunk_designer.component_insert import (
    _existing_roots,
    _unique_root,
    add_component,
)
from cyberpunk_designer.state import EditorState
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=20, height=10, text="w")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _scene(widgets=None):
    return SimpleNamespace(
        widgets=list(widgets or []),
        width=256,
        height=128,
    )


def _app(widgets=None):
    designer = UIDesigner(256, 128)
    designer.create_scene("main")
    sc = designer.scenes["main"]
    for w in widgets or []:
        sc.widgets.append(w)

    layout = MagicMock()
    layout.canvas_rect = pygame.Rect(0, 0, 256, 128)
    state = EditorState(designer, layout)

    app = SimpleNamespace(
        designer=designer,
        state=state,
        snap_enabled=False,
        pointer_pos=(50, 50),
        scene_rect=pygame.Rect(0, 0, 256, 128),
        layout=layout,
        _dirty=False,
        _set_status=MagicMock(),
        _mark_dirty=lambda: setattr(app, "_dirty", True),
        _set_selection=MagicMock(),
        _auto_complete_widget=MagicMock(),
        _next_group_name=lambda prefix: f"{prefix}1",
    )
    app._mark_dirty = lambda: setattr(app, "_dirty", True)
    return app


# ---------------------------------------------------------------------------
# _existing_roots
# ---------------------------------------------------------------------------


class TestExistingRoots:
    def test_basic(self):
        sc = _scene(
            [
                _w(_widget_id="card.title"),
                _w(_widget_id="card.value"),
                _w(_widget_id="toast.message"),
            ]
        )
        roots = _existing_roots(sc)
        assert roots == {"card", "toast"}

    def test_no_widget_ids(self):
        sc = _scene([_w(), _w()])
        assert _existing_roots(sc) == set()

    def test_empty(self):
        sc = _scene([])
        assert _existing_roots(sc) == set()

    def test_root_only(self):
        sc = _scene([_w(_widget_id="mymenu")])
        assert _existing_roots(sc) == {"mymenu"}


# ---------------------------------------------------------------------------
# _unique_root
# ---------------------------------------------------------------------------


class TestUniqueRoot:
    def test_no_collision(self):
        sc = _scene([_w(_widget_id="card.title")])
        assert _unique_root(sc, "toast") == "toast"

    def test_collision(self):
        sc = _scene([_w(_widget_id="card.title")])
        assert _unique_root(sc, "card") == "card_2"

    def test_multiple_collisions(self):
        sc = _scene(
            [
                _w(_widget_id="card.title"),
                _w(_widget_id="card_2.title"),
            ]
        )
        assert _unique_root(sc, "card") == "card_3"

    def test_empty_base(self):
        sc = _scene([_w(_widget_id="card.title")])
        assert _unique_root(sc, "") == ""

    def test_empty_scene(self):
        sc = _scene([])
        assert _unique_root(sc, "card") == "card"


# ---------------------------------------------------------------------------
# add_component
# ---------------------------------------------------------------------------


class TestAddComponent:
    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_inserts_widgets(self, mock_bp):
        mock_bp.return_value = [
            {
                "type": "panel",
                "role": "panel",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 50,
                "text": "",
            },
            {
                "type": "label",
                "role": "title",
                "x": 2,
                "y": 2,
                "width": 96,
                "height": 10,
                "text": "Hello",
            },
        ]
        app = _app()
        add_component(app, "card")
        sc = app.state.current_scene()
        assert len(sc.widgets) == 2
        assert app._dirty

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_unknown_component(self, mock_bp):
        mock_bp.return_value = []
        app = _app()
        add_component(app, "nonexistent")
        app._set_status.assert_called()
        assert not app._dirty

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_unique_root_on_collision(self, mock_bp):
        mock_bp.return_value = [
            {
                "type": "label",
                "role": "title",
                "x": 0,
                "y": 0,
                "width": 50,
                "height": 10,
                "text": "T",
            },
        ]
        # Pre-populate with a card root
        app = _app([_w(_widget_id="card.title")])
        add_component(app, "card")
        sc = app.state.current_scene()
        # New widget should have card_2 root
        new_w = sc.widgets[-1]
        assert new_w._widget_id == "card_2.title"

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_snap_enabled(self, mock_bp):
        mock_bp.return_value = [
            {"type": "panel", "role": "bg", "x": 0, "y": 0, "width": 50, "height": 30, "text": ""},
        ]
        app = _app()
        app.snap_enabled = True
        add_component(app, "test")
        sc = app.state.current_scene()
        w = sc.widgets[-1]
        assert w.x % 8 == 0
        assert w.y % 8 == 0


# ---------------------------------------------------------------------------
# AT: Extended component insert tests — modal, multi-widget, error paths
# ---------------------------------------------------------------------------


class TestAddComponentModal:
    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_modal_origin_at_zero(self, mock_bp):
        """Modal component type starts at origin (0, 0)."""
        mock_bp.return_value = [
            {
                "type": "panel",
                "role": "bg",
                "x": 0,
                "y": 0,
                "width": 256,
                "height": 128,
                "text": "",
            },
            {
                "type": "label",
                "role": "title",
                "x": 10,
                "y": 10,
                "width": 100,
                "height": 12,
                "text": "Modal",
            },
        ]
        app = _app()
        add_component(app, "modal")
        sc = app.state.current_scene()
        bg = sc.widgets[-2]
        assert bg.x == 0
        assert bg.y == 0

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_many_widgets_in_component(self, mock_bp):
        """Component with many blueprint widgets inserts all of them."""
        bps = [
            {
                "type": "label",
                "role": f"item{i}",
                "x": 0,
                "y": i * 12,
                "width": 80,
                "height": 10,
                "text": f"Item {i}",
            }
            for i in range(10)
        ]
        mock_bp.return_value = bps
        app = _app()
        add_component(app, "big_list")
        sc = app.state.current_scene()
        assert len(sc.widgets) == 10
        assert app._dirty

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_z_index_stacks_on_existing(self, mock_bp):
        """New component z_index stacks above existing widgets."""
        mock_bp.return_value = [
            {
                "type": "label",
                "role": "top",
                "x": 0,
                "y": 0,
                "width": 50,
                "height": 10,
                "text": "T",
                "z": 2,
            },
        ]
        existing = _w(z_index=5)
        app = _app([existing])
        add_component(app, "overlay")
        sc = app.state.current_scene()
        new_w = sc.widgets[-1]
        assert new_w.z_index == 5 + 2

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_auto_complete_called(self, mock_bp):
        """_auto_complete_widget is called for each inserted widget."""
        mock_bp.return_value = [
            {
                "type": "label",
                "role": "a",
                "x": 0,
                "y": 0,
                "width": 30,
                "height": 10,
                "text": "A",
            },
            {
                "type": "label",
                "role": "b",
                "x": 0,
                "y": 12,
                "width": 30,
                "height": 10,
                "text": "B",
            },
        ]
        app = _app()
        add_component(app, "pair")
        assert app._auto_complete_widget.call_count == 2

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_blueprint_construction_error_skipped(self, mock_bp):
        """Widget construction failure (bad field) is silently skipped."""
        mock_bp.return_value = [
            {
                "type": "label",
                "role": "ok",
                "x": 0,
                "y": 0,
                "width": 30,
                "height": 10,
                "text": "OK",
            },
            {
                "type": "label",
                "role": "bad",
                "x": 0,
                "y": 0,
                "width": 30,
                "height": 10,
                "text": "Bad",
                "value": "not_int",  # Will cause ValueError in int() conversion
            },
        ]
        app = _app()
        add_component(app, "mixed")
        sc = app.state.current_scene()
        # Only valid widget inserted
        assert len(sc.widgets) == 1
        assert app._dirty

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_all_bad_blueprints_shows_failure(self, mock_bp):
        """When all blueprints fail, status shows failure."""
        mock_bp.return_value = [
            {
                "type": "label",
                "role": "bad",
                "x": 0,
                "y": 0,
                "width": 30,
                "height": 10,
                "text": "B",
                "value": "invalid",  # causes ValueError in int()
            },
        ]
        app = _app()
        add_component(app, "broken")
        app._set_status.assert_called()
        call_args = app._set_status.call_args[0][0]
        assert "failed" in call_args.lower()

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_sequential_inserts_unique_roots(self, mock_bp):
        """Two sequential inserts get different root names."""
        mock_bp.return_value = [
            {
                "type": "label",
                "role": "title",
                "x": 0,
                "y": 0,
                "width": 50,
                "height": 10,
                "text": "T",
            },
        ]
        app = _app()
        add_component(app, "card")
        add_component(app, "card")
        sc = app.state.current_scene()
        ids = [w._widget_id for w in sc.widgets]
        assert ids[0] == "card.title"
        assert ids[1] == "card_2.title"

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_widget_clamped_to_scene_bounds(self, mock_bp):
        """Widget positions are clamped to scene boundaries."""
        mock_bp.return_value = [
            {
                "type": "panel",
                "role": "bg",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 50,
                "text": "",
            },
        ]
        app = _app()
        # Pointer way outside scene rect → should be clamped
        app.pointer_pos = (5000, 5000)
        add_component(app, "test")
        sc = app.state.current_scene()
        w = sc.widgets[-1]
        assert w.x + w.width <= sc.width
        assert w.y + w.height <= sc.height


# ===================================================================
# BE – empty blueprints guard & edge cases
# ===================================================================


class TestEmptyBlueprintsGuard:
    """The min/max bounds calculation is guarded against empty blueprints."""

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_empty_blueprints_returns_early(self, mock_bp):
        """If component_blueprints returns [], no crash."""
        mock_bp.return_value = []
        app = _app()
        add_component(app, "empty_comp")
        app._set_status.assert_called()
        assert "not found" in app._set_status.call_args[0][0].lower()

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_single_blueprint_widget(self, mock_bp):
        """A component with exactly one blueprint widget works."""
        mock_bp.return_value = [
            {
                "type": "label",
                "role": "only",
                "x": 0,
                "y": 0,
                "width": 50,
                "height": 20,
                "text": "Solo",
            },
        ]
        app = _app()
        add_component(app, "solo")
        sc = app.state.current_scene()
        assert len(sc.widgets) == 1
        assert sc.widgets[0].text == "Solo"

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_z_index_on_empty_scene(self, mock_bp):
        """Inserting into an empty scene: base_z=0, no crash."""
        mock_bp.return_value = [
            {
                "type": "label",
                "role": "item",
                "x": 0,
                "y": 0,
                "width": 30,
                "height": 10,
                "text": "Z",
                "z": 5,
            },
        ]
        app = _app()
        assert len(app.state.current_scene().widgets) == 0
        add_component(app, "ztest")
        w = app.state.current_scene().widgets[0]
        assert w.z_index == 5  # base_z(0) + z(5)

    @patch("cyberpunk_designer.component_insert.component_blueprints")
    def test_negative_xy_in_blueprint(self, mock_bp):
        """Blueprint with negative x/y coords → clamped to 0."""
        mock_bp.return_value = [
            {
                "type": "panel",
                "role": "bg",
                "x": -10,
                "y": -20,
                "width": 40,
                "height": 30,
                "text": "",
            },
        ]
        app = _app()
        add_component(app, "neg")
        w = app.state.current_scene().widgets[0]
        assert w.x >= 0
        assert w.y >= 0
