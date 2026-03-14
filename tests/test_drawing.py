"""Tests for cyberpunk_designer/drawing.py — text measurement helpers,
rendering primitives, panel/button/scrollbar widgets, text layout,
and full-app drawing smoke tests."""

from __future__ import annotations

import time
from types import SimpleNamespace

import pygame

from cyberpunk_designer.constants import (
    PALETTE,
    SHADE_BTN_FILL,
    SHADE_BTN_FILL_PRESS,
    SHADE_BTN_HOVER,
    SHADE_GRID_CANVAS,
    SHADE_GRID_H,
    SHADE_GRID_V,
    SHADE_HOVER,
    SHADE_NORMAL,
    SHADE_PALETTE_HOVER,
    SHADE_PRESSED,
    SHADE_SCANLINE,
    SHADE_SEL_FILL,
    SHADE_SHADOW,
    SHADE_THUMB,
    SHADE_THUMB_BORDER,
    SHADE_TITLE_SHADOW,
    SHADE_TOOLBAR_DARK,
    SHADE_TOOLBAR_LIGHT,
    SHADE_TOOLBAR_SEP,
    SHADE_TRACK,
    SHADE_WIDGET_BG_OFF,
    SHADE_WIDGET_HOVER,
    SHADE_WIDGET_PRESS,
)
from cyberpunk_designer.drawing import (
    draw_bevel_frame,
    draw_border_style,
    draw_context_menu,
    draw_dashed_rect,
    draw_frame,
    draw_help_overlay,
    draw_overflow_marker,
    draw_pixel_frame,
    draw_pixel_panel_bg,
    draw_scrollbar,
    draw_status,
    draw_text_clipped,
    draw_text_in_rect,
    draw_tooltip,
    ellipsize_text_px,
    panel,
    render_pixel_text,
    text_width_px,
    wrap_text_px,
)
from cyberpunk_editor import CyberpunkEditorApp
from ui_designer import WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeFont:
    """Monospace font stub: each char = char_w pixels wide."""

    def __init__(self, char_w: int = 7, line_h: int = 12):
        self._char_w = char_w
        self._line_h = line_h

    def get_height(self):
        return self._line_h

    def size(self, text):
        return (len(str(text or "")) * self._char_w, self._line_h)

    def render(self, text, antialias, color):
        w, h = self.size(text)
        surf = pygame.Surface((max(1, w), max(1, h)), pygame.SRCALPHA)
        surf.fill((*color, 255) if len(color) == 3 else color)
        return surf


def _app(char_w: int = 7) -> SimpleNamespace:
    return SimpleNamespace(pixel_font=_FakeFont(char_w=char_w))


def _shade_factory():
    """Return a _shade callable that simply brightens/darkens."""

    def _shade(color, delta):
        return tuple(max(0, min(255, c + delta)) for c in color)

    return _shade


# ---------------------------------------------------------------------------
# text_width_px
# ---------------------------------------------------------------------------


class TestTextWidthPx:
    def test_basic(self):
        app = _app(7)
        assert text_width_px(app, "Hello") == 35  # 5×7

    def test_empty(self):
        app = _app(7)
        assert text_width_px(app, "") == 0

    def test_none(self):
        app = _app(7)
        assert text_width_px(app, None) == 0

    def test_broken_font(self):
        app = SimpleNamespace(
            pixel_font=SimpleNamespace(size=lambda t: (_ for _ in ()).throw(TypeError))
        )
        assert text_width_px(app, "abc") == 0


# ---------------------------------------------------------------------------
# ellipsize_text_px
# ---------------------------------------------------------------------------


class TestEllipsizeTextPx:
    def test_fits(self):
        app = _app(7)
        assert ellipsize_text_px(app, "Hi", 200) == "Hi"

    def test_truncates(self):
        app = _app(7)
        result = ellipsize_text_px(app, "A very long string", 50)
        # Must end with "..."
        assert result.endswith("...")
        # Width must be ≤ 50
        assert text_width_px(app, result) <= 50

    def test_zero_width(self):
        app = _app(7)
        assert ellipsize_text_px(app, "abc", 0) == ""

    def test_empty(self):
        app = _app(7)
        assert ellipsize_text_px(app, "", 100) == ""

    def test_none(self):
        app = _app(7)
        assert ellipsize_text_px(app, None, 100) == ""

    def test_very_narrow(self):
        # Max width less than ellipsis → falls back to char-by-char
        app = _app(7)
        result = ellipsize_text_px(app, "Hello World", 10)
        assert text_width_px(app, result) <= 10

    def test_exact_fit(self):
        # String exactly fits → no truncation
        app = _app(7)
        assert ellipsize_text_px(app, "AB", 14) == "AB"


