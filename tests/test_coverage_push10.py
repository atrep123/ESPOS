"""Push10: input_handlers click paths + overlays two-column help."""

from __future__ import annotations

import pygame

from cyberpunk_editor import CyberpunkEditorApp
from ui_models import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=60, height=20, text="hello")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _make_big_app(tmp_path, monkeypatch, *, widgets=None):
    """App with large layout so palette/inspector hitboxes have real sizes."""
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    app = CyberpunkEditorApp(json_path, (256, 128))
    if not hasattr(app, "_save_undo_state"):
        app._save_undo_state = lambda: None
    app.logical_surface = pygame.Surface((1200, 800))
    app.layout = app.layout.__class__(1200, 800)
    if widgets:
        sc = app.state.current_scene()
        for w in widgets:
            sc.widgets.append(w)
    return app


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None


DUMMY_MODS = 0


# ===========================================================================
# on_mouse_down — inspector_commit_edit fails (L684)
# ===========================================================================


class TestInspectorCommitFails:
    def test_commit_edit_returns_false(self, make_app):
        """Click outside inspector with bad edit pending — commit returns False (L684)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=0, y=0, width=40, height=20))
        _sel(app, 0)
        app.state.inspector_selected_field = "x"
        app.state.inspector_input_buffer = "not_a_number!!!"
        # Click on canvas (outside inspector)
        cr = app.layout.canvas_rect
        on_mouse_down(app, (cr.x + 5, cr.y + 5))


# ===========================================================================
# on_mouse_down — click outside canvas (L886)
# ===========================================================================


class TestClickOutsideCanvas:
    def test_click_outside_all_panels(self, make_app):
        """Click at coordinates not in any panel or canvas (L886)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = make_app()
        # Ensure no inspector editing state
        app.state.inspector_selected_field = None
        # Click far outside any panel (negative coords or beyond layout)
        on_mouse_down(app, (-50, -50))


# ===========================================================================
# on_mouse_down — selection empty after click (L911)
# ===========================================================================


class TestSelectionEmptyAfterClick:
    def test_ctrl_click_deselects_only_widget(self, monkeypatch, make_app):
        """Ctrl-click on the only selected widget deselects → empty selected (L911)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        cr = app.layout.canvas_rect
        app.scene_rect = pygame.Rect(cr.x, cr.y, 256, 128)
        # Ctrl held so _apply_click_selection toggles off the only widget
        monkeypatch.setattr("pygame.key.get_mods", lambda: pygame.KMOD_CTRL)
        pos = (cr.x + 15, cr.y + 15)
        on_mouse_down(app, pos)
        assert app.state.selected == []


# ===========================================================================
# on_mouse_down — bounds is None after selection (L921)
# ===========================================================================


class TestBoundsNoneAfterSelection:
    def test_selection_with_oob_index(self, make_app):
        """selection_bounds returns None for valid selection (L921)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        _sel(app, 0)
        cr = app.layout.canvas_rect
        app.scene_rect = pygame.Rect(cr.x, cr.y, 256, 128)
        # Monkeypatch _selection_bounds to return None (e.g. all zero-dim widgets)
        app._selection_bounds = lambda sel: None
        pos = (cr.x + 15, cr.y + 15)
        on_mouse_down(app, pos)


# ===========================================================================
# on_mouse_down — palette empty hitboxes triggers _draw_palette (L736)
# ===========================================================================


class TestPaletteEmptyHitboxes:
    def test_palette_click_no_hitboxes(self, make_app):
        """Click in palette area when hitboxes empty — triggers _draw_palette (L736)."""
        from cyberpunk_designer.input_handlers import on_mouse_down

        app = make_app()
        # Clear hitboxes so they're falsy
        app.palette_hitboxes = []
        app.palette_section_hitboxes = []
        app.palette_widget_hitboxes = []
        pr = app.layout.palette_rect
        on_mouse_down(app, (pr.x + 5, pr.y + 5))


# ===========================================================================
# on_mouse_down — scene_rect not a Rect in finish_box_select (L1030)
# ===========================================================================


class TestBoxSelectBadSceneRect:
    def test_finish_box_select_bad_scene_rect(self, make_app):
        """_finish_box_select with scene_rect=None (L1030)."""
        from cyberpunk_designer.input_handlers import on_mouse_up

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        # Both box_select_start AND box_select_rect must be non-None for _finish_box_select
        cr = app.layout.canvas_rect
        app.state.box_select_start = (cr.x, cr.y)
        app.state.box_select_rect = pygame.Rect(cr.x, cr.y, 100, 50)
        app.pointer_down = True
        app.scene_rect = None  # Not a Rect → triggers L1030
        on_mouse_up(app, (cr.x + 100, cr.y + 50))


# ===========================================================================
# on_mouse_move — empty selection returns early (L1108)
# ===========================================================================


