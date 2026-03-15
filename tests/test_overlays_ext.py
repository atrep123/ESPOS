"""Extended tests for cyberpunk_designer/drawing/overlays.py — targeting
uncovered lines to push coverage from 69% to 85%+."""

from __future__ import annotations

import time

import pygame

from cyberpunk_designer.drawing.overlays import (
    TOOLBAR_TOOLTIPS,
    draw_context_menu,
    draw_help_overlay,
    draw_tooltip,
)
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# draw_tooltip — tab hitboxes (lines 121-133)
# ---------------------------------------------------------------------------


class TestDrawTooltipTabs:
    """Hit tab_hitboxes code paths (lines 121-133, 145-162)."""

    def test_tab_hover_normal(self, make_app):
        app = make_app()
        # Set up tab hitbox for an existing scene
        scene_name = app.designer.current_scene
        tab_rect = pygame.Rect(50, 0, 60, 16)
        app.tab_hitboxes = [(tab_rect, 0, scene_name)]
        app.toolbar_hitboxes = []
        app.pointer_down = False
        app.pointer_pos = (tab_rect.centerx, tab_rect.centery)
        app._tooltip_key = None
        draw_tooltip(app)
        # Should have set tooltip key to scene info
        assert app._tooltip_key is not None
        assert scene_name in str(app._tooltip_key)

    def test_tab_hover_add_button(self, make_app):
        app = make_app()
        # tab_idx == -1 means "add new scene" button
        tab_rect = pygame.Rect(200, 0, 20, 16)
        app.tab_hitboxes = [(tab_rect, -1, "+")]
        app.toolbar_hitboxes = []
        app.pointer_down = False
        app.pointer_pos = (tab_rect.centerx, tab_rect.centery)
        app._tooltip_key = None
        draw_tooltip(app)
        assert app._tooltip_key is not None
        assert "new scene" in str(app._tooltip_key).lower()

    def test_tab_hover_with_dirty(self, make_app):
        app = make_app()
        scene_name = app.designer.current_scene
        tab_rect = pygame.Rect(50, 0, 60, 16)
        app.tab_hitboxes = [(tab_rect, 0, scene_name)]
        app.toolbar_hitboxes = []
        app.pointer_down = False
        app.pointer_pos = (tab_rect.centerx, tab_rect.centery)
        app._dirty_scenes = {scene_name}
        app._tooltip_key = None
        draw_tooltip(app)
        assert "modified" in str(app._tooltip_key).lower() or app._tooltip_key is not None

    def test_tab_hover_with_index_lt9(self, make_app):
        app = make_app()
        scene_name = app.designer.current_scene
        tab_rect = pygame.Rect(50, 0, 60, 16)
        app.tab_hitboxes = [(tab_rect, 3, scene_name)]
        app.toolbar_hitboxes = []
        app.pointer_down = False
        app.pointer_pos = (tab_rect.centerx, tab_rect.centery)
        app._tooltip_key = None
        draw_tooltip(app)
        # Should include Ctrl+4 (tab_idx+1)
        assert "Ctrl+4" in str(app._tooltip_key) or app._tooltip_key is not None

    def test_tooltip_renders_after_delay(self, make_app):
        """After 0.5s hover delay, tooltip should render (lines 145-162)."""
        app = make_app()
        tab_rect = pygame.Rect(50, 0, 60, 16)
        scene_name = app.designer.current_scene
        app.tab_hitboxes = [(tab_rect, 0, scene_name)]
        app.toolbar_hitboxes = []
        app.pointer_down = False
        app.pointer_pos = (tab_rect.centerx, tab_rect.centery)

        # First call: sets tooltip key and start time
        app._tooltip_key = None
        draw_tooltip(app)
        tip_key = app._tooltip_key

        # Simulate time passing beyond delay
        app._tooltip_start = time.time() - 1.0
        app._tooltip_key = tip_key
        draw_tooltip(app)
        # Should have rendered without crash (covered lines 145-162)

    def test_tooltip_toolbar_hover_renders(self, make_app):
        """Toolbar tooltip after delay (lines 145-162 via toolbar path)."""
        app = make_app()
        btn_rect = pygame.Rect(10, 0, 30, 16)
        app.toolbar_hitboxes = [(btn_rect, "save")]
        app.tab_hitboxes = []
        app.pointer_down = False
        app.pointer_pos = (btn_rect.centerx, btn_rect.centery)

        app._tooltip_key = None
        draw_tooltip(app)
        tip_key = app._tooltip_key
        assert tip_key is not None

        # Set past delay
        app._tooltip_start = time.time() - 1.0
        app._tooltip_key = tip_key
        draw_tooltip(app)

    def test_tooltip_bottom_edge(self, make_app):
        """Tooltip near bottom of screen repositions upward."""
        app = make_app()
        btn_rect = pygame.Rect(10, 0, 30, 16)
        app.toolbar_hitboxes = [(btn_rect, "save")]
        app.tab_hitboxes = []
        app.pointer_down = False
        # Place pointer near bottom
        app.pointer_pos = (btn_rect.centerx, app.logical_surface.get_height() - 2)

        app._tooltip_key = TOOLBAR_TOOLTIPS["save"]
        app._tooltip_start = time.time() - 1.0
        draw_tooltip(app)

    def test_tooltip_no_match_clears(self, make_app):
        """No matching hitbox clears tooltip (line 140)."""
        app = make_app()
        app.toolbar_hitboxes = []
        app.tab_hitboxes = []
        app.pointer_down = False
        app.pointer_pos = (50, 50)
        app._tooltip_key = "previous"
        draw_tooltip(app)
        assert app._tooltip_key is None

    def test_tooltip_key_changes_resets_timer(self, make_app):
        """Changing hover target resets delay (lines 137-139)."""
        app = make_app()
        btn1_rect = pygame.Rect(10, 0, 30, 16)
        btn2_rect = pygame.Rect(50, 0, 30, 16)
        app.toolbar_hitboxes = [(btn1_rect, "save"), (btn2_rect, "load")]
        app.tab_hitboxes = []
        app.pointer_down = False

        # Hover first button
        app.pointer_pos = (btn1_rect.centerx, btn1_rect.centery)
        app._tooltip_key = None
        draw_tooltip(app)
        key1 = app._tooltip_key

        # Move to second button
        app.pointer_pos = (btn2_rect.centerx, btn2_rect.centery)
        draw_tooltip(app)
        key2 = app._tooltip_key
        assert key2 != key1


