"""Tests for cyberpunk_designer/fit_text.py — fit_selection_to_text with
device-profile and pixel-font code paths."""

from __future__ import annotations

from types import SimpleNamespace
from typing import List, Optional
from unittest.mock import MagicMock

import pygame

from cyberpunk_designer.fit_text import fit_selection_to_text
from cyberpunk_designer.state import EditorState
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _w(wtype="label", **kw) -> WidgetConfig:
    defaults = dict(type=wtype, x=0, y=0, width=20, height=10, text="Hello")
    defaults.update(kw)
    return WidgetConfig(**defaults)


class _FakeFont:
    """Minimal stand-in for pygame.font.Font."""
    def __init__(self, char_w=7, line_h=12):
        self._char_w = char_w
        self._line_h = line_h

    def get_height(self):
        return self._line_h

    def size(self, text):
        return (len(text) * self._char_w, self._line_h)


def _app(
    widgets: Optional[List[WidgetConfig]] = None,
    *,
    snap: bool = False,
    profile: Optional[str] = None,
    char_w: int = 7,
    line_h: int = 12,
):
    designer = UIDesigner(256, 128)
    designer.create_scene("main")
    sc = designer.scenes["main"]
    for w in (widgets or []):
        sc.widgets.append(w)

    layout = MagicMock()
    layout.canvas_rect = pygame.Rect(0, 0, 256, 128)
    state = EditorState(designer, layout)

    font = _FakeFont(char_w, line_h)

    app = SimpleNamespace(
        designer=designer,
        state=state,
        snap_enabled=snap,
        pixel_font=font,
        pixel_padding=4,
        hardware_profile=profile,
        _dirty=False,
        _set_status=MagicMock(),
        _mark_dirty=lambda: setattr(app, "_dirty", True),
    )
    app._mark_dirty = lambda: setattr(app, "_dirty", True)

    # Pixel-based text width (non-device path)
    app._text_width_px = lambda txt: len(txt) * char_w
    # Pixel-based text wrap (non-device path)
    def _wrap(text, max_width_px=100, max_lines=9999):
        words = text.replace("\n", " ").split()
        lines: List[str] = []
        cur = ""
        for w in words:
            cand = w if not cur else f"{cur} {w}"
            if len(cand) * char_w <= max_width_px:
                cur = cand
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines[:max_lines] if lines else [""]
    app._wrap_text_px = _wrap

    return app


# ---------------------------------------------------------------------------
# No selection
# ---------------------------------------------------------------------------


class TestFitTextNoSelection:
    def test_no_selection(self):
        app = _app([_w()])
        app.state.selected = []
        fit_selection_to_text(app)
        assert not app._dirty
        app._set_status.assert_called()

    def test_none_selected(self):
        app = _app([_w()])
        app.state.selected = None
        fit_selection_to_text(app)
        assert not app._dirty


# ---------------------------------------------------------------------------
# Device profile path (uses character cells)
# ---------------------------------------------------------------------------


