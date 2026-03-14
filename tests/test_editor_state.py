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


# ===================================================================
# Hit-test edge cases
# ===================================================================


class TestHitTestEdgeCases:
    def test_origin_offset(self):
        """Hit-test accounts for canvas origin offset."""
        d = _designer_with_widgets(_w(x=0, y=0, width=20, height=20))
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(50, 50, 256, 128)
        # Click at (55, 55) → widget-local (5, 5) → hit
        assert s.hit_test_at((55, 55), origin) == 0
        # Click at (10, 10) → outside origin+widget → miss
        assert s.hit_test_at((10, 10), origin) is None

    def test_boundary_exact_corner(self):
        """Click on exact top-left corner of widget → hit."""
        d = _designer_with_widgets(_w(x=10, y=10, width=30, height=20))
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(0, 0, 256, 128)
        assert s.hit_test_at((10, 10), origin) == 0

    def test_boundary_just_outside(self):
        """Click just outside bottom-right corner → miss."""
        d = _designer_with_widgets(_w(x=10, y=10, width=30, height=20))
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(0, 0, 256, 128)
        assert s.hit_test_at((40, 30), origin) is None

    def test_boundary_bottom_right_inside(self):
        """Click at bottom-right edge (just inside) → hit."""
        d = _designer_with_widgets(_w(x=10, y=10, width=30, height=20))
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(0, 0, 256, 128)
        assert s.hit_test_at((39, 29), origin) == 0

    def test_overlapping_z_index_topmost_wins(self):
        """With overlapping widgets, the last in list (topmost) wins."""
        w0 = _w(x=0, y=0, width=100, height=100, text="bottom")
        w1 = _w(x=0, y=0, width=100, height=100, text="middle")
        w2 = _w(x=0, y=0, width=100, height=100, text="top")
        d = _designer_with_widgets(w0, w1, w2)
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(0, 0, 256, 128)
        assert s.hit_test_at((50, 50), origin) == 2  # topmost

    def test_partial_overlap_picks_correct(self):
        """Non-overlapping ends of partially overlapping widgets."""
        w0 = _w(x=0, y=0, width=30, height=30, text="left")
        w1 = _w(x=20, y=0, width=30, height=30, text="right")
        d = _designer_with_widgets(w0, w1)
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(0, 0, 256, 128)
        # Overlap region (25, 15) → topmost = w1 (index 1)
        assert s.hit_test_at((25, 15), origin) == 1
        # Only w0 region (5, 15)
        assert s.hit_test_at((5, 15), origin) == 0
        # Only w1 region (45, 15)
        assert s.hit_test_at((45, 15), origin) == 1

    def test_empty_scene(self):
        """Hit-test on empty scene returns None."""
        d = _designer_with_widgets()
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(0, 0, 256, 128)
        assert s.hit_test_at((50, 50), origin) is None

    def test_invisible_among_visible(self):
        """Invisible widget on top is skipped, visible below is hit."""
        w_vis = _w(x=0, y=0, width=50, height=50, visible=True, text="vis")
        w_invis = _w(x=0, y=0, width=50, height=50, visible=False, text="invis")
        d = _designer_with_widgets(w_vis, w_invis)
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(0, 0, 256, 128)
        # w_invis is index 1 (topmost) but invisible → fall through to w_vis
        assert s.hit_test_at((25, 25), origin) == 0


# ===================================================================
# BF – EditorState edge cases
# ===================================================================


class TestSelectedWidgetEdge:
    def test_negative_index_returns_none(self):
        d = _designer_with_widgets(_w())
        s = EditorState(d, MagicMock())
        s.selected_idx = -1
        assert s.selected_widget() is None

    def test_large_index_returns_none(self):
        d = _designer_with_widgets(_w())
        s = EditorState(d, MagicMock())
        s.selected_idx = 999
        assert s.selected_widget() is None

    def test_zero_index_with_widget(self):
        w = _w(text="first")
        d = _designer_with_widgets(w)
        s = EditorState(d, MagicMock())
        s.selected_idx = 0
        assert s.selected_widget() is not None
        assert s.selected_widget().text == "first"

    def test_last_valid_index(self):
        d = _designer_with_widgets(_w(text="a"), _w(text="b"), _w(text="c"))
        s = EditorState(d, MagicMock())
        s.selected_idx = 2
        assert s.selected_widget().text == "c"


class TestSelectAtEdge:
    def test_select_updates_designer_selected_widget(self):
        w = _w(x=0, y=0, width=50, height=50)
        d = _designer_with_widgets(w)
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(0, 0, 256, 128)
        result = s.select_at((25, 25), origin)
        assert result == 0
        assert d.selected_widget == 0

    def test_miss_clears_designer_selected_widget(self):
        d = _designer_with_widgets(_w(x=0, y=0, width=10, height=10))
        s = EditorState(d, MagicMock())
        s.selected_idx = 0
        s.selected = [0]
        d.selected_widget = 0
        origin = pygame.Rect(0, 0, 256, 128)
        result = s.select_at((200, 200), origin)
        assert result is None
        assert s.selected_idx is None
        assert s.selected == []
        assert d.selected_widget is None

    def test_select_with_offset_origin(self):
        """Origin rect shifts the hit-test coordinate space."""
        w = _w(x=0, y=0, width=20, height=20)
        d = _designer_with_widgets(w)
        s = EditorState(d, MagicMock())
        origin = pygame.Rect(100, 100, 256, 128)
        # Widget at (0,0) with origin at (100,100) → screen coords (100,100)-(120,120)
        assert s.select_at((110, 110), origin) == 0
        assert s.select_at((50, 50), origin) is None


class TestInitialDefaults:
    def test_drag_state_defaults(self):
        d = _designer_with_widgets()
        s = EditorState(d, MagicMock())
        assert s.dragging is False
        assert s.resizing is False
        assert s.drag_offset == (0, 0)
        assert s.resize_anchor is None
        assert s.box_select_start is None
        assert s.box_select_rect is None
        assert s.inspector_selected_field is None
        assert s.inspector_input_buffer == ""
        assert s.active_guides == []

    def test_palette_and_inspector_scroll_zero(self):
        d = _designer_with_widgets()
        s = EditorState(d, MagicMock())
        assert s.palette_scroll == 0
        assert s.inspector_scroll == 0