# ---------------------------------------------------------------------------
# wrap_text_px
# ---------------------------------------------------------------------------


class TestWrapTextPx:
    def test_single_line(self):
        app = _app(7)
        lines = wrap_text_px(app, "Hello", 200, max_lines=5)
        assert lines == ["Hello"]

    def test_wraps(self):
        app = _app(7)
        lines = wrap_text_px(app, "word1 word2 word3", 42, max_lines=5)
        # 42 / 7 = 6 chars max per line; "word1" (5) fits, "word1 word2" (11) doesn't
        assert len(lines) >= 2
        for ln in lines:
            assert text_width_px(app, ln) <= 42

    def test_max_lines_truncation(self):
        app = _app(7)
        lines = wrap_text_px(app, "a b c d e f g h", 14, max_lines=2)
        assert len(lines) <= 2

    def test_empty(self):
        app = _app(7)
        assert wrap_text_px(app, "", 100, max_lines=5) == []

    def test_zero_width(self):
        app = _app(7)
        assert wrap_text_px(app, "Hello", 0, max_lines=5) == []

    def test_long_word_chunks(self):
        app = _app(7)
        lines = wrap_text_px(app, "ABCDEFGHIJKLMNO", 28, max_lines=10)
        # 28 / 7 = 4 chars → long word broken into chunks
        assert len(lines) >= 2

    def test_newlines_preserved(self):
        app = _app(7)
        lines = wrap_text_px(app, "line1\nline2", 200, max_lines=5)
        assert len(lines) == 2

    def test_single_max_line(self):
        app = _app(7)
        lines = wrap_text_px(app, "word1 word2 word3", 42, max_lines=1)
        assert len(lines) == 1


# ---------------------------------------------------------------------------
# draw_dashed_rect
# ---------------------------------------------------------------------------


class TestDrawDashedRect:
    def test_basic(self):
        surface = pygame.Surface((100, 100))
        draw_dashed_rect(surface, (255, 255, 255), pygame.Rect(10, 10, 50, 50))
        # No crash; just verify it runs

    def test_small_rect(self):
        surface = pygame.Surface((20, 20))
        draw_dashed_rect(surface, (128, 128, 128), pygame.Rect(0, 0, 5, 5), dash=1, gap=1)

    def test_zero_rect(self):
        surface = pygame.Surface((10, 10))
        draw_dashed_rect(surface, (255, 0, 0), pygame.Rect(0, 0, 0, 0))


# ---------------------------------------------------------------------------
# draw_border_style
# ---------------------------------------------------------------------------


class TestDrawBorderStyle:
    def _make_app(self):
        return SimpleNamespace(
            pixel_font=_FakeFont(),
            _shade=_shade_factory(),
        )

    def test_single(self):
        app = self._make_app()
        surface = pygame.Surface((100, 100))
        draw_border_style(app, surface, pygame.Rect(10, 10, 50, 50), "single", (200, 200, 200))

    def test_bold(self):
        app = self._make_app()
        surface = pygame.Surface((100, 100))
        draw_border_style(app, surface, pygame.Rect(10, 10, 50, 50), "bold", (200, 200, 200))

    def test_double(self):
        app = self._make_app()
        surface = pygame.Surface((100, 100))
        draw_border_style(app, surface, pygame.Rect(10, 10, 50, 50), "double", (200, 200, 200))

    def test_rounded(self):
        app = self._make_app()
        surface = pygame.Surface((100, 100))
        draw_border_style(app, surface, pygame.Rect(10, 10, 50, 50), "rounded", (200, 200, 200))

    def test_dashed(self):
        app = self._make_app()
        surface = pygame.Surface((100, 100))
        draw_border_style(app, surface, pygame.Rect(10, 10, 50, 50), "dashed", (200, 200, 200))

    def test_unknown_falls_back(self):
        app = self._make_app()
        surface = pygame.Surface((100, 100))
        draw_border_style(
            app, surface, pygame.Rect(10, 10, 50, 50), "unknown_style", (200, 200, 200)
        )


# ---------------------------------------------------------------------------
# draw_bevel_frame
# ---------------------------------------------------------------------------