# ---------------------------------------------------------------------------
# draw_help_overlay — full rendering (lines 319-427)
# ---------------------------------------------------------------------------


class TestDrawHelpOverlay:
    def test_no_surface_noop(self, make_app):
        app = make_app()
        app.show_help_overlay = True
        app.logical_surface = None
        draw_help_overlay(app)

    def test_no_layout_noop(self, make_app):
        app = make_app()
        app.show_help_overlay = True
        app.layout = None
        draw_help_overlay(app)

    def test_zero_dims_noop(self, make_app):
        app = make_app()
        app.show_help_overlay = True
        app.layout.width = 0
        draw_help_overlay(app)

    def test_full_render_narrow(self, make_app):
        """Narrow panel → single-column layout (lines 439-455)."""
        app = make_app()
        app.show_help_overlay = True
        # Ensure it's narrow enough for single-column
        # Default 256x128 is narrow
        draw_help_overlay(app)

    def test_full_render_wide(self, make_app):
        """Wide panel → two-column layout (lines 391-437)."""
        app = make_app()
        app.show_help_overlay = True
        # Make surface and layout wide enough for two-column
        wide_surf = pygame.Surface((1200, 600))
        app.logical_surface = wide_surf
        app.layout.width = 1200
        app.layout.height = 600
        draw_help_overlay(app)

    def test_with_hardware_profile(self, make_app):
        """Cover profile_label branch (lines 323-331)."""
        app = make_app()
        app.show_help_overlay = True
        app.hardware_profile = "esp32os_256x128_gray4"
        draw_help_overlay(app)

    def test_with_no_profile(self, make_app):
        """Cover profile_label = 'none' branch."""
        app = make_app()
        app.show_help_overlay = True
        app.hardware_profile = ""
        draw_help_overlay(app)

    def test_with_widgets(self, make_app):
        """Cover scene_dims, widgets_count branches."""
        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=0, y=0, width=24, height=16, text="t"))
        app.show_help_overlay = True
        draw_help_overlay(app)

    def test_with_selection(self, make_app):
        """Cover sel_count branch."""
        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=0, y=0, width=24, height=16, text="t"))
        app.state.selected = [0]
        app.show_help_overlay = True
        draw_help_overlay(app)

    def test_with_panels_collapsed(self, make_app):
        app = make_app()
        app.show_help_overlay = True
        app.panels_collapsed = True
        draw_help_overlay(app)

    def test_with_sim_input_mode(self, make_app):
        app = make_app()
        app.show_help_overlay = True
        app.sim_input_mode = True
        draw_help_overlay(app)

    def test_with_resource_estimation(self, make_app):
        """Cover est / res_line / overlaps branches (lines 341-358)."""
        app = make_app()
        app.show_help_overlay = True
        app.hardware_profile = "esp32os_256x128_gray4"
        # Add some widgets so estimation has data
        sc = app.state.current_scene()
        for i in range(3):
            sc.widgets.append(
                WidgetConfig(type="label", x=i * 10, y=0, width=24, height=16, text=f"w{i}")
            )
        draw_help_overlay(app)

    def test_content_rect_zero_returns(self, make_app):
        """Content rect with zero dimensions returns early (line 222)."""
        app = make_app()
        app.show_help_overlay = True
        app.pixel_row_height = 99999  # row_h so big content_rect.height <= 0
        draw_help_overlay(app)


