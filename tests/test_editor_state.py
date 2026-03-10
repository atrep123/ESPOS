"""Tests for cyberpunk_designer/state.py — EditorState class."""

from __future__ import annotations

from unittest.mock import MagicMock

import pygame

from cyberpunk_designer.state import EditorState
from ui_designer import UIDesigner, WidgetConfig


def _designer_with_widgets(*widgets: WidgetConfig) -> UIDesigner:
    d = UIDesigner(256, 128)
    d.create_scene("main")
    for w in widgets:
        d.scenes["main"].widgets.append(w)
    return d


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=20, height=10, text="t")
    defaults.update(kw)
    return WidgetConfig(**defaults)


class TestEditorStateInit:
    def test_initial_state(self):
        d = _designer_with_widgets()
        layout = MagicMock()
        s = EditorState(d, layout)
        assert s.selected_idx is None
        assert s.selected == []
        assert s.dragging is False
        assert s.resizing is False
        assert s.input_mode is False
        assert s.input_buffer == ""
        assert s.inspector_selected_field is None


class TestCurrentScene:
    def test_returns_scene(self):
        d = _designer_with_widgets(_w(text="hello"))
        s = EditorState(d, MagicMock())
        sc = s.current_scene()
        assert sc.name == "main"
        assert len(sc.widgets) == 1


class TestSelectedWidget:
    def test_returns_none_when_no_selection(self):
        d = _designer_with_widgets(_w())
        s = EditorState(d, MagicMock())
        assert s.selected_widget() is None

    def test_returns_widget(self):
        w = _w(text="picked")
        d = _designer_with_widgets(w)
        s = EditorState(d, MagicMock())
        s.selected_idx = 0
        assert s.selected_widget() is w

    def test_out_of_range_returns_none(self):
        d = _designer_with_widgets(_w())
        s = EditorState(d, MagicMock())
        s.selected_idx = 99
        assert s.selected_widget() is None


class TestHitTest:
    def test_hit(self):
        d = _designer_with_widgets(_w(x=10, y=10, width=30, height=20))
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(0, 0, 256, 128)
        result = s.hit_test_at((20, 20), origin)
        assert result == 0

    def test_miss(self):
        d = _designer_with_widgets(_w(x=10, y=10, width=30, height=20))
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(0, 0, 256, 128)
        result = s.hit_test_at((200, 200), origin)
        assert result is None

    def test_topmost_wins(self):
        w1 = _w(x=0, y=0, width=50, height=50, text="bottom")
        w2 = _w(x=0, y=0, width=50, height=50, text="top")
        d = _designer_with_widgets(w1, w2)
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(0, 0, 256, 128)
        result = s.hit_test_at((10, 10), origin)
        assert result == 1  # last in list = topmost

    def test_invisible_skipped(self):
        d = _designer_with_widgets(_w(x=0, y=0, width=50, height=50, visible=False))
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(0, 0, 256, 128)
        assert s.hit_test_at((10, 10), origin) is None


class TestSelectAt:
    def test_selects_hit(self):
        d = _designer_with_widgets(_w(x=0, y=0, width=50, height=50))
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(0, 0, 256, 128)
        result = s.select_at((10, 10), origin)
        assert result == 0
        assert s.selected_idx == 0
        assert s.selected == [0]
        assert d.selected_widget == 0

    def test_selects_nothing_on_miss(self):
        d = _designer_with_widgets(_w(x=0, y=0, width=10, height=10))
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(0, 0, 256, 128)
        result = s.select_at((200, 200), origin)
        assert result is None
        assert s.selected_idx is None
        assert s.selected == []
