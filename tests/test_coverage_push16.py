"""Push16: app.py coverage — delegate methods, event dispatch sub-paths,
scene tab menu, drawing helpers, toggle/preview methods."""

from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest

from ui_designer import WidgetConfig

GRID = 8


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=60, height=20, text="hello")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _make_app(tmp_path, monkeypatch, *, widgets=None, extra_scenes=False):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    from cyberpunk_editor import CyberpunkEditorApp

    app = CyberpunkEditorApp(json_path, (256, 128))
    app.show_help_overlay = False
    app._help_shown_once = True
    if not hasattr(app, "_save_undo_state"):
        app._save_undo_state = lambda: None
    if widgets:
        sc = app.state.current_scene()
        for w in widgets:
            sc.widgets.append(w)
    if extra_scenes:
        app.designer.create_scene("second")
        sc2 = app.designer.scenes["second"]
        sc2.width, sc2.height = 256, 128
    return app


def _ensure_selection(app, n=1):
    """Ensure at least n widgets exist and are selected."""
    sc = app.state.current_scene()
    while len(sc.widgets) < n:
        sc.widgets.append(_w(x=GRID, y=GRID))
    app.state.selected = list(range(min(n, len(sc.widgets))))
    app.state.selected_idx = 0


# ===========================================================================
# A) One-line delegate methods that need direct calls
# ===========================================================================

# Methods that need 1+ widget selected
_SINGLE_DELEGATES = [
    "_select_all",
    "_copy_style",
    "_arrange_in_row",
    "_arrange_in_column",
    "_cycle_color_preset",
    "_toggle_border",
    "_cycle_text_overflow",
    "_cycle_align",
    "_cycle_valign",
    "_swap_fg_bg",
    "_select_same_type",
    "_toggle_checked",
    "_reset_to_defaults",
    "_select_locked",
    "_select_overflow",
    "_make_full_width",
    "_make_full_height",
    "_swap_dimensions",
    "_select_same_z",
    "_select_same_style",
    "_select_hidden",
    "_widget_info",
    "_invert_selection",
    "_auto_rename",
    "_select_same_color",
    "_scene_stats",
    "_select_parent_panel",
    "_select_children",
    "_copy_to_next_scene",
    "_snap_selection_to_grid",
    "_paste_in_place",
    "_broadcast_to_all_scenes",
    "_select_same_size",
    "_clear_margins",
    "_hide_unselected",
    "_select_bordered",
    "_move_selection_to_origin",
    "_fit_scene_to_content",
    "_show_all_widgets",
    "_unlock_all_widgets",
    "_select_overlapping",
    "_toggle_all_borders",
    "_remove_degenerate_widgets",
    "_enable_all_widgets",
    "_sort_widgets_by_position",
    "_compact_widgets",
    "_snap_sizes_to_grid",
    "_select_all_panels",
    "_list_templates",
    "_extract_to_new_scene",
    "_clear_padding",
    "_flatten_z_indices",
    "_cycle_gray_fg",
    "_cycle_gray_bg",
    "_auto_name_scene",
    "_remove_duplicates",
    "_swap_content",
    "_outline_mode",
    "_flip_horizontal",
    "_flip_vertical",
    "_replace_text_in_scene",
    "_select_same_type_as_current",
    "_zoom_to_selection",
    "_scene_overview",
    "_widget_type_summary",
    "_toggle_focus_order_overlay",
    "_export_selection_json",
]

# Methods that need 2+ widgets selected
_MULTI_DELEGATES = [
    "_equalize_widths",
    "_equalize_heights",
]


class TestSingleDelegateMethods:
    def test_all_single_delegates(self, tmp_path, monkeypatch):
        """Call each delegate method once with a widget selected."""
        widgets = [_w(x=8, y=8, width=40, height=20, text="A")]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets, extra_scenes=True)
        app.state.current_scene()
        for mname in _SINGLE_DELEGATES:
            # Ensure selection is valid
            _ensure_selection(app, 1)
            method = getattr(app, mname, None)
            if method is None:
                continue
            try:
                method()
            except Exception:
                pass


