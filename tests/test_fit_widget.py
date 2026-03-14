"""Tests for cyberpunk_designer/fit_widget.py — fit_selection_to_widget (shrink
or grow) with device-profile and pixel-font code paths."""

from __future__ import annotations

from types import SimpleNamespace
from typing import List, Optional
from unittest.mock import MagicMock

import pygame

from cyberpunk_designer.fit_widget import fit_selection_to_widget
from cyberpunk_designer.state import EditorState
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Helpers (shared pattern with test_fit_text)
# ---------------------------------------------------------------------------


def _w(wtype="label", **kw) -> WidgetConfig:
    defaults = dict(type=wtype, x=0, y=0, width=20, height=10, text="Hello")
    defaults.update(kw)
    return WidgetConfig(**defaults)


class _FakeFont:
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
    for w in widgets or []:
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
    app._text_width_px = lambda txt: len(txt) * char_w

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


class TestFitWidgetNoSelection:
    def test_no_selection(self):
        app = _app([_w()])
        app.state.selected = []
        fit_selection_to_widget(app)
        assert not app._dirty
        app._set_status.assert_called()

    def test_none_selected(self):
        app = _app([_w()])
        app.state.selected = None
        fit_selection_to_widget(app)
        assert not app._dirty


# ---------------------------------------------------------------------------
# Device profile path — can shrink
# ---------------------------------------------------------------------------


class TestFitWidgetDeviceShrink:
    def test_shrinks_width(self):
        # Short text "Hi" (2 chars × 6px = 12 + insets ~16) in 200px wide box
        w = _w("label", text="Hi", width=200, height=30)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width < 200

    def test_shrinks_height(self):
        # Single-line text in very tall box
        w = _w("label", text="Hi", width=200, height=100)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].height < 100

    def test_grows_width(self):
        # Long text in narrow box
        w = _w("label", text="ABCDEFGHIJKLMNOP", width=20, height=10)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width > 20


# ---------------------------------------------------------------------------
# Pixel font path — can shrink
# ---------------------------------------------------------------------------


class TestFitWidgetPixelShrink:
    def test_shrinks_width_pixel(self):
        w = _w("label", text="Hi", width=200, height=30)
        app = _app([w], profile=None, char_w=7, line_h=12)
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width < 200

    def test_grows_width_pixel(self):
        w = _w("label", text="ABCDEFGHIJKLMNOP", width=20, height=10)
        app = _app([w], profile=None, char_w=7, line_h=12)
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width > 20


# ---------------------------------------------------------------------------
# Checkbox
# ---------------------------------------------------------------------------


class TestFitWidgetCheckbox:
    def test_checkbox_device(self):
        w = _w("checkbox", text="Enable logging", width=200, height=30)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        # Should shrink to fit the text
        assert sc.widgets[0].width < 200

    def test_checkbox_pixel(self):
        w = _w("checkbox", text="OK", width=200, height=30)
        app = _app([w], profile=None)
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width < 200


# ---------------------------------------------------------------------------
# Wrap mode
# ---------------------------------------------------------------------------


