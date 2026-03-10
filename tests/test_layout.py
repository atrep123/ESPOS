"""Tests for cyberpunk_designer/layout.py Layout class."""

import pygame

from cyberpunk_designer.layout import Layout


class TestLayoutDefaults:
    def test_default_constructor(self):
        lay = Layout(1024, 768)
        assert lay.width == 1024
        assert lay.height == 768
        assert lay.palette_w == 112
        assert lay.inspector_w == 200
        assert lay.toolbar_h == 24
        assert lay.status_h == 18
        assert lay.scene_tabs_h == 0


class TestBodyTop:
    def test_no_tabs(self):
        lay = Layout(800, 600, toolbar_h=24, scene_tabs_h=0)
        assert lay._body_top == 24

    def test_with_tabs(self):
        lay = Layout(800, 600, toolbar_h=24, scene_tabs_h=20)
        assert lay._body_top == 44


class TestToolbarRect:
    def test_full_width(self):
        lay = Layout(1024, 768, toolbar_h=30)
        r = lay.toolbar_rect
        assert r.x == 0
        assert r.y == 0
        assert r.width == 1024
        assert r.height == 30


class TestSceneTabsRect:
    def test_below_toolbar(self):
        lay = Layout(1024, 768, toolbar_h=24, scene_tabs_h=20)
        r = lay.scene_tabs_rect
        assert r.x == 0
        assert r.y == 24
        assert r.width == 1024
        assert r.height == 20

    def test_zero_height(self):
        lay = Layout(800, 600, scene_tabs_h=0)
        r = lay.scene_tabs_rect
        assert r.height == 0


class TestCanvasRect:
    def test_default(self):
        lay = Layout(1024, 768, palette_w=112, inspector_w=200, toolbar_h=24, status_h=18)
        r = lay.canvas_rect
        assert r.x == 112
        assert r.y == 24
        assert r.width == 1024 - 112 - 200  # 712
        assert r.height == 768 - 24 - 18  # 726

    def test_with_tabs(self):
        lay = Layout(1024, 768, palette_w=100, inspector_w=150, toolbar_h=24, status_h=18, scene_tabs_h=20)
        r = lay.canvas_rect
        assert r.x == 100
        assert r.y == 44  # 24 + 20
        assert r.width == 1024 - 100 - 150
        assert r.height == 768 - 44 - 18


class TestPaletteRect:
    def test_left_side(self):
        lay = Layout(800, 600, palette_w=112, toolbar_h=24, status_h=18)
        r = lay.palette_rect
        assert r.x == 0
        assert r.y == 24
        assert r.width == 112
        assert r.height == 600 - 24 - 18


class TestInspectorRect:
    def test_right_side(self):
        lay = Layout(800, 600, inspector_w=200, toolbar_h=24, status_h=18)
        r = lay.inspector_rect
        assert r.x == 600  # 800 - 200
        assert r.y == 24
        assert r.width == 200
        assert r.height == 600 - 24 - 18


class TestStatusRect:
    def test_bottom(self):
        lay = Layout(800, 600, status_h=20)
        r = lay.status_rect
        assert r.x == 0
        assert r.y == 580  # 600 - 20
        assert r.width == 800
        assert r.height == 20


class TestLayoutEdgeCases:
    def test_zero_panels(self):
        lay = Layout(800, 600, palette_w=0, inspector_w=0, toolbar_h=0, status_h=0, scene_tabs_h=0)
        r = lay.canvas_rect
        assert r.x == 0
        assert r.y == 0
        assert r.width == 800
        assert r.height == 600

    def test_all_returns_pygame_rect(self):
        lay = Layout(1024, 768)
        for prop in ("canvas_rect", "palette_rect", "inspector_rect", "toolbar_rect", "scene_tabs_rect", "status_rect"):
            assert isinstance(getattr(lay, prop), pygame.Rect)
