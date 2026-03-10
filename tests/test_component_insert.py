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