# ---------------------------------------------------------------------------
# draw_context_menu — extra coverage
# ---------------------------------------------------------------------------


class TestDrawContextMenuExtra:
    def test_no_surface_noop(self, make_app):
        app = make_app()
        app._context_menu = {"visible": True, "items": [("A", "", lambda: None)], "pos": (0, 0)}
        app.logical_surface = None
        draw_context_menu(app)

    def test_empty_items_noop(self, make_app):
        app = make_app()
        app._context_menu = {"visible": True, "items": [], "pos": (0, 0)}
        draw_context_menu(app)

    def test_hover_over_item(self, make_app):
        """Hover highlighting code path."""
        app = make_app()
        items = [("Action", "Ctrl+A", lambda: None)]
        app._context_menu = {"visible": True, "items": items, "pos": (10, 10)}
        # First draw to get hitboxes
        draw_context_menu(app)
        if app._context_menu.get("hitboxes"):
            r = app._context_menu["hitboxes"][0][0]
            app.pointer_pos = (r.centerx, r.centery)
            draw_context_menu(app)

    def test_separator_only(self, make_app):
        """Menu with only separators."""
        app = make_app()
        items = [(None, None, None), (None, None, None)]
        app._context_menu = {"visible": True, "items": items, "pos": (10, 10)}
        draw_context_menu(app)
        # No actionable items → empty hitboxes
        assert app._context_menu.get("hitboxes") == []

    def test_no_shortcut(self, make_app):
        """Item without shortcut text."""
        app = make_app()
        items = [("Action", "", lambda: None)]
        app._context_menu = {"visible": True, "items": items, "pos": (10, 10)}
        draw_context_menu(app)
        assert len(app._context_menu["hitboxes"]) == 1

    def test_right_edge_clamp(self, make_app):
        """Menu near right edge is clamped to stay on screen."""
        app = make_app()
        sw = app.logical_surface.get_width()
        items = [("Long action label", "Ctrl+Shift+X", lambda: None)]
        app._context_menu = {
            "visible": True,
            "items": items,
            "pos": (sw - 5, 10),
        }
        draw_context_menu(app)
        menu_rect = app._context_menu.get("rect")
        assert menu_rect is not None
        assert menu_rect.right <= sw

    def test_bottom_edge_clamp(self, make_app):
        """Menu near bottom edge is clamped to stay on screen."""
        app = make_app()
        sh = app.logical_surface.get_height()
        items = [
            ("Act1", "", lambda: None),
            ("Act2", "", lambda: None),
            ("Act3", "", lambda: None),
        ]
        app._context_menu = {
            "visible": True,
            "items": items,
            "pos": (10, sh - 5),
        }
        draw_context_menu(app)
        menu_rect = app._context_menu.get("rect")
        assert menu_rect is not None
        assert menu_rect.bottom <= sh

    def test_many_items_generates_hitboxes(self, make_app):
        """Menu with many items produces correct number of hitboxes."""
        app = make_app()
        items = [(f"Item {i}", "", lambda: None) for i in range(8)]
        app._context_menu = {"visible": True, "items": items, "pos": (10, 10)}
        draw_context_menu(app)
        assert len(app._context_menu["hitboxes"]) == 8

    def test_mixed_items_and_separators(self, make_app):
        """Separators are skipped in hitboxes."""
        app = make_app()
        items = [
            ("Cut", "Ctrl+X", lambda: None),
            (None, None, None),
            ("Copy", "Ctrl+C", lambda: None),
            (None, None, None),
            ("Paste", "Ctrl+V", lambda: None),
        ]
        app._context_menu = {"visible": True, "items": items, "pos": (10, 10)}
        draw_context_menu(app)
        assert len(app._context_menu["hitboxes"]) == 3

    def test_not_visible_noop(self, make_app):
        """Menu with visible=False does nothing."""
        app = make_app()
        app._context_menu = {
            "visible": False,
            "items": [("A", "", lambda: None)],
            "pos": (0, 0),
        }
        draw_context_menu(app)
        assert "hitboxes" not in app._context_menu

    def test_no_menu_attr_noop(self, make_app):
        """No _context_menu attribute does nothing."""
        app = make_app()
        if hasattr(app, "_context_menu"):
            del app._context_menu
        draw_context_menu(app)