class TestDrawBevelFrame:
    def _make_app(self):
        return SimpleNamespace(
            pixel_font=_FakeFont(),
            _shade=_shade_factory(),
        )

    def test_normal(self):
        app = self._make_app()
        surface = pygame.Surface((100, 100))
        draw_bevel_frame(app, surface, pygame.Rect(10, 10, 40, 20), (128, 128, 128))

    def test_pressed(self):
        app = self._make_app()
        surface = pygame.Surface((100, 100))
        draw_bevel_frame(app, surface, pygame.Rect(10, 10, 40, 20), (128, 128, 128), pressed=True)


# ---------------------------------------------------------------------------
# Shared helpers for full-app tests
# ---------------------------------------------------------------------------


def _make_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    return CyberpunkEditorApp(json_path, (256, 128))


def _rich_app(char_w: int = 7) -> SimpleNamespace:
    """A SimpleNamespace stub with enough attrs for draw_* primitives."""
    surface = pygame.Surface((256, 128))
    font = _FakeFont(char_w=char_w)
    return SimpleNamespace(
        pixel_font=font,
        font=font,
        logical_surface=surface,
        window=surface,
        _shade=_shade_factory(),
        pixel_padding=4,
        pixel_row_height=12,
        toolbar_h=16,
        pointer_pos=(0, 0),
        pointer_down=False,
        _is_pointer_over=lambda r: False,
        _snap_rect=lambda r: r,
        show_grid=False,
        show_overflow_warnings=False,
        hardware_profile=None,
    )


# ---------------------------------------------------------------------------
# draw_frame
# ---------------------------------------------------------------------------


class TestDrawFrame:
    def test_fills_surface(self):
        app = _rich_app()
        draw_frame(app)
        # Surface should be filled with PALETTE["bg"]
        assert app.logical_surface.get_at((0, 0))[:3] == PALETTE["bg"]

    def test_uses_window_if_present(self):
        app = _rich_app()
        w = pygame.Surface((100, 50))
        app.window = w
        draw_frame(app)
        assert w.get_at((0, 0))[:3] == PALETTE["bg"]

    def test_noop_no_surface(self):
        app = _rich_app()
        app.window = None
        app.logical_surface = None
        draw_frame(app)  # no crash


# ---------------------------------------------------------------------------
# render_pixel_text
# ---------------------------------------------------------------------------