class TestFitWidgetWrap:
    def test_wrap_device(self):
        w = _w(
            "label",
            text="word1 word2 word3 word4 word5",
            width=60,
            height=100,
            text_overflow="wrap",
        )
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        # Height should shrink to fit wrapped content
        assert sc.widgets[0].height < 100

    def test_wrap_pixel(self):
        w = _w("label", text="word1 word2 word3", width=80, height=100, text_overflow="wrap")
        app = _app([w], profile=None, char_w=7, line_h=12)
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].height < 100


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestFitWidgetEdgeCases:
    def test_locked_skipped(self):
        w = _w("label", text="Long text here", width=200, height=100, locked=True)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width == 200

    def test_empty_text_skipped(self):
        w = _w("label", text="", width=200, height=100)
        app = _app([w])
        app.state.selected = [0]
        fit_selection_to_widget(app)
        assert not app._dirty

    def test_snap_enabled(self):
        w = _w("label", text="Hello World!!!", width=200, height=100)
        app = _app([w], snap=True, profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width % 8 == 0
        assert sc.widgets[0].height % 8 == 0

    def test_icon_type(self):
        w = _w("icon", text="", icon_char="★", width=100, height=100)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width < 100

    def test_multiple_widgets(self):
        w1 = _w("label", text="A", width=200, height=100)
        w2 = _w("label", text="B", width=200, height=100)
        app = _app([w1, w2], profile="esp32os_256x128_gray4")
        app.state.selected = [0, 1]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width < 200
        assert sc.widgets[1].width < 200

    def test_clamped_to_scene(self):
        w = _w("label", text="A" * 200, width=20, height=10)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width <= 256

    def test_already_optimal_noop(self):
        # Widget already at the computed optimal size
        # 2 chars × 6px = 12 + insets (2*2=4) = 16 → snaps to GRID boundaries
        w = _w("label", text="Hi", width=16, height=12)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        # No crash; may or may not change based on exact inset calc

    def test_invalid_index(self):
        app = _app([_w()])
        app.state.selected = [99]
        fit_selection_to_widget(app)
        assert not app._dirty


# ---------------------------------------------------------------------------
# Deep coverage — _parse_max_lines, overflow fallback, locked/empty messages
# ---------------------------------------------------------------------------


class TestFitWidgetDeep:
    def test_widget_with_max_lines(self):
        """Widget with max_lines exercises _parse_max_lines valid path (lines 39-40)."""
        w = _w(
            "label",
            text="AAA BBB CCC DDD EEE",
            width=80,
            height=100,
            text_overflow="wrap",
            max_lines=2,
        )
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].height <= 100

    def test_invalid_overflow_fallback(self):
        """Invalid text_overflow falls back to ellipsis (line 71)."""
        w = _w("label", text="Short", width=200, height=100, text_overflow="GARBAGE_MODE")
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width <= 200

    def test_locked_plus_changed_message(self):
        """Mix of locked and unlocked widgets shows locked count (line 160)."""
        w1 = _w("label", text="Short", width=200, height=100, locked=True)
        w2 = _w("label", text="Short", width=200, height=100)
        app = _app([w1, w2], profile="esp32os_256x128_gray4")
        app.state.selected = [0, 1]
        fit_selection_to_widget(app)
        status_calls = [str(c) for c in app._set_status.call_args_list]
        assert any("locked" in s.lower() or "Skipped" in s for s in status_calls)

    def test_empty_text_plus_changed_message(self):
        """Mix of empty-text and normal widgets shows empty count (line 162)."""
        w1 = _w("label", text="", width=200, height=100)
        w2 = _w("label", text="Short", width=200, height=100)
        app = _app([w1, w2], profile="esp32os_256x128_gray4")
        app.state.selected = [0, 1]
        fit_selection_to_widget(app)
        status_calls = [str(c) for c in app._set_status.call_args_list]
        assert any("empty" in s.lower() or "text" in s.lower() for s in status_calls)


# ---------------------------------------------------------------------------
# LIST widget fitting
# ---------------------------------------------------------------------------


class TestFitWidgetList:
    def test_list_device_shrinks_height(self):
        """LIST with 3 items in a tall box should shrink height to fit content."""
        w = _w("list", text="A\nB\nC", width=80, height=100, items=["A", "B", "C"])
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].height < 100

    def test_list_device_width_fits_longest(self):
        """LIST width should fit the longest item."""
        w = _w(
            "list",
            text="Short\nVeryLongItemName\nMed",
            width=20,
            height=40,
            items=["Short", "VeryLongItemName", "Med"],
        )
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width > 20

    def test_list_pixel_font(self):
        """LIST fitting via pixel font path (no device profile)."""
        w = _w("list", text="Foo\nBar\nBaz", width=200, height=100, items=["Foo", "Bar", "Baz"])
        app = _app([w], profile=None, char_w=7, line_h=12)
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].height < 100

    def test_list_empty_items_from_text(self):
        """LIST with only text (no items attr) should parse items from newlines."""
        w = _w("list", text="X\nY", width=200, height=100)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].height < 100


# ---------------------------------------------------------------------------
# TOGGLE widget fitting
# ---------------------------------------------------------------------------


class TestFitWidgetToggle:
    def test_toggle_device_shrinks(self):
        """TOGGLE with short label should shrink from large box."""
        w = _w("toggle", text="On", width=200, height=100)
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width < 200
        assert sc.widgets[0].height < 100

    def test_toggle_pixel_font(self):
        """TOGGLE fitting via pixel font path."""
        w = _w("toggle", text="WiFi", width=200, height=100)
        app = _app([w], profile=None, char_w=7, line_h=12)
        app.state.selected = [0]
        fit_selection_to_widget(app)
        sc = app.state.current_scene()
        assert sc.widgets[0].width < 200

    def test_toggle_no_label(self):
        """TOGGLE with empty label should still produce valid size (track only)."""
        w = _w("toggle", text="", width=200, height=100)
        # Empty text is skipped by fit_widget, so it should remain unchanged
        app = _app([w], profile="esp32os_256x128_gray4")
        app.state.selected = [0]
        fit_selection_to_widget(app)
        # No crash — empty text is skipped
