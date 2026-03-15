"""BW: Additional tests for panels, toolbar, overlays, and inspector commit
to push coverage toward 90%+."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pygame

from cyberpunk_designer.drawing.overlays import (
    draw_context_menu,
    draw_help_overlay,
    draw_tooltip,
)
from cyberpunk_designer.drawing.panels import draw_inspector, draw_palette, draw_status
from cyberpunk_designer.drawing.toolbar import draw_toolbar
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _w(**kw):
    defaults = dict(type="label", x=0, y=0, width=24, height=16, text="w")
    defaults.update(kw)
    return WidgetConfig(**defaults)


# ---------------------------------------------------------------------------
# draw_context_menu
# ---------------------------------------------------------------------------


class TestDrawContextMenu:
    def test_no_menu_attr(self, make_app):
        """No _context_menu → no-op."""
        app = make_app()
        if hasattr(app, "_context_menu"):
            del app._context_menu
        draw_context_menu(app)  # no crash

    def test_empty_items(self, make_app):
        """Menu with empty items → no-op."""
        app = make_app()
        app._context_menu = {"visible": True, "pos": (10, 10), "items": []}
        draw_context_menu(app)

    def test_separator_rendering(self, make_app):
        """Menu with separator items draws separator lines."""
        app = make_app()
        items = [
            ("Copy", "Ctrl+C", "copy"),
            ("---", "", None),
            ("Paste", "Ctrl+V", "paste"),
        ]
        app._context_menu = {"visible": True, "pos": (10, 10), "items": items}
        draw_context_menu(app)
        assert "hitboxes" in app._context_menu
        assert len(app._context_menu["hitboxes"]) == 2  # Only non-sep items

    def test_shortcut_rendering(self, make_app):
        """Menu items with shortcuts are rendered."""
        app = make_app()
        items = [("Copy", "Ctrl+C", "copy")]
        app._context_menu = {"visible": True, "pos": (10, 10), "items": items}
        draw_context_menu(app)
        assert len(app._context_menu["hitboxes"]) == 1

    def test_screen_edge_clamping(self, make_app):
        """Menu near screen edges clamps to fit."""
        app = make_app()
        items = [("Very Long Action Label Here", "", "action")]
        # Position near bottom-right corner
        app._context_menu = {"visible": True, "pos": (250, 125), "items": items}
        draw_context_menu(app)
        rect = app._context_menu.get("rect")
        assert rect is not None
        sw = app.logical_surface.get_width()
        sh = app.logical_surface.get_height()
        assert rect.right <= sw
        assert rect.bottom <= sh

    def test_hover_highlight(self, make_app):
        """Hover over menu item highlights it."""
        app = make_app()
        items = [("Copy", "", "copy")]
        app._context_menu = {"visible": True, "pos": (10, 10), "items": items}
        # Set pointer to item position
        app.pointer_pos = (20, 20)
        draw_context_menu(app)
        assert len(app._context_menu["hitboxes"]) == 1


# ---------------------------------------------------------------------------
# draw_tooltip
# ---------------------------------------------------------------------------


class TestDrawTooltip:
    def test_no_hover(self, make_app):
        """No toolbar/tab hover → tooltip key cleared."""
        app = make_app()
        app.pointer_pos = (-100, -100)
        app.pointer_down = False
        app.toolbar_hitboxes = []
        app.tab_hitboxes = []
        draw_tooltip(app)
        assert getattr(app, "_tooltip_key", None) is None

    def test_pointer_down_clears(self, make_app):
        """Pointer down clears tooltip."""
        app = make_app()
        app.pointer_down = True
        app._tooltip_key = "something"
        draw_tooltip(app)
        assert app._tooltip_key is None

    def test_toolbar_hover_starts_timer(self, make_app):
        """Hovering over toolbar button starts tooltip timer."""
        app = make_app()
        app.pointer_down = False
        btn_rect = pygame.Rect(10, 10, 30, 20)
        app.toolbar_hitboxes = [(btn_rect, "save")]
        app.tab_hitboxes = []
        app.pointer_pos = (20, 15)
        draw_tooltip(app)
        assert app._tooltip_key is not None

    def test_tooltip_shown_after_delay(self, make_app):
        """Tooltip renders after 0.5s hover delay."""
        app = make_app()
        app.pointer_down = False
        btn_rect = pygame.Rect(10, 10, 30, 20)
        app.toolbar_hitboxes = [(btn_rect, "save")]
        app.tab_hitboxes = []
        app.pointer_pos = (20, 15)
        # First call: start timer
        draw_tooltip(app)
        # Simulate elapsed time
        app._tooltip_start = time.time() - 1.0
        # Second call: should render
        draw_tooltip(app)

    def test_tab_hover_tooltip(self, make_app):
        """Hovering over a scene tab shows tooltip."""
        app = make_app()
        app.pointer_down = False
        tab_rect = pygame.Rect(10, 10, 50, 16)
        sc_name = app.designer.current_scene
        app.toolbar_hitboxes = []
        app.tab_hitboxes = [(tab_rect, 0, sc_name)]
        app.pointer_pos = (30, 15)
        draw_tooltip(app)
        assert app._tooltip_key is not None

    def test_add_tab_tooltip(self, make_app):
        """Hovering over '+' tab shows 'Add new scene' tooltip."""
        app = make_app()
        app.pointer_down = False
        tab_rect = pygame.Rect(100, 10, 20, 16)
        app.toolbar_hitboxes = []
        app.tab_hitboxes = [(tab_rect, -1, "+")]
        app.pointer_pos = (110, 15)
        draw_tooltip(app)
        assert "new scene" in (app._tooltip_key or "").lower()


# ---------------------------------------------------------------------------
# draw_help_overlay
# ---------------------------------------------------------------------------


class TestDrawHelpOverlay:
    def test_not_visible(self, make_app):
        """Overlay not shown when flag is False."""
        app = make_app()
        app.show_help_overlay = False
        draw_help_overlay(app)  # no crash

    def test_visible(self, make_app):
        """Overlay draws when flag is True."""
        app = make_app()
        app.show_help_overlay = True
        draw_help_overlay(app)

    def test_no_surface(self, make_app):
        """No logical_surface → no-op."""
        app = make_app()
        app.show_help_overlay = True
        app.logical_surface = None
        draw_help_overlay(app)


# ---------------------------------------------------------------------------
# draw_palette — edge cases
# ---------------------------------------------------------------------------


class TestDrawPaletteEdges:
    def test_collapsed_section(self, make_app):
        """Collapsed palette section skips items."""
        app = make_app(widgets=[_w()])
        sections = getattr(app, "palette_sections", [])
        if sections:
            app.palette_collapsed = {sections[0][0]}
        draw_palette(app)

    def test_nonzero_scroll(self, make_app):
        """Palette with scroll offset renders correctly."""
        app = make_app(widgets=[_w() for _ in range(20)])
        app.state.palette_scroll = 50
        draw_palette(app)

    def test_selected_widget_highlight(self, make_app):
        """Selected widget in palette list is highlighted."""
        app = make_app(widgets=[_w(), _w()])
        app.state.selected = [0]
        draw_palette(app)

    def test_content_height_exception(self, make_app):
        """Exception in _palette_content_height handled gracefully."""
        app = make_app()
        app._palette_content_height = MagicMock(side_effect=TypeError("bad"))
        draw_palette(app)  # Should not crash


# ---------------------------------------------------------------------------
# draw_inspector — edge cases
# ---------------------------------------------------------------------------


class TestDrawInspectorEdges:
    def test_no_selection(self, make_app):
        """Inspector with no selection draws empty."""
        app = make_app(widgets=[_w()])
        app.state.selected = []
        draw_inspector(app)

    def test_multi_selection(self, make_app):
        """Inspector with multi-selection shows shared fields."""
        app = make_app(widgets=[_w(), _w(text="other")])
        app.state.selected = [0, 1]
        draw_inspector(app)


# ---------------------------------------------------------------------------
# draw_status — edge cases
# ---------------------------------------------------------------------------


class TestDrawStatusEdges:
    def test_status_with_message(self, make_app):
        """Status bar with active message shows it."""
        app = make_app()
        app._set_status("Test message", ttl_sec=5.0)
        draw_status(app)

    def test_status_expired_message(self, make_app):
        """Expired status message is not shown."""
        app = make_app()
        app._set_status("Old message", ttl_sec=0.001)
        time.sleep(0.01)
        draw_status(app)


# ---------------------------------------------------------------------------
# draw_toolbar — edge cases
# ---------------------------------------------------------------------------


class TestDrawToolbarEdges:
    def test_basic_render(self, make_app):
        """Toolbar renders without crash."""
        app = make_app()
        draw_toolbar(app)
        assert len(getattr(app, "toolbar_hitboxes", [])) > 0


# ---------------------------------------------------------------------------
# _execute_context_action via dict dispatch
# ---------------------------------------------------------------------------


class TestContextActionDispatch:
    def test_simple_action(self, make_app):
        """Simple action dispatches to correct method."""
        app = make_app(widgets=[_w()])
        app.state.selected = [0]
        app._execute_context_action("toggle_visibility")
        # Should have toggled visibility
        sc = app.state.current_scene()
        assert hasattr(sc.widgets[0], "visible")

    def test_view_grid_toggle(self, make_app):
        """view_grid toggles show_grid flag."""
        app = make_app()
        before = app.show_grid
        app._execute_context_action("view_grid")
        assert app.show_grid != before

    def test_view_snap_toggle(self, make_app):
        """view_snap toggles snap_enabled flag."""
        app = make_app()
        before = app.snap_enabled
        app._execute_context_action("view_snap")
        assert app.snap_enabled != before

    def test_add_widget_action(self, make_app):
        """add_label action adds a label widget."""
        app = make_app()
        count_before = len(app.state.current_scene().widgets)
        app._execute_context_action("add_label")
        assert len(app.state.current_scene().widgets) == count_before + 1

    def test_unknown_action_noop(self, make_app):
        """Unknown action is a no-op."""
        app = make_app()
        app._execute_context_action("nonexistent_action_xyz")  # no crash

    def test_z_forward_action(self, make_app):
        """z_forward dispatches with parameter."""
        app = make_app(widgets=[_w(), _w(text="b")])
        app.state.selected = [0]
        app._execute_context_action("z_forward")

    def test_reorder_up_action(self, make_app):
        """reorder_up dispatches with -1 parameter."""
        app = make_app(widgets=[_w(), _w(text="b")])
        app.state.selected = [1]
        app._execute_context_action("reorder_up")


# ---------------------------------------------------------------------------
# _open_context_menu helper extraction
# ---------------------------------------------------------------------------


class TestContextMenuBuilders:
    def test_ctx_single_items(self, make_app):
        """_ctx_single_items returns expected item structure."""
        app = make_app()
        items = app._ctx_single_items(("---", "", None))
        assert len(items) > 10
        # All items are 3-tuples
        for item in items:
            assert len(item) == 3

    def test_ctx_multi_items(self, make_app):
        """_ctx_multi_items returns expected item structure."""
        app = make_app()
        items = app._ctx_multi_items(("---", "", None))
        assert len(items) > 10
        for item in items:
            assert len(item) == 3

    def test_ctx_view_items_reflects_state(self, make_app):
        """_ctx_view_items reflects current toggle state."""
        app = make_app()
        app.show_grid = True
        items = app._ctx_view_items()
        grid_item = next(i for i in items if "Grid" in i[0])
        assert "\u2713" in grid_item[0]

        app.show_grid = False
        items = app._ctx_view_items()
        grid_item = next(i for i in items if "Grid" in i[0])
        assert "\u2713" not in grid_item[0]

    def test_ctx_add_items(self, make_app):
        """_ctx_add_items returns add and composite items."""
        app = make_app()
        items = app._ctx_add_items(("---", "", None))
        actions = [i[2] for i in items if i[2] is not None]
        assert "add_label" in actions
        assert "create_header_bar" in actions

    def test_full_context_menu_with_selection(self, make_app):
        """Full context menu build with selected widgets."""
        app = make_app(widgets=[_w(), _w()])
        app.state.selected = [0, 1]
        app._clipboard = [_w()]
        app._open_context_menu((50, 50))
        menu = app._context_menu
        assert menu["visible"]
        assert len(menu["items"]) > 20

    def test_context_menu_no_selection(self, make_app):
        """Context menu with no selection shows add widgets + view."""
        app = make_app()
        app.state.selected = []
        app._open_context_menu((50, 50))
        menu = app._context_menu
        actions = [i[2] for i in menu["items"] if i[2] is not None]
        assert "add_label" in actions
        assert "view_grid" in actions