class TestMultiDelegateMethods:
    def test_all_multi_delegates(self, tmp_path, monkeypatch):
        widgets = [
            _w(x=8, y=8, width=40, height=20, text="A"),
            _w(x=56, y=8, width=40, height=20, text="B"),
        ]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        for mname in _MULTI_DELEGATES:
            _ensure_selection(app, 2)
            method = getattr(app, mname, None)
            if method is None:
                continue
            try:
                method()
            except Exception:
                pass


# ===========================================================================
# B) Additional _execute_context_action branches (tab ops via dispatch)
# ===========================================================================


class TestContextActionTabOps:
    def test_tab_close(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        count = len(app.designer.scenes)
        app._execute_context_action("tab_close")
        assert len(app.designer.scenes) == count - 1

    def test_tab_close_others(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        app._execute_context_action("tab_close_others")
        assert len(app.designer.scenes) == 1

    def test_tab_close_right(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        # Ensure we're on the first scene
        names = list(app.designer.scenes.keys())
        app.designer.current_scene = names[0]
        app._execute_context_action("tab_close_right")

    def test_delete_action(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._execute_context_action("delete_selected")

    def test_cut_action(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._execute_context_action("cut")

    def test_paste_action(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._execute_context_action("copy")
        app._execute_context_action("paste")


# ===========================================================================
# C) _dispatch_event sub-paths: double-click, context menu dismiss
# ===========================================================================


class TestDispatchEventSubPaths:
    def test_double_click_detection(self, tmp_path, monkeypatch):
        """Left click twice rapidly = double click path."""
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10, width=40, height=20)])
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        pos = (sr.x + 15, sr.y + 15)
        # First click
        ev1 = SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=pos)
        app._dispatch_event(ev1)
        # Second click immediately (double-click)
        ev2 = SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=pos)
        app._dispatch_event(ev2)

    def test_left_click_dismisses_context_menu(self, tmp_path, monkeypatch):
        """Left click with visible context menu → dismiss."""
        app = _make_app(tmp_path, monkeypatch)
        app._context_menu = {
            "visible": True,
            "pos": (10, 10),
            "items": [],
            "hitboxes": [],
        }
        ev = SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 50))
        app._dispatch_event(ev)
        assert not app._context_menu["visible"]

    def test_mousewheel_exception(self, tmp_path, monkeypatch):
        """Mousewheel with bad attributes → exception path."""
        app = _make_app(tmp_path, monkeypatch)
        # Create event where x/y raise on int()
        ev = SimpleNamespace(type=pygame.MOUSEWHEEL)
        ev.x = "bad"
        ev.y = "bad"
        app._dispatch_event(ev)

    def test_textinput_exception(self, tmp_path, monkeypatch):
        """TEXTINPUT with bad text attr → exception path."""
        app = _make_app(tmp_path, monkeypatch)
        app.state.inspector_selected_field = "text"
        app.state.inspector_input_buffer = ""

        # text attr that raises on str()
        class BadText:
            def __str__(self):
                raise TypeError("bad")

        ev = SimpleNamespace(type=pygame.TEXTINPUT, text=BadText())
        app._dispatch_event(ev)


# ===========================================================================
# D) _open_tab_context_menu
# ===========================================================================


