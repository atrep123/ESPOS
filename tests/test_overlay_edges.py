"""Edge-case tests for drawing overlays: context menu, tooltip, help overlay, shortcuts panel.

Covers positioning, clamping, boundary conditions, and the new quick-ref panel.
"""

from __future__ import annotations

import time

import pygame

from cyberpunk_designer.drawing.overlays import (
    draw_context_menu,
    draw_help_overlay,
    draw_shortcuts_panel,
    draw_tooltip,
)
from cyberpunk_editor import CyberpunkEditorApp


def _make_app(tmp_path, monkeypatch, **kw):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    return CyberpunkEditorApp(json_path, (256, 128))


# ---------------------------------------------------------------------------
# draw_context_menu — edge cases
# ---------------------------------------------------------------------------


class TestContextMenuEdgeCases:
    """Positioning, clamping, and content edge-cases for context menu."""

    def test_clamp_top_left_corner(self, tmp_path, monkeypatch):
        """Menu at (0,0) stays within screen bounds."""
        app = _make_app(tmp_path, monkeypatch)
        items = [("Action", "", "act")]
        app._context_menu = {"visible": True, "pos": (0, 0), "items": items}
        draw_context_menu(app)
        rect = app._context_menu.get("rect")
        assert rect is not None
        assert rect.x >= 0 and rect.y >= 0

    def test_clamp_bottom_right_corner(self, tmp_path, monkeypatch):
        """Menu placed at bottom-right corner clamps to fit."""
        app = _make_app(tmp_path, monkeypatch)
        sw = app.logical_surface.get_width()
        sh = app.logical_surface.get_height()
        items = [("Long label text here", "Ctrl+X", "act")]
        app._context_menu = {"visible": True, "pos": (sw, sh), "items": items}
        draw_context_menu(app)
        rect = app._context_menu["rect"]
        assert rect.right <= sw
        assert rect.bottom <= sh

    def test_many_items_tall_menu(self, tmp_path, monkeypatch):
        """Menu with many items renders all hitboxes."""
        app = _make_app(tmp_path, monkeypatch)
        items = [(f"Item {i}", "", f"act_{i}") for i in range(20)]
        app._context_menu = {"visible": True, "pos": (10, 10), "items": items}
        draw_context_menu(app)
        hitboxes = app._context_menu.get("hitboxes", [])
        assert len(hitboxes) == 20

    def test_all_separators(self, tmp_path, monkeypatch):
        """Menu with only separators produces no hitboxes."""
        app = _make_app(tmp_path, monkeypatch)
        items = [("---", "", None), ("---", "", None)]
        app._context_menu = {"visible": True, "pos": (10, 10), "items": items}
        draw_context_menu(app)
        assert app._context_menu.get("hitboxes") == []

    def test_mixed_separators_and_actions(self, tmp_path, monkeypatch):
        """Separators don't count as hitbox items."""
        app = _make_app(tmp_path, monkeypatch)
        items = [
            ("A", "", "a"),
            ("---", "", None),
            ("B", "", "b"),
            ("---", "", None),
            ("C", "", "c"),
        ]
        app._context_menu = {"visible": True, "pos": (5, 5), "items": items}
        draw_context_menu(app)
        assert len(app._context_menu["hitboxes"]) == 3

    def test_not_visible_is_noop(self, tmp_path, monkeypatch):
        """Menu with visible=False is not drawn."""
        app = _make_app(tmp_path, monkeypatch)
        app._context_menu = {"visible": False, "pos": (0, 0), "items": [("X", "", "x")]}
        draw_context_menu(app)
        assert "hitboxes" not in app._context_menu

    def test_no_logical_surface(self, tmp_path, monkeypatch):
        """Missing logical_surface is a no-op."""
        app = _make_app(tmp_path, monkeypatch)
        app._context_menu = {"visible": True, "pos": (0, 0), "items": [("X", "", "x")]}
        app.logical_surface = None
        draw_context_menu(app)
        assert "hitboxes" not in app._context_menu


# ---------------------------------------------------------------------------
# draw_tooltip — edge cases
# ---------------------------------------------------------------------------