class TestMouseMoveEmptySelection:
    def test_move_with_no_selection(self, make_app):
        """Mouse move while dragging but selection empty (L1108)."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = make_app()
        app.pointer_down = True
        app.state.dragging = True
        app.state.selected = []
        app.state.selected_idx = None
        cr = app.layout.canvas_rect
        app.scene_rect = pygame.Rect(cr.x, cr.y, 256, 128)
        on_mouse_move(app, (cr.x + 50, cr.y + 50), (1, 0, 0))


# ===========================================================================
# on_mouse_move — drag with missing start_position (L1152)
# ===========================================================================


class TestDragMissingStartPos:
    def test_drag_widget_not_in_start_positions(self, make_app):
        """Drag with widget index not in drag_start_positions (L1152)."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        sc.widgets.append(_w(type="label", x=60, y=10, width=40, height=20))
        app.pointer_down = True
        app.state.dragging = True
        _sel(app, 0, 1)
        # Only widget 0 has a start position — widget 1 should be skipped
        app.state.drag_start_rect = pygame.Rect(10, 10, 40, 20)
        app.state.drag_start_positions = {0: (10, 10)}  # Missing idx 1
        cr = app.layout.canvas_rect
        app.scene_rect = pygame.Rect(cr.x, cr.y, 256, 128)
        on_mouse_move(app, (cr.x + 60, cr.y + 60), (1, 0, 0))


# ===========================================================================
# on_mouse_move — drag with OOB index (L1154)
# ===========================================================================


class TestDragOOBIndex:
    def test_drag_oob_widget_index(self, make_app):
        """Drag with widget index that's OOB in widgets list (L1154)."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        app.pointer_down = True
        app.state.dragging = True
        _sel(app, 0, 99)  # Index 99 is OOB
        app.state.drag_start_rect = pygame.Rect(10, 10, 40, 20)
        app.state.drag_start_positions = {0: (10, 10), 99: (100, 100)}
        cr = app.layout.canvas_rect
        app.scene_rect = pygame.Rect(cr.x, cr.y, 256, 128)
        on_mouse_move(app, (cr.x + 60, cr.y + 60), (1, 0, 0))


# ===========================================================================
# overlays.py — two-column help overlay (L381-427)
# ===========================================================================


class TestHelpOverlayTwoColumn:
    def test_wide_help_overlay(self, tmp_path, monkeypatch, make_app):
        """Help overlay in wide window uses two-column layout (L381-427)."""
        from cyberpunk_designer.drawing.overlays import draw_help_overlay

        app = _make_big_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        draw_help_overlay(app)


# ===========================================================================
# on_mouse_move — snap_drag_to_guides exception (L1139-1140)
# ===========================================================================


class TestSnapDragException:
    def test_snap_drag_raises(self, monkeypatch, make_app):
        """snap_drag_to_guides raises Exception → caught (L1139-1140)."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        app.pointer_down = True
        app.state.dragging = True
        _sel(app, 0)
        app.state.drag_start_rect = pygame.Rect(10, 10, 40, 20)
        app.state.drag_start_positions = {0: (10, 10)}
        app.snap_enabled = True
        cr = app.layout.canvas_rect
        app.scene_rect = pygame.Rect(cr.x, cr.y, 256, 128)
        monkeypatch.setattr(
            "cyberpunk_designer.mouse_handlers.layout_tools.snap_drag_to_guides",
            lambda *a, **kw: (_ for _ in ()).throw(ValueError("snap fail")),
        )
        on_mouse_move(app, (cr.x + 60, cr.y + 60), (1, 0, 0))


# ===========================================================================
# on_mouse_move — clear_active_guides exception during resize (L1164-1165)
# ===========================================================================


class TestResizeClearGuidesException:
    def test_clear_guides_raises_during_resize(self, monkeypatch, make_app):
        """clear_active_guides raises during resize (L1164-1165)."""
        from cyberpunk_designer.input_handlers import on_mouse_move

        app = make_app()
        sc = app.state.current_scene()
        sc.widgets.append(_w(type="button", x=10, y=10, width=40, height=20))
        app.pointer_down = True
        app.state.resizing = True
        app.state.resize_anchor = "br"
        _sel(app, 0)
        app.state.drag_start_rect = pygame.Rect(10, 10, 40, 20)
        app.state.drag_start_positions = {0: (10, 10)}
        cr = app.layout.canvas_rect
        app.scene_rect = pygame.Rect(cr.x, cr.y, 256, 128)
        monkeypatch.setattr(
            "cyberpunk_designer.mouse_handlers.layout_tools.clear_active_guides",
            lambda *a, **kw: (_ for _ in ()).throw(AttributeError("clear fail")),
        )
        on_mouse_move(app, (cr.x + 80, cr.y + 80), (1, 0, 0))