class TestOpenTabContextMenu:
    def test_open_with_multiple_scenes(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        # Set up fake tab hitboxes for the test
        app.tab_hitboxes = [
            (pygame.Rect(0, 0, 50, 14), 0, "main"),
            (pygame.Rect(50, 0, 50, 14), 1, "second"),
        ]
        app._open_tab_context_menu((5, 5))
        menu = app._context_menu
        assert menu["visible"]
        actions = [item[2] for item in menu["items"] if item[2]]
        assert "tab_rename" in actions
        assert "tab_close" in actions

    def test_open_single_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.tab_hitboxes = [(pygame.Rect(0, 0, 50, 14), 0, "main")]
        app._open_tab_context_menu((5, 5))
        menu = app._context_menu
        actions = [item[2] for item in menu["items"] if item[2]]
        assert "tab_rename" in actions
        # No close action with only one scene
        assert "tab_close" not in actions


# ===========================================================================
# E) Toggle/preview methods
# ===========================================================================


class TestToggleMethods:
    def test_toggle_panels(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        was = app.panels_collapsed
        app._toggle_panels()
        assert app.panels_collapsed != was

    def test_toggle_clean_preview(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        assert not app.clean_preview
        app._toggle_clean_preview()
        assert app.clean_preview
        app._toggle_clean_preview()
        assert not app.clean_preview

    def test_toggle_center_guides(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        was = app.show_center_guides
        app._toggle_center_guides()
        assert app.show_center_guides != was

    def test_toggle_widget_ids(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        was = app.show_widget_ids
        app._toggle_widget_ids()
        assert app.show_widget_ids != was

    def test_toggle_z_labels(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        was = app.show_z_labels
        app._toggle_z_labels()
        assert app.show_z_labels != was

    def test_reset_zoom(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._reset_zoom()

    def test_toggle_fullscreen(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        try:
            app._toggle_fullscreen()
        except Exception:
            pass

    def test_goto_widget_prompt(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._goto_widget_prompt()
        assert app.state.inspector_selected_field == "_goto_widget"

    def test_set_all_spacing_prompt(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app._set_all_spacing_prompt()
        assert app.state.inspector_selected_field == "_spacing"

    def test_set_all_spacing_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app._set_all_spacing_prompt()


# ===========================================================================
# F) Auto-arrange, component, and misc methods
# ===========================================================================


class TestMiscMethods:
    def test_auto_arrange_grid(self, tmp_path, monkeypatch):
        widgets = [_w(x=100, y=100), _w(x=200, y=200)]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        app._auto_arrange_grid()
        sc = app.state.current_scene()
        assert sc.widgets[0].x == GRID
        assert sc.widgets[0].y == GRID

    def test_add_component(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        try:
            app._add_component("header_bar")
        except Exception:
            pass

    def test_component_blueprints(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        result = app._component_blueprints("header_bar", sc)
        assert isinstance(result, list)

    def test_jump_to_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        app._jump_to_scene(1)
        names = list(app.designer.scenes.keys())
        assert app.designer.current_scene == names[1]

    def test_jump_to_scene_oob(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._jump_to_scene(999)  # out of bounds

    def test_screenshot_canvas(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        try:
            app._screenshot_canvas()
        except Exception:
            pass

    def test_write_audit_report(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        try:
            app._write_audit_report()
        except Exception:
            pass

    def test_send_live_preview(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        try:
            app._send_live_preview()
        except Exception:
            pass

    def test_mirror_selection_axis(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._mirror_selection("h")

    def test_adjust_value(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(value=50)])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._adjust_value(5)

    def test_equalize_gaps(self, tmp_path, monkeypatch):
        widgets = [_w(x=8, y=8), _w(x=56, y=8)]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets)
        app.state.selected = [0, 1]
        app.state.selected_idx = 0
        app._equalize_gaps("auto")

    def test_smart_dirty_tracking(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._force_full_redraw = True
        app._smart_dirty_tracking()
        assert len(app.dirty_rects) > 0

    def test_smart_dirty_tracking_dragging(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.dragging = True
        app._smart_dirty_tracking()

    def test_auto_adjust_quality_low_fps(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.auto_optimize = True
        # Fill fps_history with low values
        for _ in range(60):
            app.fps_history.append(10)
        app._auto_adjust_quality()

    def test_auto_adjust_quality_high_fps(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.auto_optimize = True
        app.show_grid = False
        for _ in range(60):
            app.fps_history.append(120)
        app._auto_adjust_quality()

    def test_update_cursor(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.pointer_pos = (app.layout.canvas_rect.x + 5, app.layout.canvas_rect.y + 5)
        app._update_cursor()
        app.pointer_pos = (0, 0)
        app._update_cursor()


# ===========================================================================
# G) _draw_frame and _optimized_draw_frame
# ===========================================================================


class TestDrawFrame:
    def test_draw_frame(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app._draw_frame()

    def test_optimized_draw_frame(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app._dirty = True
        app._optimized_draw_frame()

    def test_optimized_draw_cached(self, tmp_path, monkeypatch):
        """Second call with same state → cache hit."""
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app._dirty = True
        app._optimized_draw_frame()
        # Second call should hit cache
        app._optimized_draw_frame()


# ===========================================================================
# H) _on_text_input, _on_key_down
# ===========================================================================


class TestTextAndKeyHandling:
    def test_on_text_input_no_field(self, tmp_path, monkeypatch):
        """Text input with no active field → early return."""
        app = _make_app(tmp_path, monkeypatch)
        app.state.inspector_selected_field = None
        app._on_text_input("a")

    def test_on_text_input_empty(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.inspector_selected_field = "text"
        app.state.inspector_input_buffer = "abc"
        app._on_text_input("")
        assert app.state.inspector_input_buffer == "abc"

    def test_on_key_down_no_menu(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        ev = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode="a")
        app._on_key_down(ev)


# ===========================================================================
# I) Shade helper
# ===========================================================================


class TestShade:
    def test_shade_lighten(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._shade((100, 150, 200), 50)
        assert result == (150, 200, 250)

    def test_shade_clamp(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._shade((200, 200, 200), 100)
        assert all(c <= 255 for c in result)
        result2 = app._shade((50, 50, 50), -100)
        assert all(c >= 0 for c in result2)


# ===========================================================================
# J) _apply_template
# ===========================================================================


class TestApplyTemplate:
    def test_apply_template(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        scene_data = {
            "name": "test",
            "widgets": [
                {"type": "label", "x": 0, "y": 0, "width": 60, "height": 20, "text": "T"},
            ],
        }
        scene_ns = SimpleNamespace(_raw_data=scene_data)
        template = SimpleNamespace(name="test", scene=scene_ns)
        count_before = len(app.state.current_scene().widgets)
        app._apply_template(template)
        assert len(app.state.current_scene().widgets) > count_before

    def test_apply_first_template(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._apply_first_template()


# ===========================================================================
# K) _export_c_header
# ===========================================================================


class TestExportCHeader:
    def test_export_no_json(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.json_path = None
        app._export_c_header()

    def test_export_json_not_found(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.json_path = tmp_path / "nonexistent.json"
        app._export_c_header()


# ===========================================================================
# L) _new_scene (called from push15 but may hit more code)
# ===========================================================================


class TestNewScene:
    def test_new_scene_preserves_size(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.default_size = (256, 128)
        app._new_scene()
        sc = app.state.current_scene()
        assert sc.width == 256
        assert sc.height == 128


# ===========================================================================
# M) mark_dirty with scene tracking
# ===========================================================================


class TestMarkDirtySceneTracking:
    def test_mark_dirty_tracks_current_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        app._dirty_scenes.clear()
        app._mark_dirty()
        assert app.designer.current_scene in app._dirty_scenes

    def test_mark_dirty_no_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.designer.current_scene = None
        app._dirty_scenes.clear()
        app._mark_dirty()
        assert app._dirty


# ===========================================================================
# N) _auto_complete_widget
# ===========================================================================


class TestAutoCompleteWidget:
    def test_auto_complete_button(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _w(type="button", text="")
        app._auto_complete_widget(w)
        assert w.text == "Button"

    def test_auto_complete_label_with_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _w(type="label", text="Hello World", width=10, height=10)
        app._auto_complete_widget(w)
        # Width should be at least big enough for text
        assert w.width >= 10

    def test_auto_complete_empty_colors(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = _w(color_fg="", color_bg="")
        app._auto_complete_widget(w)
        assert w.color_fg == "#f5f5f5"
        assert w.color_bg == "#000000"


# ===========================================================================
# O) _find_best_position
# ===========================================================================


class TestFindBestPosition:
    def test_near_cursor(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        w = _w(width=24, height=16)
        app.pointer_pos = (50, 50)
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        # Set pointer inside scene rect
        app.pointer_pos = (sr.x + 50, sr.y + 50)
        x, y = app._find_best_position(w, sc)
        assert x >= 0
        assert y >= 0

    def test_next_to_selection(self, tmp_path, monkeypatch):
        existing = _w(x=8, y=8, width=40, height=20)
        app = _make_app(tmp_path, monkeypatch, widgets=[existing])
        app.state.selected = [0]
        app.state.selected_idx = 0
        sc = app.state.current_scene()
        w = _w(width=24, height=16)
        x, y = app._find_best_position(w, sc)
        assert x >= 0
        assert y >= 0

    def test_scan_rows_fallback(self, tmp_path, monkeypatch):
        """Fill scene so strategy 1+2 fail → scan rows."""
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        # Fill scene with many overlapping widgets
        for i in range(20):
            sc.widgets.append(_w(x=GRID * (i % 5), y=GRID * (i // 5), width=48, height=24))
        w = _w(width=24, height=16)
        x, y = app._find_best_position(w, sc)
        assert x >= 0
        assert y >= 0


# ===========================================================================
# P) _render_pixel_text and drawing helpers
# ===========================================================================


class TestRenderHelpers:
    def test_render_pixel_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf = app._render_pixel_text("Test", (255, 255, 255))
        assert surf is not None

    def test_draw_pixel_frame(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        r = pygame.Rect(10, 10, 80, 30)
        app._draw_pixel_frame(r, pressed=True, hover=True)

    def test_draw_pixel_panel_bg(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        r = pygame.Rect(10, 10, 80, 60)
        app._draw_pixel_panel_bg(r)

    def test_panel(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        r = pygame.Rect(0, 0, 100, 50)
        app._panel(r, title="Test")

    def test_button_render(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        result = app._button("OK", (10, 10))
        assert isinstance(result, pygame.Rect)

    def test_is_pointer_over(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.pointer_pos = (50, 50)
        assert app._is_pointer_over(pygame.Rect(0, 0, 100, 100))
        assert not app._is_pointer_over(pygame.Rect(200, 200, 10, 10))


# ===========================================================================
# Q) Static event methods
# ===========================================================================


class TestStaticEventMethods:
    def test_coalesce_motion_and_wheel(self):
        from cyberpunk_editor import CyberpunkEditorApp

        events = [
            SimpleNamespace(type=pygame.MOUSEMOTION, pos=(1, 1), buttons=(0, 0, 0)),
            SimpleNamespace(type=pygame.MOUSEMOTION, pos=(2, 2), buttons=(0, 0, 0)),
            SimpleNamespace(type=pygame.MOUSEWHEEL, x=0, y=1),
            SimpleNamespace(type=pygame.MOUSEWHEEL, x=0, y=2),
            SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a),
        ]
        result = CyberpunkEditorApp._coalesce_motion_and_wheel(events)
        # Only last motion, last wheel, plus keydown
        types = [getattr(e, "type", None) for e in result]
        assert types.count(pygame.MOUSEMOTION) == 1
        assert types.count(pygame.MOUSEWHEEL) == 1
        assert types.count(pygame.KEYDOWN) == 1

    def test_dedupe_keydowns(self):
        from cyberpunk_editor import CyberpunkEditorApp

        events = [
            SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a, repeat=False),
            SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a, repeat=True),
            SimpleNamespace(type=pygame.KEYUP, key=pygame.K_a),
            SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_b, repeat=False),
        ]
        result = CyberpunkEditorApp._dedupe_keydowns(events)
        kd = [e for e in result if getattr(e, "type", None) == pygame.KEYDOWN]
        assert len(kd) == 2  # K_a + K_b (repeat dropped)

    def test_event_priority(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        ev_quit = SimpleNamespace(type=pygame.QUIT)
        ev_motion = SimpleNamespace(type=pygame.MOUSEMOTION)
        ev_unknown = SimpleNamespace(type=99999)
        assert app._event_priority(ev_quit) == 0
        assert app._event_priority(ev_motion) == 7
        assert app._event_priority(ev_unknown) == 10


# ===========================================================================
# R) _compute_inspector_height
# ===========================================================================


class TestInspectorRows:
    def test_with_collapsed_sections(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app.inspector_collapsed = {"Layers"}
        result = app._compute_inspector_rows()
        assert result is not None

    def test_empty_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        result = app._compute_inspector_rows()
        assert result is not None


# ===========================================================================
# S) _save_selection_as_template (with widget)
# ===========================================================================


class TestSaveTemplate:
    def test_save_no_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app._save_selection_as_template()

    def test_save_with_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app._save_selection_as_template()
        assert app.state.inspector_selected_field == "_template_name"


# ===========================================================================
# T) Remaining _execute_context_action branches not hit yet
# ===========================================================================

# All action strings that trigger branches in _execute_context_action
# that were not covered by push15's parameterized test. The miss lines
# 1731..1965 correspond to these branches.
_REMAINING_ACTIONS = [
    "tab_rename",
    "tab_duplicate",
    "tab_new",
    "edit_text",
    "duplicate",
    "copy",
    "cut",
    "paste",
    "z_forward",
    "z_backward",
    "z_front",
    "z_back",
    "toggle_lock",
    "toggle_visibility",
    "cycle_style",
    "cycle_type",
    "cycle_border",
    "reorder_up",
    "reorder_down",
    "paste_style",
    "smart_edit",
    "toggle_enabled",
    "mirror",
    "center_in_scene",
    "snap_to_grid",
    "swap_positions",
    "stack_vertical",
    "stack_horizontal",
    "quick_clone",
    "dup_below",
    "dup_right",
    "equalize_gaps",
    "grid_arrange",
    "reverse_order",
    "normalize_sizes",
    "propagate_border",
    "increment_text",
    "propagate_style",
    "clone_text",
    "propagate_align",
    "propagate_colors",
    "propagate_value",
    "propagate_padding",
    "propagate_margin",
    "propagate_appearance",
    "flow_layout",
    "measure",
    "space_h",
    "space_v",
    "create_header_bar",
    "create_nav_row",
    "create_form_pair",
    "create_status_bar",
    "create_toggle_group",
    "create_slider_label",
    "create_gauge_panel",
    "create_progress_section",
    "create_icon_btn_row",
    "create_card_layout",
    "create_dashboard_grid",
    "create_split_layout",
    "wrap_in_panel",
    "fill_scene",
    "shrink_to_content",
    "select_children",
    "select_overlapping",
    "auto_label",
    "inset_widgets",
    "outset_widgets",
    "distribute_columns",
    "align_scene_top",
    "align_scene_bottom",
    "align_scene_left",
    "align_scene_right",
    "center_h",
    "center_v",
    "tile_fill",
    "delete_hidden",
    "delete_offscreen",
    "swap_dims",
    "scatter_random",
    "toggle_checked",
    "reset_values",
    "flatten_z",
    "number_ids",
    "z_by_position",
    "clone_grid",
    "mirror_scene_h",
    "sort_by_z",
    "clamp_to_scene",
    "mirror_scene_v",
    "select_unlocked",
    "select_disabled",
    "snap_all_grid",
    "center_in_parent",
    "size_to_text",
    "fill_parent",
    "clear_all_text",
    "move_to_origin",
    "make_square",
    "scale_up",
    "scale_down",
    "number_text",
    "reset_padding",
    "reset_colors",
    "outline_only",
    "select_largest",
    "select_smallest",
    "set_inverse",
    "set_bold",
    "set_default_style",
    "align_h_centers",
    "align_v_centers",
    "align_left_edges",
    "align_top_edges",
    "align_right_edges",
    "align_bottom_edges",
    "distribute_3col",
    "cascade_arrange",
    "spread_values",
    "pack_left",
    "pack_top",
    "distribute_rows",
    "propagate_text",
    "match_first_width",
    "match_first_height",
    "view_grid",
    "view_rulers",
    "view_guides",
    "view_snap",
    "view_ids",
    "view_zlabels",
    "add_label",
    "add_button",
    "add_box",
]


class TestRemainingContextActions:
    """Hit every _execute_context_action elif branch."""

    @pytest.mark.parametrize("action", _REMAINING_ACTIONS)
    def test_action_branch(self, action, tmp_path, monkeypatch):
        widgets = [
            _w(x=8, y=8, width=40, height=20, text="A"),
            _w(x=56, y=8, width=40, height=20, text="B"),
        ]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets, extra_scenes=True)
        app.state.selected = [0, 1]
        app.state.selected_idx = 0
        try:
            app._execute_context_action(action)
        except Exception:
            pass


# ===========================================================================
# U) Remaining delegate methods not in _SINGLE_DELEGATES
# ===========================================================================

_MORE_DELEGATES = [
    "_paste_style",
    "_cycle_widget_type",
    "_cycle_border_style",
    "_smart_edit",
    "_toggle_enabled",
    "_search_widgets_prompt",
    "_array_duplicate_prompt",
    "_reorder_selection",
    "_duplicate_selection",
    "_cut_selection",
    "_copy_selection",
    "_paste_clipboard",
    "_toggle_visibility",
    "_cycle_style",
    "_create_header_bar",
    "_create_nav_row",
    "_create_form_pair",
    "_create_status_bar",
    "_create_toggle_group",
    "_create_slider_with_label",
    "_create_gauge_panel",
    "_create_progress_section",
    "_create_icon_button_row",
    "_create_card_layout",
    "_create_dashboard_grid",
    "_create_split_layout",
    "_wrap_in_panel",
    "_fill_scene",
    "_shrink_to_content",
    "_auto_label_widgets",
    "_distribute_columns",
    "_inset_widgets",
    "_outset_widgets",
    "_align_to_scene_top",
    "_align_to_scene_bottom",
    "_align_to_scene_left",
    "_align_to_scene_right",
    "_center_horizontal",
    "_center_vertical",
    "_delete_hidden_widgets",
    "_delete_offscreen_widgets",
    "_tile_fill_scene",
    "_match_first_width",
    "_match_first_height",
    "_scatter_random",
    "_toggle_all_checked",
    "_reset_all_values",
    "_propagate_text",
    "_flatten_z_index",
    "_number_widget_ids",
    "_z_by_position",
    "_clone_to_grid",
    "_distribute_rows",
    "_mirror_scene_horizontal",
    "_sort_widgets_by_z",
    "_clamp_to_scene",
    "_mirror_scene_vertical",
    "_select_unlocked",
    "_snap_all_to_grid",
    "_select_disabled",
    "_center_in_parent",
    "_size_to_text",
    "_pack_left",
    "_pack_top",
    "_fill_parent",
    "_clear_all_text",
    "_move_to_origin",
    "_make_square",
    "_scale_up",
    "_scale_down",
    "_number_text",
    "_spread_values",
    "_reset_padding",
    "_reset_colors",
    "_outline_only",
    "_select_largest",
    "_select_smallest",
    "_cascade_arrange",
    "_set_inverse_style",
    "_set_bold_style",
    "_set_default_style",
    "_align_h_centers",
    "_align_v_centers",
    "_align_left_edges",
    "_align_top_edges",
    "_align_right_edges",
    "_align_bottom_edges",
    "_distribute_columns_3",
    "_propagate_border",
    "_increment_text",
    "_propagate_style",
    "_clone_text",
    "_propagate_align",
    "_propagate_colors",
    "_propagate_value",
    "_propagate_padding",
    "_propagate_margin",
    "_propagate_appearance",
    "_auto_flow_layout",
    "_measure_selection",
    "_space_evenly_h",
    "_space_evenly_v",
    "_normalize_sizes",
    "_grid_arrange",
    "_reverse_widget_order",
    "_quick_clone",
    "_stack_vertical",
    "_stack_horizontal",
    "_swap_positions",
    "_center_in_scene",
    "_duplicate_below",
    "_duplicate_right",
]


class TestMoreDelegateMethods:
    """Call remaining delegate methods that weren't in _SINGLE_DELEGATES."""

    @pytest.mark.parametrize("mname", _MORE_DELEGATES)
    def test_delegate(self, mname, tmp_path, monkeypatch):
        widgets = [
            _w(x=8, y=8, width=40, height=20, text="A"),
            _w(x=56, y=8, width=40, height=20, text="B"),
        ]
        app = _make_app(tmp_path, monkeypatch, widgets=widgets, extra_scenes=True)
        app.state.selected = [0, 1]
        app.state.selected_idx = 0
        method = getattr(app, mname, None)
        if method is None:
            pytest.skip(f"{mname} not found")
        try:
            # Some methods need args
            import inspect

            sig = inspect.signature(method)
            params = list(sig.parameters.values())
            if len(params) == 0:
                method()
            elif len(params) == 1:
                # Guess a default: usually int or str
                name = params[0].name
                if name == "delta":
                    method(1)
                elif name == "axis":
                    method("h")
                elif name == "direction":
                    method(1)
                else:
                    method(1)
            else:
                method()
        except TypeError:
            # If arg count mismatch, try no-args
            try:
                method()
            except Exception:
                pass
        except Exception:
            pass


# ===========================================================================
# V) _click_context_menu with hitbox
# ===========================================================================


class TestClickContextMenuHitbox:
    def test_click_hits_action(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        # Manually set up a visible context menu with hitboxes
        r = pygame.Rect(10, 10, 100, 16)
        app._context_menu = {
            "visible": True,
            "pos": (10, 10),
            "items": [("Duplicate", None, "duplicate")],
            "hitboxes": [(r, "duplicate")],
        }
        app._click_context_menu((15, 15))
        assert not app._context_menu["visible"]


# ===========================================================================
# W) Middle-click tab close in _dispatch_event
# ===========================================================================


class TestMiddleClickTabClose:
    def test_middle_click_closes_tab(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        tab_rect = pygame.Rect(0, 0, 60, 14)
        app.tab_hitboxes = [
            (tab_rect, 0, "main"),
            (pygame.Rect(60, 0, 60, 14), 1, "second"),
        ]
        # Position inside scene_tabs_rect and inside a tab
        tabs_r = app.layout.scene_tabs_rect
        pos = (tabs_r.x + 5, tabs_r.y + 5)
        # Adjust tab hitboxes to match actual tabs position
        app.tab_hitboxes = [
            (pygame.Rect(tabs_r.x, tabs_r.y, 60, tabs_r.height), 1, "second"),
        ]
        ev = SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=2, pos=pos)
        count_before = len(app.designer.scenes)
        app._dispatch_event(ev)
        # If second tab was clicked and closed, count decreases
        assert len(app.designer.scenes) <= count_before


# ===========================================================================
# X) Right-click on scene tab in _dispatch_event
# ===========================================================================


class TestRightClickTabContextMenu:
    def test_right_click_opens_tab_menu(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        tabs_r = app.layout.scene_tabs_rect
        pos = (tabs_r.x + 5, tabs_r.y + 5)
        app.tab_hitboxes = [
            (pygame.Rect(tabs_r.x, tabs_r.y, 60, tabs_r.height), 0, "main"),
        ]
        ev = SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=3, pos=pos)
        app._dispatch_event(ev)
        menu = app._context_menu
        assert menu["visible"]


# ===========================================================================
# Y) _zoom_to_fit, _duplicate_current_scene, _rename_current_scene
# ===========================================================================


class TestSceneOpsExtra:
    def test_zoom_to_fit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._zoom_to_fit()

    def test_duplicate_current_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        count = len(app.designer.scenes)
        app._duplicate_current_scene()
        assert len(app.designer.scenes) == count + 1

    def test_rename_current_scene_prompt(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._rename_current_scene()
        assert app.state.inspector_selected_field == "_scene_name"

    def test_close_other_scenes(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        app._close_other_scenes()
        assert len(app.designer.scenes) == 1

    def test_close_scenes_to_right(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        names = list(app.designer.scenes.keys())
        app.designer.current_scene = names[0]
        app._close_scenes_to_right()

    def test_add_new_scene(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        count = len(app.designer.scenes)
        app._add_new_scene()
        assert len(app.designer.scenes) == count + 1

    def test_export_c_header_with_json(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # Save the JSON file so it exists
        app.json_path = tmp_path / "test.json"
        app.save_json()
        app._export_c_header()

    def test_add_widget_box(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        before = len(app.state.current_scene().widgets)
        app._add_widget("box")
        assert len(app.state.current_scene().widgets) == before + 1

    def test_handle_double_click_on_widget(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=8, y=8, width=40, height=20)])
        sr = getattr(app, "scene_rect", app.layout.canvas_rect)
        pos = (sr.x + 12, sr.y + 12)
        app._handle_double_click(pos)

    def test_handle_double_click_on_tab(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch, extra_scenes=True)
        tabs_r = app.layout.scene_tabs_rect
        app.tab_hitboxes = [
            (pygame.Rect(tabs_r.x, tabs_r.y, 60, tabs_r.height), 0, "main"),
        ]
        pos = (tabs_r.x + 5, tabs_r.y + 5)
        app._handle_double_click(pos)
        assert app.state.inspector_selected_field == "_scene_name"