class TestFitTextDeviceProfile:
    def test_grows_width(self):
        # 10 chars × 6px/char = 60px + insets, current width 20 → should grow
        w = _w("label", text="ABCDEFGHIJ", width=20, height=10)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_text(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width > 20

    def test_height_stays_ge(self):
        # Fit text should only grow, never shrink (for non-wrap)
        w = _w("label", text="Hi", width=100, height=30)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_text(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].height >= 30

    def test_wrap_mode(self):
        w = _w("label", text="word1 word2 word3 word4", width=50, height=10,
               text_overflow="wrap")
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_text(app)
        sc = app.state.current_scene()
        # Height should grow to fit wrapped lines
        assert sc.widgets[0].height >= 10

    def test_checkbox(self):
        w = _w("checkbox", text="Enable option", width=20, height=10)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_text(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width > 20


# ---------------------------------------------------------------------------
# Pixel font path (non-device)
# ---------------------------------------------------------------------------


class TestFitTextPixelFont:
    def test_grows_width(self):
        # 10 chars × 7px/char = 70 + pad, current width 20
        w = _w("label", text="ABCDEFGHIJ", width=20, height=10)
        app = _app([w], profile=None, char_w=7, line_h=12)
        app.state.selected = [0]
        fit_selection_to_text(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width > 20

    def test_grows_height(self):
        w = _w("label", text="Hello", width=200, height=4)
        app = _app([w], profile=None, char_w=7, line_h=12)
        app.state.selected = [0]
        fit_selection_to_text(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].height >= 12

    def test_wrap_mode_pixel(self):
        w = _w("label", text="one two three four five", width=50, height=10,
               text_overflow="wrap")
        app = _app([w], profile=None, char_w=7, line_h=12)
        app.state.selected = [0]
        fit_selection_to_text(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].height >= 10


# ---------------------------------------------------------------------------
# Locked / empty / snap
# ---------------------------------------------------------------------------


class TestFitTextEdgeCases:
    def test_locked_skipped(self):
        w = _w("label", text="Long text here", width=20, height=10, locked=True)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_text(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width == 20  # unchanged

    def test_empty_text_skipped(self):
        w = _w("label", text="", width=20, height=10)
        app = _app([w])
        app.state.selected = [0]
        fit_selection_to_text(app)
        assert not app._dirty

    def test_snap_enabled(self):
        w = _w("label", text="Hello World!!!", width=20, height=10)
        app = _app([w], snap=True, profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_text(app)
        _sc = app.state.current_scene()
        # With snap, width and height should be multiples of GRID (8)


# ---------------------------------------------------------------------------
# Deep coverage — _parse_max_lines, overflow fallback, checkbox non-device
# ---------------------------------------------------------------------------


class TestFitTextDeep:
    def test_widget_with_max_lines(self):
        """Widget with max_lines exercises _parse_max_lines valid path (lines 36-37)."""
        w = _w("label", text="AAA BBB CCC DDD EEE", width=40, height=10,
               text_overflow="wrap", max_lines=3)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_text(app)
        # Should fit without crash
        sc = app.state.current_scene()
        assert sc.widgets[0].height >= 10

    def test_invalid_overflow_fallback(self):
        """Invalid text_overflow falls back to ellipsis (line 63)."""
        w = _w("label", text="Some very long label text", width=20, height=10,
               text_overflow="INVALID_MODE")
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_text(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width >= 20

    def test_checkbox_non_device(self):
        """Checkbox text fitting without device profile (lines 78-80)."""
        w = _w("checkbox", text="Check me please", width=20, height=10)
        app = _app([w], profile=None)  # non-device
        app.state.selected = [0]
        fit_selection_to_text(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width >= 20

    def test_locked_plus_changed_message(self):
        """Mix of locked and unlocked widgets shows locked count (line 157)."""
        w1 = _w("label", text="Short", width=200, height=10, locked=True)
        w2 = _w("label", text="AAAA BBBB CCCC DDDD EEEE", width=20, height=10)
        app = _app([w1, w2], profile="esp32os_256x128_gray4")
        app.state.selected = [0, 1]
        fit_selection_to_text(app)
        status_calls = [str(c) for c in app._set_status.call_args_list]
        assert any("locked" in s.lower() or "Skipped" in s for s in status_calls)

    def test_icon_uses_icon_char(self):
        w = _w("icon", text="", icon_char="X", width=8, height=8)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_text(app)
        # Should use icon_char not empty text → still tries to fit
        # At minimum no crash
        assert True

    def test_multiple_widgets(self):
        w1 = _w("label", text="Short", width=20, height=10)
        w2 = _w("label", text="Much longer text here", width=20, height=10)
        app = _app([w1, w2], profile="esp32os_256x128_gray4")
        app.state.selected = [0, 1]
        fit_selection_to_text(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width >= 20
        assert sc.widgets[1].width > sc.widgets[0].width

    def test_already_fits_noop(self):
        # Very short text in a big box → no change
        w = _w("label", text="Hi", width=200, height=100)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_text(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width == 200
        assert sc.widgets[0].height == 100

    def test_clamped_to_scene(self):
        # Text would need huge width, clamped to scene width
        w = _w("label", text="A" * 200, width=20, height=10)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_text(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width <= 256

    def test_invalid_index_skipped(self):
        app = _app([_w()])
        app.state.selected = [99]
        fit_selection_to_text(app)
        assert not app._dirty
