"""Extended tests for cyberpunk_designer/drawing/toolbar.py — targeting
uncovered lines to push coverage from 77% to 90%+."""

from __future__ import annotations

import pygame

from cyberpunk_designer.drawing.toolbar import draw_scene_tabs, draw_toolbar
from cyberpunk_editor import CyberpunkEditorApp
from ui_designer import SceneConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    return CyberpunkEditorApp(json_path, (256, 128))


# ---------------------------------------------------------------------------
# draw_scene_tabs — zero-height tabs rect (line 34)
# ---------------------------------------------------------------------------


class TestDrawSceneTabsEdgeCases:
    def test_zero_height_tabs_rect(self, tmp_path, monkeypatch):
        """scene_tabs_rect with height=0 → early return (line 34)."""
        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(
            type(app.layout), "scene_tabs_rect", property(lambda self: pygame.Rect(0, 0, 256, 0))
        )
        draw_scene_tabs(app)

    def test_empty_names_noop(self, tmp_path, monkeypatch):
        """No scenes → early return (line 54)."""
        app = _make_app(tmp_path, monkeypatch)
        app.designer.scenes.clear()
        draw_scene_tabs(app)


# ---------------------------------------------------------------------------
# draw_scene_tabs — overflow with many scenes (lines 96-128)
# ---------------------------------------------------------------------------


class TestDrawSceneTabsOverflow:
    def test_many_scenes_overflow(self, tmp_path, monkeypatch):
        """Many scenes cause overflow → scroll arrows drawn (lines 96-128)."""
        app = _make_app(tmp_path, monkeypatch)
        # Add many scenes to force overflow
        for i in range(15):
            name = f"scene_{i:02d}"
            app.designer.scenes[name] = SceneConfig(
                name=name,
                width=256,
                height=128,
                widgets=[],
            )
        draw_scene_tabs(app)
        # Should have scroll arrow hitboxes
        assert len(app.tab_scroll_hitboxes) == 2  # left and right arrows

    def test_scroll_left(self, tmp_path, monkeypatch):
        """Scrolled tabs → left arrow active."""
        app = _make_app(tmp_path, monkeypatch)
        for i in range(15):
            name = f"scene_{i:02d}"
            app.designer.scenes[name] = SceneConfig(
                name=name,
                width=256,
                height=128,
                widgets=[],
            )
        app._tab_scroll = 50  # Pre-scroll
        draw_scene_tabs(app)
        assert len(app.tab_scroll_hitboxes) >= 2

    def test_scroll_to_active_tab(self, tmp_path, monkeypatch):
        """Active tab not visible → auto-scrolls."""
        app = _make_app(tmp_path, monkeypatch)
        for i in range(15):
            name = f"scene_{i:02d}"
            app.designer.scenes[name] = SceneConfig(
                name=name,
                width=256,
                height=128,
                widgets=[],
            )
        # Set current scene to a far scene
        app.designer.current_scene = "scene_14"
        draw_scene_tabs(app)
        # Auto-scroll should have adjusted _tab_scroll
        assert app._tab_scroll > 0


# ---------------------------------------------------------------------------
# draw_scene_tabs — tab drag indicator (lines 186-195)
# ---------------------------------------------------------------------------


class TestDrawSceneTabsDrag:
    def test_tab_drag_indicator(self, tmp_path, monkeypatch):
        """Dragging a tab draws cyan underline (lines 186-195)."""
        app = _make_app(tmp_path, monkeypatch)
        # Add a second scene so multi=True
        app.designer.scenes["second"] = SceneConfig(
            name="second",
            width=256,
            height=128,
            widgets=[],
        )
        draw_scene_tabs(app)
        # Now set drag state and redraw
        app._tab_drag_idx = 0
        draw_scene_tabs(app)

    def test_tab_drag_invalid_idx(self, tmp_path, monkeypatch):
        """Dragging with non-matching index → no crash."""
        app = _make_app(tmp_path, monkeypatch)
        app._tab_drag_idx = 999
        draw_scene_tabs(app)


# ---------------------------------------------------------------------------
# draw_scene_tabs — dirty scenes
# ---------------------------------------------------------------------------


class TestDrawSceneTabsDirty:
    def test_dirty_scene_marker(self, tmp_path, monkeypatch):
        """Dirty scenes show * prefix."""
        app = _make_app(tmp_path, monkeypatch)
        scene_name = app.designer.current_scene
        app._dirty_scenes = {scene_name}
        draw_scene_tabs(app)

    def test_close_buttons(self, tmp_path, monkeypatch):
        """Multiple scenes show close buttons."""
        app = _make_app(tmp_path, monkeypatch)
        app.designer.scenes["second"] = SceneConfig(
            name="second",
            width=256,
            height=128,
            widgets=[],
        )
        draw_scene_tabs(app)
        assert len(app.tab_close_hitboxes) >= 1


# ---------------------------------------------------------------------------
# draw_toolbar
# ---------------------------------------------------------------------------


class TestDrawToolbar:
    def test_basic_draw(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_toolbar(app)
        assert len(app.toolbar_hitboxes) > 0