class TestTooltipEdgeCases:
    """Tooltip positioning and boundary conditions."""

    def test_tooltip_near_right_edge(self, tmp_path, monkeypatch):
        """Tooltip near right edge shifts left to fit."""
        app = _make_app(tmp_path, monkeypatch)
        app.pointer_down = False
        sw = app.logical_surface.get_width()
        btn_rect = pygame.Rect(sw - 20, 5, 15, 15)
        app.toolbar_hitboxes = [(btn_rect, "save")]
        app.tab_hitboxes = []
        app.pointer_pos = (sw - 10, 10)
        # First call sets timer
        draw_tooltip(app)
        app._tooltip_start = time.time() - 2.0
        # Second call renders — should not crash
        draw_tooltip(app)

    def test_tooltip_near_bottom_edge(self, tmp_path, monkeypatch):
        """Tooltip near bottom edge shifts up."""
        app = _make_app(tmp_path, monkeypatch)
        app.pointer_down = False
        sh = app.logical_surface.get_height()
        btn_rect = pygame.Rect(10, sh - 10, 20, 10)
        app.toolbar_hitboxes = [(btn_rect, "save")]
        app.tab_hitboxes = []
        app.pointer_pos = (15, sh - 5)
        draw_tooltip(app)
        app._tooltip_start = time.time() - 2.0
        draw_tooltip(app)

    def test_tooltip_different_keys_reset_timer(self, tmp_path, monkeypatch):
        """Changing tooltip key restarts the delay timer."""
        app = _make_app(tmp_path, monkeypatch)
        app.pointer_down = False
        btn1 = pygame.Rect(10, 5, 20, 15)
        btn2 = pygame.Rect(40, 5, 20, 15)
        app.toolbar_hitboxes = [(btn1, "save"), (btn2, "load")]
        app.tab_hitboxes = []
        # Hover btn1
        app.pointer_pos = (15, 10)
        draw_tooltip(app)
        key1 = app._tooltip_key
        # Move to btn2
        app.pointer_pos = (45, 10)
        draw_tooltip(app)
        key2 = app._tooltip_key
        assert key1 != key2

    def test_tab_hover_modified_scene(self, tmp_path, monkeypatch):
        """Tab tooltip shows '(modified)' for dirty scenes."""
        app = _make_app(tmp_path, monkeypatch)
        app.pointer_down = False
        sc_name = app.designer.current_scene
        tab_rect = pygame.Rect(10, 10, 50, 16)
        app.toolbar_hitboxes = []
        app.tab_hitboxes = [(tab_rect, 0, sc_name)]
        app._dirty_scenes = {sc_name}
        app.pointer_pos = (30, 15)
        draw_tooltip(app)
        assert "modified" in (app._tooltip_key or "").lower()


# ---------------------------------------------------------------------------
# draw_help_overlay — edge cases
# ---------------------------------------------------------------------------


class TestHelpOverlayEdgeCases:
    """Help overlay boundary and layout conditions."""

    def test_no_layout(self, tmp_path, monkeypatch):
        """Missing layout attribute → no-op."""
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        app.layout = None
        draw_help_overlay(app)

    def test_zero_dimension_layout(self, tmp_path, monkeypatch):
        """Layout with zero width/height → no-op."""
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True

        class ZeroLayout:
            width = 0
            height = 0

        app.layout = ZeroLayout()
        draw_help_overlay(app)

    def test_no_state_current_scene(self, tmp_path, monkeypatch):
        """Help overlay handles missing state.current_scene gracefully."""
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        original = app.state.current_scene
        app.state.current_scene = lambda: None  # type: ignore[assignment]
        draw_help_overlay(app)
        app.state.current_scene = original

    def test_visible_with_widgets(self, tmp_path, monkeypatch):
        """Help overlay draws successfully with widgets in scene."""
        app = _make_app(tmp_path, monkeypatch)
        from ui_designer import WidgetConfig

        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=0, y=0, width=24, height=16, text="w"))
        app.show_help_overlay = True
        draw_help_overlay(app)


# ---------------------------------------------------------------------------
# draw_shortcuts_panel — new quick-ref panel
# ---------------------------------------------------------------------------


class TestShortcutsPanel:
    """Tests for the Ctrl+/ quick-reference shortcuts panel."""

    def test_hidden_by_default(self, tmp_path, monkeypatch):
        """Panel not drawn when show_shortcuts_panel is False."""
        app = _make_app(tmp_path, monkeypatch)
        app.show_shortcuts_panel = False
        draw_shortcuts_panel(app)  # no crash, no-op

    def test_visible(self, tmp_path, monkeypatch):
        """Panel draws when show_shortcuts_panel is True."""
        app = _make_app(tmp_path, monkeypatch)
        app.show_shortcuts_panel = True
        draw_shortcuts_panel(app)  # no crash

    def test_no_surface_noop(self, tmp_path, monkeypatch):
        """Missing logical_surface → no-op."""
        app = _make_app(tmp_path, monkeypatch)
        app.show_shortcuts_panel = True
        app.logical_surface = None
        draw_shortcuts_panel(app)

    def test_no_layout_noop(self, tmp_path, monkeypatch):
        """Missing layout → no-op."""
        app = _make_app(tmp_path, monkeypatch)
        app.show_shortcuts_panel = True
        app.layout = None
        draw_shortcuts_panel(app)

    def test_zero_layout_noop(self, tmp_path, monkeypatch):
        """Zero-dimension layout → no-op."""
        app = _make_app(tmp_path, monkeypatch)
        app.show_shortcuts_panel = True

        class ZeroLayout:
            width = 0
            height = 0

        app.layout = ZeroLayout()
        draw_shortcuts_panel(app)

    def test_toggle_keybind(self, tmp_path, monkeypatch):
        """Ctrl+/ toggles panel on and off."""
        app = _make_app(tmp_path, monkeypatch)
        assert not app.show_shortcuts_panel
        from cyberpunk_designer.key_handlers import on_key_down

        # Simulate Ctrl+/
        monkeypatch.setattr(pygame.key, "get_mods", lambda: pygame.KMOD_CTRL)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SLASH)
        on_key_down(app, event)
        assert app.show_shortcuts_panel

        # Toggle off
        on_key_down(app, event)
        assert not app.show_shortcuts_panel

    def test_esc_dismisses(self, tmp_path, monkeypatch):
        """Pressing Esc while panel is visible dismisses it."""
        app = _make_app(tmp_path, monkeypatch)
        app.show_shortcuts_panel = True
        from cyberpunk_designer.key_handlers import on_key_down

        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        on_key_down(app, event)
        assert not app.show_shortcuts_panel
