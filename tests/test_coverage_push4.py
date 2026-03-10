"""Tests targeting uncovered branches in drawing modules: text, panels, overlays, canvas."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pygame

from ui_models import WidgetConfig

# ---------------------------------------------------------------------------
# Shared helpers (same pattern as push3)
# ---------------------------------------------------------------------------


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=60, height=20, text="hello")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _make_app(tmp_path, monkeypatch, *, widgets=None, snap=False):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    from cyberpunk_editor import CyberpunkEditorApp

    json_path = tmp_path / "scene.json"
    app = CyberpunkEditorApp(json_path, (256, 128))
    if not hasattr(app, "_save_undo_state"):
        app._save_undo_state = lambda: None
    if widgets:
        sc = app.state.current_scene()
        for w in widgets:
            sc.widgets.append(w)
    app.snap_enabled = snap
    return app


# ---------------------------------------------------------------------------
# drawing/text.py — wrap_text_px truncation, draw_text_clipped edges
# ---------------------------------------------------------------------------


class TestDrawingTextEdges:
    """Cover uncovered branches in drawing/text.py."""

    def test_wrap_text_px_multi_para_truncate(self, tmp_path, monkeypatch):
        """L60,68-69,96,99,110: wrap with multi-para text that hits max_lines."""
        from cyberpunk_designer.drawing.text import wrap_text_px

        app = _make_app(tmp_path, monkeypatch)
        # Long text with newlines → multiple paragraphs, will truncate at max_lines=2
        text = "Line one is fairly long text\nLine two also quite long\nLine three"
        result = wrap_text_px(app, text, max_width_px=200, max_lines=2, ellipsis="...")
        assert len(result) <= 2

    def test_wrap_text_px_no_stripped_paras(self, tmp_path, monkeypatch):
        """L60: paras = [s] when splitlines produces empty paragraphs."""
        from cyberpunk_designer.drawing.text import wrap_text_px

        app = _make_app(tmp_path, monkeypatch)
        # Text with only whitespace between newlines that strip to nothing
        result = wrap_text_px(app, "   ", max_width_px=200, max_lines=3)
        # "   ".strip() → "" → paras = ["   "] (original s)
        assert isinstance(result, list)

    def test_wrap_text_px_char_break(self, tmp_path, monkeypatch):
        """L96: break inside per-character splitting when max_lines hit."""
        from cyberpunk_designer.drawing.text import wrap_text_px

        app = _make_app(tmp_path, monkeypatch)
        # Very long word that must be broken char-by-char, with max_lines=1
        result = wrap_text_px(app, "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW", max_width_px=40, max_lines=1)
        assert len(result) == 1

    def test_wrap_text_px_truncate_with_ellipsis(self, tmp_path, monkeypatch):
        """L110: truncated=True → ellipsize last line."""
        from cyberpunk_designer.drawing.text import wrap_text_px

        app = _make_app(tmp_path, monkeypatch)
        # Text that needs 5+ lines but limited to 2 → truncated → last line ellipsized
        text = "word " * 100
        result = wrap_text_px(app, text, max_width_px=60, max_lines=2, ellipsis="...")
        assert len(result) <= 2

    def test_draw_text_clipped_device_exception(self, tmp_path, monkeypatch):
        """L139-140: canvas_rect.colliderect exception."""
        from cyberpunk_designer.drawing.text import draw_text_clipped
        from cyberpunk_designer.layout import Layout

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(app, "hardware_profile", "esp32os_256x128_gray4")
        # canvas_rect is a read-only property — patch on the class
        bad_rect = MagicMock()
        bad_rect.colliderect = MagicMock(side_effect=RuntimeError("bad"))
        monkeypatch.setattr(Layout, "canvas_rect", property(lambda self: bad_rect))

        surf = pygame.Surface((200, 100))
        rect = pygame.Rect(10, 10, 100, 50)
        draw_text_clipped(app, surf, "test", rect, (255, 255, 255), 2)

    def test_draw_text_clipped_empty_lines(self, tmp_path, monkeypatch):
        """L165: lines empty after processing → return."""
        from cyberpunk_designer.drawing.text import draw_text_clipped

        app = _make_app(tmp_path, monkeypatch)
        surf = pygame.Surface((200, 100))
        # Very narrow rect → text becomes empty
        rect = pygame.Rect(10, 10, 1, 50)
        draw_text_clipped(app, surf, "hello world", rect, (255, 255, 255), 0)

    def test_draw_text_clipped_clip_exception(self, tmp_path, monkeypatch):
        """L181-182: clip_rect.clip(old_clip) exception."""
        from cyberpunk_designer.drawing.text import draw_text_clipped

        app = _make_app(tmp_path, monkeypatch)
        surf = pygame.Surface((200, 100))
        # Set a bad existing clip that causes clip() to fail
        surf.set_clip(None)  # Reset clip
        rect = pygame.Rect(10, 10, 100, 50)
        draw_text_clipped(app, surf, "test text", rect, (255, 255, 255), 2)

    def test_draw_text_in_rect_device_exception(self, tmp_path, monkeypatch):
        """L220-221: colliderect exception in draw_text_in_rect."""
        from cyberpunk_designer.drawing.text import draw_text_in_rect
        from cyberpunk_designer.layout import Layout

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(app, "hardware_profile", "esp32os_256x128_gray4")
        bad_rect = MagicMock()
        bad_rect.colliderect = MagicMock(side_effect=RuntimeError("bad"))
        monkeypatch.setattr(Layout, "canvas_rect", property(lambda self: bad_rect))

        surf = pygame.Surface((200, 100))
        rect = pygame.Rect(10, 10, 100, 50)
        w = _w(text_overflow="ellipsis")
        draw_text_in_rect(app, surf, "test", rect, (255, 255, 255), 2, w)

    def test_draw_text_in_rect_invalid_overflow(self, tmp_path, monkeypatch):
        """L224: overflow not in valid set → default to 'ellipsis'."""
        from cyberpunk_designer.drawing.text import draw_text_in_rect

        app = _make_app(tmp_path, monkeypatch)
        surf = pygame.Surface((200, 100))
        rect = pygame.Rect(10, 10, 100, 50)
        w = _w()
        w.text_overflow = "INVALID_OVERFLOW"
        draw_text_in_rect(app, surf, "test", rect, (255, 255, 255), 2, w)

    def test_draw_text_in_rect_auto_device(self, tmp_path, monkeypatch):
        """L232-233,240: auto overflow with device profile."""
        from cyberpunk_designer.drawing.text import draw_text_in_rect

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(app, "hardware_profile", "esp32os_256x128_gray4")
        surf = pygame.Surface((256, 128))
        rect = pygame.Rect(10, 10, 80, 40)
        w = _w()
        w.text_overflow = "auto"
        # Long text that would overflow, tall enough for 2+ lines → use_wrap
        draw_text_in_rect(app, surf, "Long text " * 20, rect, (255, 255, 255), 2, w)

    def test_draw_text_in_rect_wrap_max_lines(self, tmp_path, monkeypatch):
        """L249-250: max_lines from widget attribute in wrap mode."""
        from cyberpunk_designer.drawing.text import draw_text_in_rect

        app = _make_app(tmp_path, monkeypatch)
        surf = pygame.Surface((200, 100))
        rect = pygame.Rect(10, 10, 100, 80)
        w = _w()
        w.text_overflow = "wrap"
        w.max_lines = 2
        draw_text_in_rect(app, surf, "word " * 50, rect, (255, 255, 255), 2, w)


# ---------------------------------------------------------------------------
# drawing/panels.py — exception branches, hover/shade
# ---------------------------------------------------------------------------


class TestDrawingPanelsEdges:
    """Cover uncovered branches in drawing/panels.py."""

    def test_draw_palette_content_h_exception(self, tmp_path, monkeypatch):
        """L24-25: _palette_content_height exception."""
        from cyberpunk_designer.drawing.panels import draw_palette

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app._palette_content_height = MagicMock(side_effect=RuntimeError("boom"))
        draw_palette(app)

    def test_draw_palette_scroll_exception(self, tmp_path, monkeypatch):
        """L30-31: palette_scroll normalization exception."""
        from cyberpunk_designer.drawing.panels import draw_palette

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])

        class BadScroll:
            def __int__(self):
                raise ValueError("bad")

        app.state.palette_scroll = BadScroll()
        draw_palette(app)

    def test_draw_palette_hover(self, tmp_path, monkeypatch):
        """L83: palette section hover → _shade(fill, 10)."""
        from cyberpunk_designer.drawing.panels import draw_palette

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        # Position pointer over the palette area to trigger hover
        r = app.layout.palette_rect
        app.pointer_pos = (r.centerx, r.centery)
        draw_palette(app)

    def test_draw_inspector_content_h_exception(self, tmp_path, monkeypatch):
        """L153-154: _inspector_content_height exception."""
        from cyberpunk_designer.drawing.panels import draw_inspector

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app._inspector_content_height = MagicMock(side_effect=RuntimeError("boom"))
        draw_inspector(app)

    def test_draw_inspector_scroll_exception(self, tmp_path, monkeypatch):
        """L159-160: inspector_scroll normalization exception."""
        from cyberpunk_designer.drawing.panels import draw_inspector

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]

        class BadScroll:
            def __int__(self):
                raise ValueError("bad")

        app.state.inspector_scroll = BadScroll()
        draw_inspector(app)

    def test_draw_inspector_hover(self, tmp_path, monkeypatch):
        """L191: inspector hover → _shade(hdr_fill, 12)."""
        from cyberpunk_designer.drawing.panels import draw_inspector

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        r = app.layout.inspector_rect
        app.pointer_pos = (r.centerx, r.centery)
        draw_inspector(app)

    def test_draw_inspector_locked_widget(self, tmp_path, monkeypatch):
        """L223: locked widget fill shade."""
        from cyberpunk_designer.drawing.panels import draw_inspector

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(locked=True)])
        app.state.selected = [0]
        draw_inspector(app)

    def test_draw_inspector_scene_target(self, tmp_path, monkeypatch):
        """L229-234: key with scene target 'scene:X' parsing."""
        from cyberpunk_designer.drawing.panels import draw_inspector

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        # The inspector rows may include scene: keys if widget has runtime bindings
        draw_inspector(app)


# ---------------------------------------------------------------------------
# drawing/overlays.py — tooltip edges, help overlay self-check
# ---------------------------------------------------------------------------


class TestDrawingOverlaysEdges:
    """Cover uncovered branches in drawing/overlays.py."""

    def test_tooltip_below_screen(self, tmp_path, monkeypatch):
        """L158: ty = ly - th - 4 when tooltip would go off-screen bottom."""
        from cyberpunk_designer.drawing.overlays import draw_tooltip

        app = _make_app(tmp_path, monkeypatch)
        # Set up so tooltip is showing after delay
        app._tooltip_key = "New scene (Ctrl+N)"
        app._tooltip_start = 0  # long ago
        # Create toolbar hitbox near bottom of screen
        bottom_y = app.logical_surface.get_height() - 5
        app.toolbar_hitboxes = [(pygame.Rect(50, bottom_y - 5, 40, 10), "new")]
        app.pointer_pos = (55, bottom_y)
        draw_tooltip(app)

    def test_context_menu_max_width(self, tmp_path, monkeypatch):
        """L51: tw > max_w for wide menu labels."""
        from cyberpunk_designer.drawing.overlays import draw_context_menu

        app = _make_app(tmp_path, monkeypatch)
        app._context_menu = {
            "visible": True,
            "pos": (10, 10),
            "items": [
                ("A" * 200, "a", lambda: None),
                ("Short", "b", lambda: None),
                ("---", None, None),  # separator
            ],
        }
        draw_context_menu(app)

    def test_tooltip_initial_display(self, tmp_path, monkeypatch):
        """L147: return before delay elapsed."""

        from cyberpunk_designer.drawing.overlays import draw_tooltip

        app = _make_app(tmp_path, monkeypatch)
        # Set up toolbar hitbox
        app.toolbar_hitboxes = [(pygame.Rect(40, 40, 40, 20), "new")]
        app.pointer_pos = (50, 50)
        # First call → new key → sets start time, returns
        draw_tooltip(app)
        # Second call within delay → elapsed < 0.5 → returns
        draw_tooltip(app)

    def test_help_overlay_full(self, tmp_path, monkeypatch):
        """L319-427: help overlay with scene info, resource estimation, etc."""
        from cyberpunk_designer.drawing.overlays import draw_help_overlay

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.show_help_overlay = True
        app.state.selected = [0]
        draw_help_overlay(app)

    def test_help_overlay_scene_exception(self, tmp_path, monkeypatch):
        """L319-320: current_scene() exception in help overlay."""
        from cyberpunk_designer.drawing.overlays import draw_help_overlay

        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        app.state.current_scene = MagicMock(side_effect=RuntimeError("boom"))
        draw_help_overlay(app)

    def test_help_overlay_profile_exception(self, tmp_path, monkeypatch):
        """L326-327: HARDWARE_PROFILES[profile].get() exception."""
        from cyberpunk_designer.drawing.overlays import draw_help_overlay

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.show_help_overlay = True
        app.hardware_profile = "esp32os_256x128_gray4"
        draw_help_overlay(app)

    def test_help_overlay_dims_exception(self, tmp_path, monkeypatch):
        """L336-337: scene_dims exception."""
        from cyberpunk_designer.drawing.overlays import draw_help_overlay

        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        sc = app.state.current_scene()
        sc.width = MagicMock(side_effect=ValueError("bad"))
        draw_help_overlay(app)

    def test_help_overlay_widgets_count_exception(self, tmp_path, monkeypatch):
        """L340-341: widgets_count exception."""
        from cyberpunk_designer.drawing.overlays import draw_help_overlay

        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True

        class BadWidgets:
            def __len__(self):
                raise RuntimeError("bad")

        sc = app.state.current_scene()
        sc.widgets = BadWidgets()
        draw_help_overlay(app)

    def test_help_overlay_estimate_exception(self, tmp_path, monkeypatch):
        """L346-347: estimate_resources exception."""
        from cyberpunk_designer.drawing.overlays import draw_help_overlay

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.show_help_overlay = True
        app.designer.estimate_resources = MagicMock(side_effect=RuntimeError("boom"))
        draw_help_overlay(app)

    def test_help_overlay_res_line_exception(self, tmp_path, monkeypatch):
        """L353-354: res_line formatting exception."""
        from cyberpunk_designer.drawing.overlays import draw_help_overlay

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.show_help_overlay = True
        # Return est with bad values
        app.designer.estimate_resources = MagicMock(return_value={
            "framebuffer_kb": "not_a_number",
            "flash_kb": None,
            "overlaps": "bad",
        })
        draw_help_overlay(app)

    def test_help_overlay_two_column(self, tmp_path, monkeypatch):
        """L381-427: two-column layout when panel is wide enough."""
        from cyberpunk_designer.drawing.overlays import draw_help_overlay

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.show_help_overlay = True
        # Make the layout wide enough for two columns (>= GRID*70)
        app.layout.width = 800
        app.layout.height = 600
        app.logical_surface = pygame.Surface((800, 600))
        draw_help_overlay(app)


# ---------------------------------------------------------------------------
# drawing/canvas.py — exception branches, overlays
# ---------------------------------------------------------------------------


class TestDrawingCanvasEdges:
    """Cover uncovered branches in drawing/canvas.py."""

    def test_draw_canvas_scene_dims_exception(self, tmp_path, monkeypatch):
        """L23-24: scene_w/scene_h exception."""
        from cyberpunk_designer.drawing.canvas import draw_canvas

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.width = MagicMock(side_effect=ValueError("bad"))
        draw_canvas(app)

    def test_draw_canvas_widget_ids(self, tmp_path, monkeypatch):
        """L121,138-139: widget ID labels + exception branch."""
        from cyberpunk_designer.drawing.canvas import draw_canvas

        app = _make_app(tmp_path, monkeypatch,
                        widgets=[_w(x=10, y=10), _w(x=50, y=50, visible=False)])
        app.show_widget_ids = True
        draw_canvas(app)

    def test_draw_canvas_z_labels(self, tmp_path, monkeypatch):
        """L138-139: z-index labels."""
        from cyberpunk_designer.drawing.canvas import draw_canvas

        app = _make_app(tmp_path, monkeypatch,
                        widgets=[_w(x=10, y=10, z_index=5)])
        app.show_z_labels = True
        draw_canvas(app)

    def test_draw_canvas_focus_order(self, tmp_path, monkeypatch):
        """L156-157: focus order overlay."""
        from cyberpunk_designer.drawing.canvas import draw_canvas

        app = _make_app(tmp_path, monkeypatch,
                        widgets=[_w(type="button", x=10, y=10, enabled=True)])
        app.show_focus_order = True
        draw_canvas(app)

    def test_draw_canvas_hover_tooltip_left(self, tmp_path, monkeypatch):
        """L180: tooltip flipped to left when too close to right edge."""
        from cyberpunk_designer.drawing.canvas import draw_canvas

        app = _make_app(tmp_path, monkeypatch,
                        widgets=[_w(x=220, y=10, width=30, height=20)])
        # Put pointer over the widget near right edge
        scene_rect = getattr(app, "scene_rect", None)
        if scene_rect is None:
            scene_rect = app.layout.canvas_rect
        app.pointer_pos = (scene_rect.x + 230, scene_rect.y + 15)
        app.pointer_down = False
        app.sim_input_mode = False
        draw_canvas(app)

    def test_draw_canvas_hover_exception(self, tmp_path, monkeypatch):
        """L185-186: hover tooltip rendering exception."""
        from cyberpunk_designer.drawing.canvas import draw_canvas

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        app.pointer_pos = (app.layout.canvas_rect.x + 15, app.layout.canvas_rect.y + 15)
        app.pointer_down = False
        app.sim_input_mode = False
        # Make _load_pixel_font return something that will fail on render
        bad_font = MagicMock()
        bad_font.render = MagicMock(side_effect=RuntimeError("render fail"))
        app._load_pixel_font = MagicMock(return_value=bad_font)
        draw_canvas(app)

    def test_draw_selection_info_dragging(self, tmp_path, monkeypatch):
        """L267,269: selection info label positioned to left/top when near edge."""
        from cyberpunk_designer.drawing.canvas import _draw_selection_info

        app = _make_app(tmp_path, monkeypatch,
                        widgets=[_w(x=220, y=110, width=30, height=20)])
        app.state.selected = [0]
        app.state.dragging = True
        bounds = SimpleNamespace(x=220, y=110, width=30, height=20)
        sel_rect = pygame.Rect(220, 110, 30, 20)
        scene_rect = pygame.Rect(0, 0, 256, 128)
        _draw_selection_info(app, sel_rect, bounds, scene_rect)

    def test_draw_selection_info_exception(self, tmp_path, monkeypatch):
        """L274-275: selection info rendering exception."""
        from cyberpunk_designer.drawing.canvas import _draw_selection_info

        app = _make_app(tmp_path, monkeypatch)
        app.state.resizing = True
        bounds = SimpleNamespace(x=10, y=10, width=30, height=20)
        sel_rect = pygame.Rect(10, 10, 30, 20)
        scene_rect = pygame.Rect(0, 0, 256, 128)
        bad_font = MagicMock()
        bad_font.render = MagicMock(side_effect=RuntimeError("fail"))
        app._load_pixel_font = MagicMock(return_value=bad_font)
        _draw_selection_info(app, sel_rect, bounds, scene_rect)

    def test_draw_canvas_overflow_marker(self, tmp_path, monkeypatch):
        """L553: overflow marker for device profile with truncating text."""
        from cyberpunk_designer.drawing.canvas import draw_canvas

        app = _make_app(tmp_path, monkeypatch,
                        widgets=[_w(x=10, y=10, width=20, height=10,
                                    text="Very long text that overflows")])
        app.hardware_profile = "esp32os_256x128_gray4"
        app.show_overflow_warnings = True
        draw_canvas(app)

    def test_draw_rulers(self, tmp_path, monkeypatch):
        """L231,241: ruler break conditions."""
        from cyberpunk_designer.drawing.canvas import _draw_rulers

        app = _make_app(tmp_path, monkeypatch)
        scene_rect = pygame.Rect(0, 0, 256, 128)
        _draw_rulers(app, scene_rect, 256, 128)

    def test_draw_rulers_beyond_rect(self, tmp_path, monkeypatch):
        """L231,241: ruler ticks beyond scene_rect → break."""
        from cyberpunk_designer.drawing.canvas import _draw_rulers

        app = _make_app(tmp_path, monkeypatch)
        # scene_rect is small but scene dims are large → ticks exceed rect → break
        scene_rect = pygame.Rect(0, 0, 50, 50)
        _draw_rulers(app, scene_rect, 500, 500)

    def test_draw_canvas_icon_overflow(self, tmp_path, monkeypatch):
        """L553: icon widget overflow marker uses icon_char."""
        from cyberpunk_designer.drawing.canvas import draw_canvas

        app = _make_app(tmp_path, monkeypatch,
                        widgets=[_w(type="icon", icon_char="XXXXX", x=10, y=10,
                                    width=12, height=10)])
        app.hardware_profile = "esp32os_256x128_gray4"
        app.show_overflow_warnings = True
        draw_canvas(app)

    def test_draw_canvas_scene_dims_bad_int(self, tmp_path, monkeypatch):
        """L23-24: scene dims int() exception."""
        from cyberpunk_designer.drawing.canvas import draw_canvas

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()

        class BadInt:
            def __int__(self):
                raise TypeError("nope")

        sc.width = BadInt()
        draw_canvas(app)

    def test_draw_canvas_widget_id_render_except(self, tmp_path, monkeypatch):
        """L138-139: widget ID label render exception."""
        from cyberpunk_designer.drawing.canvas import draw_canvas

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        app.show_widget_ids = True
        # Make _load_pixel_font return a font that fails render
        bad_font = MagicMock()
        bad_font.render = MagicMock(side_effect=RuntimeError("fail"))
        real_load = app._load_pixel_font

        def _patched_load(size):
            if size <= 10:  # small font for labels
                return bad_font
            return real_load(size)

        app._load_pixel_font = _patched_load
        draw_canvas(app)

    def test_draw_canvas_focus_order_render_except(self, tmp_path, monkeypatch):
        """L156-157: focus order label render exception."""
        from cyberpunk_designer.drawing.canvas import draw_canvas

        app = _make_app(tmp_path, monkeypatch,
                        widgets=[_w(type="button", x=10, y=10, enabled=True)])
        app.show_focus_order = True
        bad_font = MagicMock()
        bad_font.render = MagicMock(side_effect=RuntimeError("fail"))
        real_load = app._load_pixel_font

        def _patched_load(size):
            if size <= 10:
                return bad_font
            return real_load(size)

        app._load_pixel_font = _patched_load
        draw_canvas(app)

    def test_draw_selection_info_offscreen(self, tmp_path, monkeypatch):
        """L267,269,288: selection info offscreen → flip position; exception."""
        from cyberpunk_designer.drawing.canvas import _draw_selection_info

        app = _make_app(tmp_path, monkeypatch)
        app.state.dragging = True
        # Near bottom-right of scene rect → label goes left and up
        bounds = SimpleNamespace(x=240, y=120, width=16, height=8)
        sel_rect = pygame.Rect(240, 120, 16, 8)
        scene_rect = pygame.Rect(0, 0, 256, 128)
        _draw_selection_info(app, sel_rect, bounds, scene_rect)


# ---------------------------------------------------------------------------
# drawing/panels.py — draw_status exception branches
# ---------------------------------------------------------------------------


class TestDrawingPanelsStatusEdges:
    """Cover uncovered branches in draw_status."""

    def test_draw_status_scene_exception(self, tmp_path, monkeypatch):
        """L277-278: current_scene() exception."""
        from cyberpunk_designer.drawing.panels import draw_status

        app = _make_app(tmp_path, monkeypatch)
        # Patch both current_scene and selected_widget (which also calls current_scene)
        app.state.current_scene = MagicMock(side_effect=RuntimeError("boom"))
        app.state.selected_widget = MagicMock(return_value=None)
        draw_status(app)

    def test_draw_status_scene_names_exception(self, tmp_path, monkeypatch):
        """L295-296: scene_names exception."""
        from cyberpunk_designer.drawing.panels import draw_status

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        # scenes.keys() must work for current_scene, but list() on the result fails
        real_scenes = app.designer.scenes
        class TrickyScenes(dict):
            _keys_call = 0
            def keys(self):
                self._keys_call += 1
                if self._keys_call > 2:  # fail on later calls (status bar)
                    raise RuntimeError("bad")
                return super().keys()
        ts = TrickyScenes(real_scenes)
        app.designer.scenes = ts
        draw_status(app)

    def test_draw_status_undo_exception(self, tmp_path, monkeypatch):
        """L351-352: undo/redo count exception."""
        from cyberpunk_designer.drawing.panels import draw_status

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])

        class BadStack:
            def __len__(self):
                raise RuntimeError("bad")

        app.designer.undo_stack = BadStack()
        draw_status(app)

    def test_draw_inspector_layer_drag(self, tmp_path, monkeypatch):
        """L229-234: layer drag highlight in inspector."""
        from cyberpunk_designer.drawing.panels import draw_inspector

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app._layer_drag_idx = 5
        # Position pointer over inspector
        r = app.layout.inspector_rect
        app.pointer_pos = (r.centerx, r.centery)
        draw_inspector(app)

    def test_draw_inspector_resources_warning(self, tmp_path, monkeypatch):
        """L223: inspector row with resources warning → locked shade."""
        from cyberpunk_designer.drawing.panels import draw_inspector

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        draw_inspector(app)

    def test_draw_palette_item_hover(self, tmp_path, monkeypatch):
        """L113: palette widget item hover shade."""
        from cyberpunk_designer.drawing.panels import draw_palette

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        # pointer on the widget list area (below palette sections)
        r = app.layout.palette_rect
        bottom_y = r.bottom - int(app.pixel_row_height)
        app.pointer_pos = (r.centerx, bottom_y)
        draw_palette(app)


# ---------------------------------------------------------------------------
# drawing/overlays.py — additional help overlay branches
# ---------------------------------------------------------------------------


class TestDrawingOverlaysExtraEdges:
    """Additional help overlay branches."""

    def test_help_overlay_wide_two_col(self, tmp_path, monkeypatch):
        """L381-427: two-column layout — need content_rect.width >= GRID*70."""
        from cyberpunk_designer.drawing.overlays import draw_help_overlay

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.show_help_overlay = True
        # Need layout wide enough so panel_w is large and content_rect >= 560
        app.layout.width = 1200
        app.layout.height = 800
        app.logical_surface = pygame.Surface((1200, 800))
        draw_help_overlay(app)

    def test_help_overlay_profile_get_exception(self, tmp_path, monkeypatch):
        """L326-327: HARDWARE_PROFILES[profile] .get() raises."""
        from cyberpunk_designer.drawing.overlays import draw_help_overlay
        from ui_designer import HARDWARE_PROFILES

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.show_help_overlay = True
        # Inject a bad profile entry that raises on .get()
        bad_profile = MagicMock()
        bad_profile.get = MagicMock(side_effect=RuntimeError("bad"))
        monkeypatch.setitem(HARDWARE_PROFILES, "test_bad", bad_profile)
        app.hardware_profile = "test_bad"
        draw_help_overlay(app)

    def test_help_overlay_scene_dims_exception(self, tmp_path, monkeypatch):
        """L336-337: int(getattr(sc, 'width',...)) fails → '?'."""
        from cyberpunk_designer.drawing.overlays import draw_help_overlay

        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        sc = app.state.current_scene()

        class BadDim:
            def __int__(self):
                raise ValueError("bad")

        sc.width = BadDim()
        draw_help_overlay(app)

    def test_help_overlay_sel_count_exception(self, tmp_path, monkeypatch):
        """L363-364: sel_count len() fails."""
        from cyberpunk_designer.drawing.overlays import draw_help_overlay

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.show_help_overlay = True

        class BadSelected:
            def __len__(self):
                raise RuntimeError("bad")

        app.state.selected = BadSelected()
        draw_help_overlay(app)


# ---------------------------------------------------------------------------
# drawing/text.py — additional wrap_text_px truncation branches
# ---------------------------------------------------------------------------


class TestDrawingTextExtraEdges:
    """Additional branches in text.py wrap logic."""

    def test_wrap_text_px_truncation_multi_para(self, tmp_path, monkeypatch):
        """L68-69,96,99,110: truncation inside wrap loop."""
        from cyberpunk_designer.drawing.text import wrap_text_px

        app = _make_app(tmp_path, monkeypatch)
        # Create text with many paragraphs → hit max_lines truncation
        text = "\n".join(["Word " * 20] * 10)
        result = wrap_text_px(app, text, max_width_px=100, max_lines=2, ellipsis="...")
        assert len(result) <= 2

    def test_wrap_text_px_long_word_break_truncation(self, tmp_path, monkeypatch):
        """L96: break after char-by-char split hits max_lines."""
        from cyberpunk_designer.drawing.text import wrap_text_px

        app = _make_app(tmp_path, monkeypatch)
        # One extremely long word that must break char-by-char, hitting max_lines
        text = "A" * 500
        result = wrap_text_px(app, text, max_width_px=30, max_lines=2, ellipsis="...")
        assert len(result) <= 2

    def test_draw_text_clipped_wrap_empty(self, tmp_path, monkeypatch):
        """L165: wrap mode returns [] → empty lines → return."""
        from cyberpunk_designer.drawing.text import draw_text_clipped

        app = _make_app(tmp_path, monkeypatch)
        surf = pygame.Surface((200, 100))
        # Padding so large that clip_rect width is tiny → wrap returns []
        rect = pygame.Rect(10, 10, 8, 80)
        draw_text_clipped(app, surf, "hello world test", rect, (255, 255, 255), 3,
                          max_lines=5)

    # L181-182: clip_rect.clip(old_clip) exception — cannot monkeypatch
    # immutable pygame.Rect.clip. Branch is defensive guard for corrupted clip state.

    def test_draw_text_in_rect_auto_device_wrap(self, tmp_path, monkeypatch):
        """L232-233,240,249-250: auto overflow with device mode + wrap."""
        from cyberpunk_designer.drawing.text import draw_text_in_rect

        app = _make_app(tmp_path, monkeypatch)
        monkeypatch.setattr(app, "hardware_profile", "esp32os_256x128_gray4")
        surf = pygame.Surface((256, 128))
        # Rect within canvas_rect (default canvas covers most of the surface)
        rect = pygame.Rect(10, 10, 80, 40)
        w = _w()
        w.text_overflow = "auto"
        w.max_lines = 3
        # Long text with newlines that forces device auto mode to choose wrap
        draw_text_in_rect(app, surf, "Very long line text\nMore text here", rect, (255, 255, 255), 2, w)

    def test_draw_text_in_rect_wrap_max_lines_bad(self, tmp_path, monkeypatch):
        """L249-250: max_lines attribute exception."""
        from cyberpunk_designer.drawing.text import draw_text_in_rect

        app = _make_app(tmp_path, monkeypatch)
        surf = pygame.Surface((200, 100))
        rect = pygame.Rect(10, 10, 100, 80)
        w = _w()
        w.text_overflow = "wrap"
        w.max_lines = "not_a_number"
        draw_text_in_rect(app, surf, "word " * 50, rect, (255, 255, 255), 2, w)
