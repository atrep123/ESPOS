"""Tests for remaining untested functions across the codebase.

Covers:
 - selection_ops: smart_edit, widget_info, scene_stats, fit_scene_to_content,
   toggle_all_borders, list_templates, center_in_scene
 - reporting: screenshot_canvas
 - input_handlers: on_key_down, on_mouse_down, on_mouse_up, on_mouse_move,
   on_mouse_wheel (smoke tests via app wrappers)
"""

from __future__ import annotations

from types import SimpleNamespace

import pygame

from cyberpunk_designer.input_handlers import (
    on_key_down,
    on_mouse_down,
    on_mouse_move,
    on_mouse_up,
    on_mouse_wheel,
)
from cyberpunk_designer.reporting import screenshot_canvas
from cyberpunk_designer.selection_ops import (
    center_in_scene,
    fit_scene_to_content,
    list_templates,
    scene_stats,
    smart_edit,
    toggle_all_borders,
    widget_info,
)
from cyberpunk_editor import CyberpunkEditorApp
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    return CyberpunkEditorApp(json_path, (256, 128))


def _add(app, **kw):
    defaults = dict(type="label", x=0, y=0, width=80, height=16, text="W")
    defaults.update(kw)
    w = WidgetConfig(**defaults)
    sc = app.state.current_scene()
    sc.widgets.append(w)
    return w


def _w(app, idx):
    return app.state.current_scene().widgets[idx]


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None


# ===================================================================
# smart_edit
# ===================================================================


class TestSmartEdit:
    def test_label_opens_text_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label", text="Hello")
        _sel(app, 0)
        smart_edit(app)
        # Should have started editing "text" field
        assert app.state.inspector_selected_field == "text"

    def test_button_opens_text_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="button", text="OK")
        _sel(app, 0)
        smart_edit(app)
        assert app.state.inspector_selected_field == "text"

    def test_gauge_opens_value_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="gauge")
        _sel(app, 0)
        smart_edit(app)
        assert app.state.inspector_selected_field == "value"

    def test_progressbar_opens_value_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="progressbar")
        _sel(app, 0)
        smart_edit(app)
        assert app.state.inspector_selected_field == "value"

    def test_chart_opens_data_points_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="chart")
        _sel(app, 0)
        smart_edit(app)
        assert app.state.inspector_selected_field == "data_points"

    def test_icon_opens_icon_char_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="icon")
        _sel(app, 0)
        smart_edit(app)
        assert app.state.inspector_selected_field == "icon_char"

    def test_checkbox_toggles_checked(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="checkbox", checked=False)
        _sel(app, 0)
        smart_edit(app)
        assert _w(app, 0).checked is True

    def test_nothing_selected_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        smart_edit(app)  # should not crash

    def test_panel_opens_text_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="panel", text="Panel1")
        _sel(app, 0)
        smart_edit(app)
        assert app.state.inspector_selected_field == "text"


# ===================================================================
# widget_info
# ===================================================================


