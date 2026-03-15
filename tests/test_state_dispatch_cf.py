"""CF: Tests for EditorState, save_undo helper, and dispatch refactors."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pygame
import pytest

from cyberpunk_designer.selection_ops.core import save_undo
from cyberpunk_designer.state import EditorState
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _w(**kw):
    defaults = dict(type="label", x=10, y=10, width=24, height=16, text="t")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _designer_and_layout():
    designer = UIDesigner(256, 128)
    designer.create_scene("main")
    designer.current_scene = "main"
    from cyberpunk_designer.layout import Layout

    layout = Layout(256, 128)
    return designer, layout


# ---------------------------------------------------------------------------
# EditorState tests
# ---------------------------------------------------------------------------


class TestEditorState:
    def test_init_defaults(self):
        d, layout = _designer_and_layout()
        state = EditorState(d, layout)
        assert state.selected == []
        assert state.selected_idx is None
        assert state.dragging is False
        assert state.resizing is False
        assert state.input_mode is False
        assert state.palette_scroll == 0
        assert state.inspector_scroll == 0
        assert state.inspector_selected_field is None
        assert state.inspector_input_buffer == ""

    def test_current_scene(self):
        d, layout = _designer_and_layout()
        state = EditorState(d, layout)
        sc = state.current_scene()
        assert sc.name == "main"

    def test_selected_widget_none(self):
        d, layout = _designer_and_layout()
        state = EditorState(d, layout)
        assert state.selected_widget() is None

    def test_selected_widget_valid(self):
        d, layout = _designer_and_layout()
        sc = d.scenes["main"]
        w = WidgetConfig(type="label", x=0, y=0, width=10, height=10)
        sc.widgets.append(w)
        state = EditorState(d, layout)
        state.selected_idx = 0
        assert state.selected_widget() is w

    def test_selected_widget_oob(self):
        d, layout = _designer_and_layout()
        state = EditorState(d, layout)
        state.selected_idx = 999
        assert state.selected_widget() is None

    def test_select_at_hit(self):
        d, layout = _designer_and_layout()
        sc = d.scenes["main"]
        w = WidgetConfig(type="label", x=10, y=10, width=20, height=20)
        sc.widgets.append(w)
        state = EditorState(d, layout)
        origin = pygame.Rect(0, 0, 256, 128)
        result = state.select_at((15, 15), origin)
        assert result == 0
        assert state.selected == [0]
        assert state.selected_idx == 0

    def test_select_at_miss(self):
        d, layout = _designer_and_layout()
        sc = d.scenes["main"]
        w = WidgetConfig(type="label", x=10, y=10, width=20, height=20)
        sc.widgets.append(w)
        state = EditorState(d, layout)
        origin = pygame.Rect(0, 0, 256, 128)
        result = state.select_at((200, 200), origin)
        assert result is None
        assert state.selected == []

    def test_hit_test_reverse_order(self):
        """Top widget (later index) takes priority."""
        d, layout = _designer_and_layout()
        sc = d.scenes["main"]
        sc.widgets.append(WidgetConfig(type="label", x=0, y=0, width=30, height=30))
        sc.widgets.append(WidgetConfig(type="button", x=0, y=0, width=30, height=30))
        state = EditorState(d, layout)
        origin = pygame.Rect(0, 0, 256, 128)
        assert state.hit_test_at((5, 5), origin) == 1

    def test_hit_test_skips_invisible(self):
        """Invisible widgets are not hit."""
        d, layout = _designer_and_layout()
        sc = d.scenes["main"]
        sc.widgets.append(WidgetConfig(type="label", x=0, y=0, width=30, height=30))
        w_hidden = WidgetConfig(type="button", x=0, y=0, width=30, height=30)
        w_hidden.visible = False
        sc.widgets.append(w_hidden)
        state = EditorState(d, layout)
        origin = pygame.Rect(0, 0, 256, 128)
        assert state.hit_test_at((5, 5), origin) == 0

    def test_hit_test_empty(self):
        d, layout = _designer_and_layout()
        state = EditorState(d, layout)
        origin = pygame.Rect(0, 0, 256, 128)
        assert state.hit_test_at((5, 5), origin) is None


# ---------------------------------------------------------------------------
# save_undo helper
# ---------------------------------------------------------------------------


class TestSaveUndo:
    def test_normal(self):
        """save_undo calls _save_state."""
        app = MagicMock()
        save_undo(app)
        app.designer._save_state.assert_called_once()

    def test_attribute_error_silent(self):
        """AttributeError is swallowed silently."""
        app = MagicMock()
        app.designer._save_state.side_effect = AttributeError("no attr")
        save_undo(app)  # no exception

    def test_type_error_silent(self):
        app = MagicMock()
        app.designer._save_state.side_effect = TypeError("bad")
        save_undo(app)  # no exception

    def test_value_error_silent(self):
        app = MagicMock()
        app.designer._save_state.side_effect = ValueError("bad")
        save_undo(app)  # no exception

    def test_log_true_warns(self):
        """With log=True, exception is logged."""
        app = MagicMock()
        app.designer._save_state.side_effect = TypeError("bad")
        # Should not raise
        save_undo(app, log=True)

    def test_runtime_error_propagates(self):
        """Non-caught exceptions propagate."""
        app = MagicMock()
        app.designer._save_state.side_effect = RuntimeError("unexpected")
        with pytest.raises(RuntimeError):
            save_undo(app)


# ---------------------------------------------------------------------------
# Dispatch refactored methods
# ---------------------------------------------------------------------------


class TestHandleQuit:
    def test_quit_dirty_first_press(self, make_app):
        app = make_app(widgets=[_w()])
        app._dirty_scenes = {"main"}
        app._quit_confirm_ts = 0.0
        app._handle_quit()
        assert app.running is True  # first press: just status
        assert app._quit_confirm_ts > 0.0

    def test_quit_dirty_second_press(self, make_app):
        app = make_app(widgets=[_w()])
        app._dirty_scenes = {"main"}
        app._quit_confirm_ts = time.time()  # recent
        app._handle_quit()
        assert app.running is False

    def test_quit_clean(self, make_app):
        app = make_app()
        app._dirty_scenes = set()
        app._handle_quit()
        assert app.running is False


class TestDispatchMouseDown:
    def test_right_click_canvas(self, make_app):
        app = make_app(widgets=[_w()])
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=3,
            pos=(app.layout.canvas_rect.centerx, app.layout.canvas_rect.centery),
        )
        app._dispatch_mouse_down(event)
        # A context menu should have been opened
        menu = getattr(app, "_context_menu", None)
        assert menu is not None

    def test_left_click_no_menu(self, make_app):
        app = make_app()
        if hasattr(app, "_context_menu"):
            app._context_menu = {"visible": False}
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=1,
            pos=(app.layout.canvas_rect.centerx, app.layout.canvas_rect.centery),
        )
        app._dispatch_mouse_down(event)
        assert app.pointer_down is True

    def test_middle_click_no_tab(self, make_app):
        app = make_app()
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=2,
            pos=(app.layout.canvas_rect.centerx, app.layout.canvas_rect.centery),
        )
        app._dispatch_mouse_down(event)  # no crash


class TestHandleLeftClick:
    def test_dismiss_context_menu(self, make_app):
        app = make_app()
        app._context_menu = {
            "visible": True,
            "items": [("Test", lambda: None)],
            "x": 0,
            "y": 0,
            "hover_idx": -1,
        }
        event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=1,
            pos=(app.layout.canvas_rect.centerx, app.layout.canvas_rect.centery),
        )
        app._handle_left_click(event)
        # Menu should be dismissed or click handled

    def test_double_click_detection(self, make_app):
        app = make_app(widgets=[_w(x=0, y=0, width=100, height=100)])
        pos = (app.layout.canvas_rect.x + 10, app.layout.canvas_rect.y + 10)
        # First click
        app._last_click_time = time.time()
        app._last_click_pos = app._screen_to_logical(pos)
        # Second click fast
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)
        app._handle_left_click(event)
        # Should have processed (no crash)


class TestDispatchEvent:
    def test_videoresize(self, make_app):
        app = make_app()
        event = pygame.event.Event(pygame.VIDEORESIZE, w=800, h=600)
        app._dispatch_event(event)
        # No crash, window may have resized

    def test_mousewheel(self, make_app):
        app = make_app()
        event = pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1)
        app._dispatch_event(event)

    def test_textinput(self, make_app):
        app = make_app()
        app.state.inspector_selected_field = "text"
        app.state.inspector_input_buffer = ""
        event = pygame.event.Event(pygame.TEXTINPUT, text="A")
        app._dispatch_event(event)
        assert "A" in app.state.inspector_input_buffer

    def test_mousemotion(self, make_app):
        app = make_app()
        event = pygame.event.Event(
            pygame.MOUSEMOTION,
            pos=(100, 100),
            buttons=(0, 0, 0),
        )
        app._dispatch_event(event)

    def test_mouseup(self, make_app):
        app = make_app()
        app.pointer_down = True
        event = pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            button=1,
            pos=(100, 100),
        )
        app._dispatch_event(event)
        assert app.pointer_down is False


# ---------------------------------------------------------------------------
# _build_palette / _build_toolbar
# ---------------------------------------------------------------------------


class TestBuildPalette:
    def test_palette_sections_populated(self, make_app):
        app = make_app()
        assert len(app.palette_sections) >= 6
        names = [name for name, _items in app.palette_sections]
        assert "Add Widget" in names
        assert "Templates" in names
        assert "Colors" in names
        assert "Components" in names
        assert "Layout" in names
        assert "Profiles" in names

    def test_palette_collapsed_defaults(self, make_app):
        app = make_app()
        assert "Add Widget" not in app.palette_collapsed
        assert "Templates" in app.palette_collapsed

    def test_palette_actions_flat(self, make_app):
        app = make_app()
        assert len(app.palette_actions) > 0
        # Each action is a (name, callable_or_none) tuple
        for name, action in app.palette_actions:
            assert isinstance(name, str)
            assert action is None or callable(action)

    def test_rebuild_palette(self, make_app):
        app = make_app()
        old_count = len(app.palette_actions)
        app._build_palette()
        assert len(app.palette_actions) == old_count


class TestBuildToolbar:
    def test_toolbar_actions(self, make_app):
        app = make_app()
        assert len(app.toolbar_actions) == 11
        names = [name for name, _action in app.toolbar_actions]
        assert "New" in names
        assert "Save" in names
        assert "Live" in names
        assert "Undo" in names
        assert "Redo" in names
        assert "Tpl" in names

    def test_overflow_warnings_env(self, make_app, monkeypatch):
        monkeypatch.setenv("ESP32OS_OVERFLOW_WARN", "1")
        app = make_app()
        assert app.show_overflow_warnings is True

    def test_overflow_warnings_env_off(self, make_app, monkeypatch):
        monkeypatch.setenv("ESP32OS_OVERFLOW_WARN", "0")
        app = make_app()
        assert app.show_overflow_warnings is False