class TestRenderPixelText:
    def test_basic_render(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf = render_pixel_text(app, "Hello", (255, 255, 255))
        assert surf.get_width() > 0
        assert surf.get_height() > 0

    def test_shadow(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        no_shadow = render_pixel_text(app, "Hi", (255, 255, 255))
        with_shadow = render_pixel_text(app, "Hi", (255, 255, 255), shadow=(0, 0, 0))
        # Shadow version is 1px wider and taller
        assert with_shadow.get_width() == no_shadow.get_width() + 1
        assert with_shadow.get_height() == no_shadow.get_height() + 1

    def test_empty_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        surf = render_pixel_text(app, "", (255, 255, 255))
        assert surf.get_height() > 0

    def test_scale_ignored(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        s1 = render_pixel_text(app, "AB", (255, 255, 255), scale=1)
        s2 = render_pixel_text(app, "AB", (255, 255, 255), scale=4)
        assert s1.get_width() == s2.get_width()


# ---------------------------------------------------------------------------
# draw_pixel_frame
# ---------------------------------------------------------------------------


class TestDrawPixelFrame:
    def test_normal(self):
        app = _rich_app()
        draw_pixel_frame(app, pygame.Rect(10, 10, 50, 30))

    def test_pressed(self):
        app = _rich_app()
        draw_pixel_frame(app, pygame.Rect(10, 10, 50, 30), pressed=True)

    def test_hover(self):
        app = _rich_app()
        draw_pixel_frame(app, pygame.Rect(10, 10, 50, 30), hover=True)

    def test_small_rect(self):
        app = _rich_app()
        draw_pixel_frame(app, pygame.Rect(0, 0, 2, 2))


# ---------------------------------------------------------------------------
# draw_pixel_panel_bg
# ---------------------------------------------------------------------------


class TestDrawPixelPanelBg:
    def test_fills_rect(self):
        app = _rich_app()
        draw_pixel_panel_bg(app, pygame.Rect(10, 10, 80, 40))
        # Interior should be PALETTE["panel"] color
        assert app.logical_surface.get_at((50, 30))[:3] == PALETTE["panel"]

    def test_small_rect(self):
        app = _rich_app()
        draw_pixel_panel_bg(app, pygame.Rect(0, 0, 1, 1))  # no crash


# ---------------------------------------------------------------------------
# draw_scrollbar
# ---------------------------------------------------------------------------


class TestDrawScrollbar:
    def test_normal(self):
        app = _rich_app()
        draw_scrollbar(app, pygame.Rect(10, 10, 20, 100), scroll=10, max_scroll=50, content_h=200)

    def test_zero_scroll(self):
        app = _rich_app()
        draw_scrollbar(app, pygame.Rect(10, 10, 20, 100), scroll=0, max_scroll=50, content_h=200)

    def test_max_scroll(self):
        app = _rich_app()
        draw_scrollbar(app, pygame.Rect(10, 10, 20, 100), scroll=50, max_scroll=50, content_h=200)

    def test_zero_max_scroll(self):
        app = _rich_app()
        draw_scrollbar(app, pygame.Rect(10, 10, 20, 100), scroll=0, max_scroll=0, content_h=100)
        # max_scroll <= 0 → early return, no crash

    def test_zero_rect(self):
        app = _rich_app()
        draw_scrollbar(app, pygame.Rect(0, 0, 0, 0), scroll=0, max_scroll=10, content_h=100)

    def test_scroll_overflow_clamped(self):
        app = _rich_app()
        draw_scrollbar(app, pygame.Rect(0, 0, 10, 80), scroll=9999, max_scroll=50, content_h=200)


# ---------------------------------------------------------------------------
# panel
# ---------------------------------------------------------------------------


class TestPanel:
    def test_with_title(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        panel(app, pygame.Rect(0, 0, 100, 60), title="Test")

    def test_no_title(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        panel(app, pygame.Rect(0, 0, 100, 60))

    def test_empty_title(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        panel(app, pygame.Rect(0, 0, 100, 60), title="")


# ---------------------------------------------------------------------------
# draw_overflow_marker
# ---------------------------------------------------------------------------


class TestDrawOverflowMarker:
    def test_normal(self):
        app = _rich_app()
        surface = pygame.Surface((100, 100))
        draw_overflow_marker(app, surface, pygame.Rect(10, 10, 40, 20))
        # Check red triangle drawn at top-right
        assert surface.get_at((47, 11))[:3] == (255, 80, 80)

    def test_none_surface(self):
        app = _rich_app()
        draw_overflow_marker(app, None, pygame.Rect(10, 10, 40, 20))  # no crash

    def test_zero_rect(self):
        app = _rich_app()
        surface = pygame.Surface((100, 100))
        draw_overflow_marker(app, surface, pygame.Rect(0, 0, 0, 0))  # early return

    def test_tiny_rect(self):
        app = _rich_app()
        surface = pygame.Surface((20, 20))
        draw_overflow_marker(app, surface, pygame.Rect(0, 0, 8, 8))


# ---------------------------------------------------------------------------
# draw_text_clipped
# ---------------------------------------------------------------------------


class TestDrawTextClipped:
    def test_left_align(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_text_clipped(
            app,
            app.logical_surface,
            "Test",
            pygame.Rect(10, 10, 100, 20),
            (255, 255, 255),
            padding=2,
            align="left",
            valign="middle",
        )

    def test_center_align(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_text_clipped(
            app,
            app.logical_surface,
            "Test",
            pygame.Rect(10, 10, 100, 20),
            (255, 255, 255),
            padding=2,
            align="center",
            valign="middle",
        )

    def test_right_align(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_text_clipped(
            app,
            app.logical_surface,
            "Test",
            pygame.Rect(10, 10, 100, 20),
            (255, 255, 255),
            padding=2,
            align="right",
            valign="middle",
        )

    def test_valign_top(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_text_clipped(
            app,
            app.logical_surface,
            "Test",
            pygame.Rect(10, 10, 100, 40),
            (255, 255, 255),
            padding=2,
            align="left",
            valign="top",
        )

    def test_valign_bottom(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_text_clipped(
            app,
            app.logical_surface,
            "Test",
            pygame.Rect(10, 10, 100, 40),
            (255, 255, 255),
            padding=2,
            align="left",
            valign="bottom",
        )

    def test_multiline(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_text_clipped(
            app,
            app.logical_surface,
            "Line1\nLine2",
            pygame.Rect(10, 10, 100, 40),
            (255, 255, 255),
            padding=2,
            max_lines=3,
        )

    def test_empty_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_text_clipped(
            app, app.logical_surface, "", pygame.Rect(10, 10, 100, 20), (255, 255, 255), padding=2
        )

    def test_none_text(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_text_clipped(
            app, app.logical_surface, None, pygame.Rect(10, 10, 100, 20), (255, 255, 255), padding=2
        )

    def test_zero_width_rect(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_text_clipped(
            app, app.logical_surface, "Text", pygame.Rect(10, 10, 0, 20), (255, 255, 255), padding=0
        )

    def test_large_padding(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_text_clipped(
            app,
            app.logical_surface,
            "Text",
            pygame.Rect(10, 10, 20, 20),
            (255, 255, 255),
            padding=15,
        )

    def test_device_font_explicit(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_text_clipped(
            app,
            app.logical_surface,
            "ABC",
            pygame.Rect(10, 10, 100, 20),
            (255, 255, 255),
            padding=2,
            use_device_font=True,
        )

    def test_device_font_multiline(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_text_clipped(
            app,
            app.logical_surface,
            "Line1\nLine2\nLine3",
            pygame.Rect(10, 10, 100, 50),
            (255, 255, 255),
            padding=2,
            use_device_font=True,
            max_lines=3,
        )


# ---------------------------------------------------------------------------
# draw_text_in_rect
# ---------------------------------------------------------------------------


class TestDrawTextInRect:
    def test_ellipsis_overflow(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(
            type="label", x=0, y=0, width=60, height=16, text="LongText", text_overflow="ellipsis"
        )
        draw_text_in_rect(
            app,
            app.logical_surface,
            "LongTextHere",
            pygame.Rect(10, 10, 60, 16),
            (255, 255, 255),
            2,
            w,
        )

    def test_wrap_overflow(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(
            type="label", x=0, y=0, width=60, height=40, text="Wrap", text_overflow="wrap"
        )
        draw_text_in_rect(
            app,
            app.logical_surface,
            "Word1 Word2 Word3",
            pygame.Rect(10, 10, 60, 40),
            (255, 255, 255),
            2,
            w,
        )

    def test_clip_overflow(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(
            type="label", x=0, y=0, width=60, height=16, text="Clip", text_overflow="clip"
        )
        draw_text_in_rect(
            app, app.logical_surface, "SomeText", pygame.Rect(10, 10, 60, 16), (255, 255, 255), 2, w
        )

    def test_auto_overflow_short(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(
            type="label", x=0, y=0, width=200, height=16, text="Short", text_overflow="auto"
        )
        draw_text_in_rect(
            app, app.logical_surface, "Short", pygame.Rect(10, 10, 200, 16), (255, 255, 255), 2, w
        )

    def test_auto_overflow_long(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(
            type="label", x=0, y=0, width=60, height=40, text="Very long text", text_overflow="auto"
        )
        draw_text_in_rect(
            app,
            app.logical_surface,
            "Very long text that wraps",
            pygame.Rect(10, 10, 60, 40),
            (255, 255, 255),
            2,
            w,
        )

    def test_align_center(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(
            type="label",
            x=0,
            y=0,
            width=100,
            height=20,
            text="Center",
            align="center",
            valign="middle",
        )
        draw_text_in_rect(
            app, app.logical_surface, "Center", pygame.Rect(10, 10, 100, 20), (255, 255, 255), 2, w
        )

    def test_max_lines(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(
            type="label",
            x=0,
            y=0,
            width=60,
            height=60,
            text="A B C",
            text_overflow="wrap",
            max_lines=2,
        )
        draw_text_in_rect(
            app,
            app.logical_surface,
            "A B C D E F G",
            pygame.Rect(10, 10, 60, 60),
            (255, 255, 255),
            2,
            w,
        )

    def test_unknown_overflow_falls_back(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        w = WidgetConfig(
            type="label", x=0, y=0, width=60, height=16, text="T", text_overflow="bogus"
        )
        draw_text_in_rect(
            app, app.logical_surface, "T", pygame.Rect(10, 10, 60, 16), (255, 255, 255), 2, w
        )


# ---------------------------------------------------------------------------
# Full-app smoke tests: draw_toolbar via CyberpunkEditorApp
# ---------------------------------------------------------------------------


class TestDrawToolbar:
    def test_no_crash(self, tmp_path, monkeypatch):
        from cyberpunk_designer.drawing import draw_toolbar

        app = _make_app(tmp_path, monkeypatch)
        draw_toolbar(app)
        assert hasattr(app, "toolbar_hitboxes")

    def test_hitboxes_populated(self, tmp_path, monkeypatch):
        from cyberpunk_designer.drawing import draw_toolbar

        app = _make_app(tmp_path, monkeypatch)
        draw_toolbar(app)
        assert len(app.toolbar_hitboxes) > 0


# ---------------------------------------------------------------------------
# draw_scene_tabs
# ---------------------------------------------------------------------------


class TestDrawSceneTabs:
    def test_no_crash(self, tmp_path, monkeypatch):
        from cyberpunk_designer.drawing import draw_scene_tabs

        app = _make_app(tmp_path, monkeypatch)
        draw_scene_tabs(app)
        assert hasattr(app, "tab_hitboxes")

    def test_multi_scene(self, tmp_path, monkeypatch):
        from cyberpunk_designer.drawing import draw_scene_tabs
        from ui_designer import SceneConfig

        app = _make_app(tmp_path, monkeypatch)
        app.designer.scenes["second"] = SceneConfig(
            name="second",
            width=256,
            height=128,
            widgets=[],
        )
        draw_scene_tabs(app)
        assert len(app.tab_hitboxes) >= 2


# ---------------------------------------------------------------------------
# draw_palette
# ---------------------------------------------------------------------------


class TestDrawPalette:
    def test_no_crash(self, tmp_path, monkeypatch):
        from cyberpunk_designer.drawing import draw_palette

        app = _make_app(tmp_path, monkeypatch)
        draw_palette(app)
        assert hasattr(app, "palette_hitboxes")


# ---------------------------------------------------------------------------
# draw_inspector
# ---------------------------------------------------------------------------


class TestDrawInspector:
    def test_no_selection(self, tmp_path, monkeypatch):
        from cyberpunk_designer.drawing import draw_inspector

        app = _make_app(tmp_path, monkeypatch)
        draw_inspector(app)

    def test_with_selection(self, tmp_path, monkeypatch):
        from cyberpunk_designer.drawing import draw_inspector

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=0, y=0, width=80, height=16, text="Hi"))
        app.state.selected = [0]
        app.state.selected_idx = 0
        draw_inspector(app)
        assert hasattr(app, "inspector_hitboxes")


# ---------------------------------------------------------------------------
# draw_status
# ---------------------------------------------------------------------------


class TestDrawStatus:
    def test_no_crash(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        draw_status(app)

    def test_with_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="button", x=10, y=10, width=40, height=16, text="B"))
        app.state.selected = [0]
        app.state.selected_idx = 0
        draw_status(app)

    def test_multi_selection(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=0, y=0, width=40, height=16))
        sc.widgets.append(WidgetConfig(type="label", x=50, y=0, width=40, height=16))
        app.state.selected = [0, 1]
        draw_status(app)

    def test_with_status_message(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.dialog_message = "Saved!"
        app._status_until_ts = time.time() + 10
        draw_status(app)


# ---------------------------------------------------------------------------
# draw_context_menu
# ---------------------------------------------------------------------------


class TestDrawContextMenu:
    def test_no_menu(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._context_menu = None
        draw_context_menu(app)  # no crash

    def test_invisible_menu(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app._context_menu = {"visible": False, "items": [], "pos": (0, 0)}
        draw_context_menu(app)  # no crash

    def test_visible_menu(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        items = [
            ("Cut", "Ctrl+X", lambda: None),
            ("Copy", "Ctrl+C", lambda: None),
            (None, None, None),  # separator
            ("Paste", "Ctrl+V", lambda: None),
        ]
        app._context_menu = {"visible": True, "items": items, "pos": (50, 50)}
        draw_context_menu(app)
        assert "hitboxes" in app._context_menu
        assert len(app._context_menu["hitboxes"]) == 3  # 3 items, 1 sep

    def test_menu_clamped_to_screen(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        items = [("Action", "", lambda: None)]
        app._context_menu = {"visible": True, "items": items, "pos": (9999, 9999)}
        draw_context_menu(app)
        rect = app._context_menu["rect"]
        sw = app.logical_surface.get_width()
        sh = app.logical_surface.get_height()
        assert rect.right <= sw
        assert rect.bottom <= sh


# ---------------------------------------------------------------------------
# draw_tooltip
# ---------------------------------------------------------------------------


class TestDrawTooltip:
    def test_no_hover(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.pointer_pos = (0, 0)
        app.pointer_down = False
        draw_tooltip(app)  # no crash

    def test_pointer_down_clears(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.pointer_down = True
        app._tooltip_key = "test"
        draw_tooltip(app)
        assert app._tooltip_key is None

    def test_toolbar_hover(self, tmp_path, monkeypatch):
        from cyberpunk_designer.drawing import draw_toolbar

        app = _make_app(tmp_path, monkeypatch)
        draw_toolbar(app)
        # Hover over first toolbar button
        if app.toolbar_hitboxes:
            rect, _key = app.toolbar_hitboxes[0]
            app.pointer_pos = (rect.centerx, rect.centery)
            app.pointer_down = False
            draw_tooltip(app)
            # First hover sets _tooltip_key but doesn't render (delay)
            assert app._tooltip_key is not None


# ---------------------------------------------------------------------------
# draw_help_overlay
# ---------------------------------------------------------------------------


class TestDrawHelpOverlay:
    def test_hidden(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = False
        draw_help_overlay(app)  # no crash

    def test_visible(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.show_help_overlay = True
        draw_help_overlay(app)  # renders overlay without crash


# ---------------------------------------------------------------------------
# draw_canvas (smoke)
# ---------------------------------------------------------------------------


class TestDrawCanvas:
    def test_no_crash(self, tmp_path, monkeypatch):
        from cyberpunk_designer.drawing import draw_canvas

        app = _make_app(tmp_path, monkeypatch)
        draw_canvas(app)

    def test_with_widgets(self, tmp_path, monkeypatch):
        from cyberpunk_designer.drawing import draw_canvas

        app = _make_app(tmp_path, monkeypatch)
        sc = app.state.current_scene()
        sc.widgets.append(WidgetConfig(type="label", x=10, y=10, width=80, height=16, text="Hi"))
        sc.widgets.append(WidgetConfig(type="button", x=10, y=30, width=60, height=20, text="Btn"))
        sc.widgets.append(
            WidgetConfig(type="checkbox", x=10, y=60, width=80, height=16, checked=True)
        )
        draw_canvas(app)

    def test_with_grid(self, tmp_path, monkeypatch):
        from cyberpunk_designer.drawing import draw_canvas

        app = _make_app(tmp_path, monkeypatch)
        app.show_grid = True
        draw_canvas(app)


# ---------------------------------------------------------------------------
# Integration: draw_widget_preview with various types
# ---------------------------------------------------------------------------


class TestDrawWidgetPreviewTypes:
    def _draw(self, app, w_type, **kw):
        from cyberpunk_designer.drawing import draw_widget_preview

        defaults = dict(type=w_type, x=0, y=0, width=80, height=24, text="T")
        defaults.update(kw)
        w = WidgetConfig(**defaults)
        draw_widget_preview(
            app,
            app.logical_surface,
            w,
            pygame.Rect(0, 0, 80, 24),
            PALETTE["bg"],
            2,
            False,
        )

    def _app(self, tmp_path, monkeypatch):
        return _make_app(tmp_path, monkeypatch)

    def test_label(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "label")

    def test_button(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "button")

    def test_button_pressed(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "button", state="pressed")

    def test_checkbox(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "checkbox", checked=True)

    def test_checkbox_unchecked(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "checkbox", checked=False)

    def test_radiobutton(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "radiobutton", checked=True)

    def test_progressbar(self, tmp_path, monkeypatch):
        self._draw(
            self._app(tmp_path, monkeypatch), "progressbar", value=50, min_value=0, max_value=100
        )

    def test_slider(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "slider", value=30, width=120, height=24)

    def test_gauge(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "gauge", value=75, width=80, height=80)

    def test_gauge_small(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "gauge", value=50, width=20, height=16)

    def test_textbox(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "textbox")

    def test_panel(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "panel", width=120, height=60)

    def test_icon(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "icon", icon_char="@")

    def test_chart_line(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "chart", width=120, height=60)

    def test_chart_bar(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "chart", style="bar", width=120, height=60)

    def test_box(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "box")

    def test_inverse_style(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "label", style="inverse")

    def test_highlight_style(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "label", style="highlight")

    def test_locked_widget(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "label", locked=True, border=True)

    def test_disabled_widget(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), "label", enabled=False)

    def test_border_styles(self, tmp_path, monkeypatch):
        for bs in ("single", "bold", "double", "rounded", "dashed"):
            self._draw(self._app(tmp_path, monkeypatch), "label", border=True, border_style=bs)

    def test_custom_colors(self, tmp_path, monkeypatch):
        self._draw(
            self._app(tmp_path, monkeypatch), "label", color_fg="#ffffff", color_bg="#333333"
        )


# ---------------------------------------------------------------------------
# LIST widget rendering
# ---------------------------------------------------------------------------


class TestDrawWidgetPreviewList:
    def _app(self, tmp_path, monkeypatch):
        return _make_app(tmp_path, monkeypatch)

    def _draw(self, app, **kw):
        from cyberpunk_designer.drawing import draw_widget_preview

        defaults = dict(type="list", x=0, y=0, width=80, height=48, text="A\nB\nC")
        defaults.update(kw)
        w = WidgetConfig(**defaults)
        draw_widget_preview(
            app,
            app.logical_surface,
            w,
            pygame.Rect(0, 0, defaults["width"], defaults["height"]),
            PALETTE["bg"],
            2,
            False,
        )

    def test_list_multi_items(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), text="Foo\nBar\nBaz\nQux")

    def test_list_active_index(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), text="A\nB\nC", value=1)

    def test_list_scroll(self, tmp_path, monkeypatch):
        self._draw(
            self._app(tmp_path, monkeypatch),
            text="A\nB\nC\nD\nE\nF\nG\nH",
            height=24,
            value=5,
            min_value=3,
        )

    def test_list_empty(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), text="")

    def test_list_single_item(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), text="Only")

    def test_list_no_scrollbar(self, tmp_path, monkeypatch):
        """When items fit in view, no scrollbar is drawn."""
        self._draw(self._app(tmp_path, monkeypatch), text="A\nB", height=60)


# ---------------------------------------------------------------------------
# TOGGLE widget rendering
# ---------------------------------------------------------------------------


class TestDrawWidgetPreviewToggle:
    def _app(self, tmp_path, monkeypatch):
        return _make_app(tmp_path, monkeypatch)

    def _draw(self, app, **kw):
        from cyberpunk_designer.drawing import draw_widget_preview

        defaults = dict(type="toggle", x=0, y=0, width=80, height=14, text="WiFi")
        defaults.update(kw)
        w = WidgetConfig(**defaults)
        draw_widget_preview(
            app,
            app.logical_surface,
            w,
            pygame.Rect(0, 0, defaults["width"], defaults["height"]),
            PALETTE["bg"],
            2,
            False,
        )

    def test_toggle_checked(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), checked=True)

    def test_toggle_unchecked(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), checked=False)

    def test_toggle_with_label(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), text="Bluetooth", checked=True)

    def test_toggle_no_label(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), text="")

    def test_toggle_narrow(self, tmp_path, monkeypatch):
        """Toggle that is too narrow for label — should not crash."""
        self._draw(self._app(tmp_path, monkeypatch), text="LongLabel", width=20, height=10)

    def test_toggle_tall(self, tmp_path, monkeypatch):
        self._draw(self._app(tmp_path, monkeypatch), width=120, height=40)


# ===================================================================
# BP — shade constants validation
# ===================================================================

_POSITIVE_SHADES = [
    SHADE_SCANLINE,
    SHADE_GRID_V,
    SHADE_THUMB,
    SHADE_HOVER,
    SHADE_NORMAL,
    SHADE_TOOLBAR_LIGHT,
    SHADE_TOOLBAR_SEP,
    SHADE_PALETTE_HOVER,
    SHADE_BTN_HOVER,
    SHADE_WIDGET_HOVER,
    SHADE_GRID_CANVAS,
]
_NEGATIVE_SHADES = [
    SHADE_GRID_H,
    SHADE_TRACK,
    SHADE_THUMB_BORDER,
    SHADE_PRESSED,
    SHADE_SHADOW,
    SHADE_TOOLBAR_DARK,
    SHADE_TITLE_SHADOW,
    SHADE_BTN_FILL_PRESS,
    SHADE_BTN_FILL,
    SHADE_SEL_FILL,
    SHADE_WIDGET_BG_OFF,
    SHADE_WIDGET_PRESS,
]


class TestShadeConstants:
    def test_positive_shades_are_positive(self):
        for val in _POSITIVE_SHADES:
            assert val > 0, f"Expected positive shade, got {val}"

    def test_negative_shades_are_negative(self):
        for val in _NEGATIVE_SHADES:
            assert val < 0, f"Expected negative shade, got {val}"

    def test_hover_brighter_than_normal(self):
        assert SHADE_HOVER > SHADE_NORMAL

    def test_pressed_darker_than_shadow(self):
        assert SHADE_PRESSED < SHADE_SHADOW

    def test_all_shades_in_range(self):
        all_shades = _POSITIVE_SHADES + _NEGATIVE_SHADES
        for val in all_shades:
            assert -255 <= val <= 255, f"Shade {val} out of 8-bit range"