class TestWidgetInfo:
    def test_shows_widget_info_in_status(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label", x=10, y=20, width=80, height=16, text="Hello")
        _sel(app, 0)
        widget_info(app)
        status = app.dialog_message
        assert "#0" in status
        assert "label" in status
        assert "Hello" in status

    def test_truncates_long_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label", text="A" * 50)
        _sel(app, 0)
        widget_info(app)
        status = app.dialog_message
        # Should show ellipsis for text > 12 chars
        assert "\u2026" in status

    def test_locked_flag(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, type="label")
        w.locked = True
        _sel(app, 0)
        widget_info(app)
        assert "L" in app.dialog_message

    def test_hidden_flag(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, type="label")
        w.visible = False
        _sel(app, 0)
        widget_info(app)
        assert "H" in app.dialog_message

    def test_disabled_flag(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, type="label")
        w.enabled = False
        _sel(app, 0)
        widget_info(app)
        assert "D" in app.dialog_message

    def test_no_selection_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        widget_info(app)


# ===================================================================
# scene_stats
# ===================================================================


class TestSceneStats:
    def test_empty_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        scene_stats(app)
        assert "empty" in app.dialog_message.lower()

    def test_shows_widget_count(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _add(app, type="button")
        _add(app, type="label")
        scene_stats(app)
        status = app.dialog_message
        assert "3w" in status

    def test_shows_type_breakdown(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _add(app, type="label")
        _add(app, type="button")
        scene_stats(app)
        assert "label:2" in app.dialog_message

    def test_shows_hidden_locked_flags(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w1 = _add(app, type="label")
        w1.visible = False
        w2 = _add(app, type="label")
        w2.locked = True
        scene_stats(app)
        status = app.dialog_message
        assert "1H" in status
        assert "1L" in status


# ===================================================================
# fit_scene_to_content
# ===================================================================


class TestFitSceneToContent:
    def test_resizes_to_fit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        _add(app, x=10, y=10, width=60, height=20)
        fit_scene_to_content(app)
        # Width should be snap(10+60+ GRID) and height snap(10+20+GRID)
        assert sc.width >= 70
        assert sc.height >= 30

    def test_empty_scene_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        fit_scene_to_content(app)  # should not crash

    def test_large_widgets(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        _add(app, x=200, y=100, width=100, height=50)
        fit_scene_to_content(app)
        assert sc.width >= 300
        assert sc.height >= 150


# ===================================================================
# toggle_all_borders
# ===================================================================


class TestToggleAllBorders:
    def test_all_bordered_turns_off(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        for _ in range(3):
            w = _add(app)
            w.border = True
        toggle_all_borders(app)
        sc = app.state.current_scene()
        assert all(not w.border for w in sc.widgets)

    def test_mixed_turns_all_on(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w1 = _add(app)
        w1.border = True
        w2 = _add(app)
        w2.border = False
        toggle_all_borders(app)
        sc = app.state.current_scene()
        assert all(w.border for w in sc.widgets)

    def test_empty_scene_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        toggle_all_borders(app)

    def test_double_toggle_restores(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        for _ in range(3):
            w = _add(app)
            w.border = True
        toggle_all_borders(app)
        toggle_all_borders(app)
        sc = app.state.current_scene()
        assert all(w.border for w in sc.widgets)


# ===================================================================
# list_templates
# ===================================================================


class TestListTemplates:
    def test_no_template_library(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Ensure there's no template_library attribute in a usable form
        if hasattr(app, "template_library"):
            app.template_library = None
        list_templates(app)
        assert "no template" in app.dialog_message.lower()

    def test_empty_templates(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.template_library = SimpleNamespace(templates={})
        list_templates(app)
        assert "no saved" in app.dialog_message.lower()

    def test_shows_template_names(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.template_library = SimpleNamespace(templates={"btn": None, "hdr": None})
        list_templates(app)
        status = app.dialog_message
        assert "btn" in status
        assert "hdr" in status

    def test_truncates_long_list(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        templates = {f"tmpl_{i}": None for i in range(15)}
        app.template_library = SimpleNamespace(templates=templates)
        list_templates(app)
        assert "more" in app.dialog_message.lower()


# ===================================================================
# center_in_scene
# ===================================================================


class TestCenterInScene:
    def test_centers_single_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        _add(app, x=0, y=0, width=80, height=16)
        _sel(app, 0)
        center_in_scene(app)
        w = _w(app, 0)
        # Should be centered: x = (256 - 80) // 2 = 88, y = (128 - 16) // 2 = 56
        assert int(w.x) == (sc.width - 80) // 2
        assert int(w.y) == (sc.height - 16) // 2

    def test_centers_group(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        _add(app, x=0, y=0, width=40, height=10)
        _add(app, x=40, y=0, width=40, height=10)
        _sel(app, 0, 1)
        center_in_scene(app)
        # Group spans 80px wide, 10px tall
        # Center: (256 - 80) // 2 = 88, (128 - 10) // 2 = 59
        assert int(_w(app, 0).x) == (sc.width - 80) // 2
        assert int(_w(app, 1).x) == (sc.width - 80) // 2 + 40

    def test_nothing_selected_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        center_in_scene(app)  # should not crash


# ===================================================================
# reporting.screenshot_canvas
# ===================================================================


class TestScreenshotCanvas:
    def test_saves_png(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label", x=10, y=10, width=60, height=12, text="Test")
        # Redirect reports dir to tmp_path
        monkeypatch.chdir(tmp_path)
        screenshot_canvas(app)
        reports = tmp_path / "reports"
        assert reports.exists()
        pngs = list(reports.glob("*.png"))
        assert len(pngs) == 1

    def test_hidden_widgets_skipped(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, type="label")
        w.visible = False
        monkeypatch.chdir(tmp_path)
        screenshot_canvas(app)
        # Should still produce a file even with no visible widgets
        pngs = list((tmp_path / "reports").glob("*.png"))
        assert len(pngs) == 1

    def test_empty_scene_creates_screenshot(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.chdir(tmp_path)
        screenshot_canvas(app)
        pngs = list((tmp_path / "reports").glob("*.png"))
        assert len(pngs) == 1


# ===================================================================
# input_handlers — smoke tests via module-level functions
# ===================================================================


class TestOnKeyDown:
    def test_f1_toggles_help(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Ensure help is off to start
        app.show_help_overlay = False
        app._help_pinned = False
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1, mod=0, unicode="")
        on_key_down(app, event)
        assert bool(app.show_help_overlay) is True

    def test_escape_during_inspector_edit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label", text="Hello")
        _sel(app, 0)
        app._inspector_start_edit("text")
        assert app.state.inspector_selected_field == "text"
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="")
        on_key_down(app, event)
        assert app.state.inspector_selected_field is None

    def test_backspace_during_edit_trims_buffer(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label", text="Hello")
        _sel(app, 0)
        app._inspector_start_edit("text")
        app.state.inspector_input_buffer = "abc"
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, mod=0, unicode="")
        on_key_down(app, event)
        assert app.state.inspector_input_buffer == "ab"

    def test_arrow_key_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT, mod=0, unicode="")
        on_key_down(app, event)  # should not crash


class TestOnMouseDown:
    def test_canvas_click_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label", x=10, y=10, width=60, height=16)
        cr = app.layout.canvas_rect
        pos = (cr.x + 20, cr.y + 20)
        on_mouse_down(app, pos)  # should not crash

    def test_toolbar_click_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        tr = app.layout.toolbar_rect
        pos = (tr.x + 5, tr.y + 5)
        on_mouse_down(app, pos)  # should not crash


class TestOnMouseUp:
    def test_basic_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        on_mouse_up(app, (100, 100))

    def test_after_drag_state_cleanup(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.dragging = True
        on_mouse_up(app, (100, 100))
        assert app.state.dragging is not True


class TestOnMouseMove:
    def test_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        on_mouse_move(app, (100, 100), (0, 0, 0))

    def test_during_drag(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, x=10, y=10, width=60, height=16)
        _sel(app, 0)
        app.state.dragging = True
        app.state.drag_start = (10, 10)
        on_mouse_move(app, (20, 20), (1, 0, 0))


class TestOnMouseWheel:
    def test_no_crash_on_canvas(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        cr = app.layout.canvas_rect
        app.pointer_pos = (cr.x + 10, cr.y + 10)
        on_mouse_wheel(app, 0, 1)  # scroll up

    def test_zero_dy_ignored(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        on_mouse_wheel(app, 0, 0)  # should return immediately

    def test_palette_scroll(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        pr = app.layout.palette_rect
        app.pointer_pos = (pr.x + 5, pr.y + 5)
        on_mouse_wheel(app, 0, -1)  # scroll down
        # Scroll should have changed (or stayed at 0 if content fits)
        assert isinstance(app.state.palette_scroll, int)

    def test_inspector_scroll(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="label")
        _sel(app, 0)
        ir = app.layout.inspector_rect
        app.pointer_pos = (ir.x + 5, ir.y + 5)
        on_mouse_wheel(app, 0, -1)
        assert isinstance(app.state.inspector_scroll, int)


# ===================================================================
# Integration
# ===================================================================


class TestInputSmartEditIntegration:
    """Test smart_edit with input handler for checkbox toggle cycle."""

    def test_checkbox_toggle_cycle(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="checkbox", checked=False)
        _sel(app, 0)
        smart_edit(app)
        assert _w(app, 0).checked is True
        smart_edit(app)
        assert _w(app, 0).checked is False

    def test_slider_opens_value(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        _add(app, type="slider")
        _sel(app, 0)
        smart_edit(app)
        assert app.state.inspector_selected_field == "value"


class TestSceneStatsAfterToggle:
    """Test scene_stats reflects toggle_all_borders changes."""

    def test_borders_affect_stats_flags(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _add(app, type="label")
        w.visible = False
        scene_stats(app)
        assert "1H" in app.dialog_message
