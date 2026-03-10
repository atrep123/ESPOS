"""Mutation-killing tests — target specific boundary conditions and
operator/constant changes that a mutation testing tool would introduce.

Each test is named with the mutant it kills (e.g. ``test_kills_mutant_X``).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import List, Optional
from unittest.mock import MagicMock

import pygame

from cyberpunk_designer.focus_nav import (
    focus_move_direction,
    set_focus,
)
from cyberpunk_designer.state import EditorState
from cyberpunk_designer.text_metrics import (
    ellipsize_chars,
    inner_text_area_px,
    text_truncates_in_widget,
    wrap_text_chars,
)
from ui_designer import UIDesigner, WidgetConfig

# ── helpers ──────────────────────────────────────────────────────────

def _w(wtype="button", **kw) -> WidgetConfig:
    defaults = dict(type=wtype, x=0, y=0, width=30, height=12, text="w")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _app(widgets: Optional[List[WidgetConfig]] = None):
    designer = UIDesigner(256, 128)
    designer.create_scene("main")
    sc = designer.scenes["main"]
    for w in (widgets or []):
        sc.widgets.append(w)
    layout = MagicMock()
    layout.canvas_rect = pygame.Rect(0, 0, 256, 128)
    state = EditorState(designer, layout)
    app = SimpleNamespace(
        designer=designer,
        state=state,
        snap_enabled=False,
        clipboard=[],
        focus_idx=None,
        focus_edit_value=False,
        sim_input_mode=False,
        pointer_pos=(0, 0),
        scene_rect=pygame.Rect(0, 0, 256, 128),
        layout=layout,
        _dirty=False,
        _set_status=MagicMock(),
        _mark_dirty=lambda: setattr(app, "_dirty", True),
        _set_selection=lambda indices, anchor_idx=None: None,
    )
    app._mark_dirty = lambda: setattr(app, "_dirty", True)
    return app


# ═══════════════════════════════════════════════════════════════════════
# focus_nav.py — direction gates (dy >= 0 / dy <= 0 / dx >= 0 / dx <= 0)
# ═══════════════════════════════════════════════════════════════════════

class TestFocusMoveDirectionGates:
    """Kill mutants that flip >= to > or <= to < in the direction gate checks."""

    def test_down_rejects_widget_at_same_y(self):
        """dy == 0 → must be rejected by `dy <= 0`.  Mutant: `dy < 0`."""
        # 3 widgets: w0 at center, w1 at same y (should be skipped),
        # w2 below (valid target)
        w0 = _w(x=0, y=50, width=30, height=10)
        w1 = _w(x=60, y=50, width=30, height=10)  # same y
        w2 = _w(x=0, y=80, width=30, height=10)    # below
        app = _app([w0, w1, w2])
        set_focus(app, 0)
        focus_move_direction(app, "down")
        # Must pick w2, not w1 (w1 has dy==0, which the gate rejects)
        assert app.focus_idx == 2

    def test_up_rejects_widget_at_same_y(self):
        """dy == 0 → must be rejected by `dy >= 0`.  Mutant: `dy > 0`."""
        w0 = _w(x=0, y=50, width=30, height=10)
        w1 = _w(x=60, y=50, width=30, height=10)  # same y
        w2 = _w(x=0, y=10, width=30, height=10)    # above
        app = _app([w0, w1, w2])
        set_focus(app, 0)
        focus_move_direction(app, "up")
        assert app.focus_idx == 2

    def test_right_rejects_widget_at_same_x(self):
        """dx == 0 → must be rejected by `dx <= 0`.  Mutant: `dx < 0`."""
        w0 = _w(x=50, y=0, width=30, height=10)
        w1 = _w(x=50, y=60, width=30, height=10)  # same x
        w2 = _w(x=100, y=0, width=30, height=10)   # to the right
        app = _app([w0, w1, w2])
        set_focus(app, 0)
        focus_move_direction(app, "right")
        assert app.focus_idx == 2

    def test_left_rejects_widget_at_same_x(self):
        """dx == 0 → must be rejected by `dx >= 0`.  Mutant: `dx > 0`."""
        w0 = _w(x=50, y=0, width=30, height=10)
        w1 = _w(x=50, y=60, width=30, height=10)  # same x
        w2 = _w(x=10, y=0, width=30, height=10)    # to the left
        app = _app([w0, w1, w2])
        set_focus(app, 0)
        focus_move_direction(app, "left")
        assert app.focus_idx == 2


class TestFocusMoveOverlapVsNoOverlap:
    """Kill mutants that remove the 1_000_000 penalty for non-overlapping
    widgets or that change the overlap > 0 threshold."""

    def test_overlapping_preferred_over_nonoverlapping(self):
        """Kill mutant: removing the 1_000_000 gap penalty."""
        # w0 at (0,0).  w1 directly below and overlapping horizontally.
        # w2 below but far to the right (no overlap).
        w0 = _w(x=0, y=0, width=40, height=10)
        w1 = _w(x=5, y=20, width=40, height=10)   # overlaps w0's x-range
        w2 = _w(x=200, y=15, width=40, height=10)  # no overlap, slightly closer y
        app = _app([w0, w1, w2])
        set_focus(app, 0)
        focus_move_direction(app, "down")
        assert app.focus_idx == 1, "Overlapping widget should be preferred"

    def test_overlap_exactly_zero_treated_as_no_overlap(self):
        """overlap = 0 → no beam match. Kill mutant: overlap >= 0."""
        # Widgets side-by-side: w0.right == w1.left → overlap = 0
        w0 = _w(x=0, y=0, width=40, height=10)
        w1 = _w(x=40, y=20, width=40, height=10)  # right at boundary
        w2 = _w(x=0, y=20, width=40, height=10)    # fully overlapping
        app = _app([w0, w1, w2])
        set_focus(app, 0)
        focus_move_direction(app, "down")
        # w2 overlaps → beam match → preferred over w1 (no overlap → loose)
        assert app.focus_idx == 2


class TestFocusMoveScoreWeights:
    """Kill mutants that change primary/secondary/dist2 weight multipliers."""

    def test_primary_distance_dominates_secondary(self):
        """Kill mutant: 10_000 → 1_000 (secondary becomes competitive)."""
        # Both below w0 and overlapping horizontally. w1 closer y, w2 farther y.
        # w0 x-span: 50..90, w1 x-span: 50..90 (exact overlap), w2 x-span: 50..90
        w0 = _w(x=50, y=0, width=40, height=10)    # center_y=5
        w1 = _w(x=50, y=15, width=40, height=10)   # center_y=20, closer
        w2 = _w(x=50, y=80, width=40, height=10)   # center_y=85, farther
        app = _app([w0, w1, w2])
        set_focus(app, 0)
        focus_move_direction(app, "down")
        assert app.focus_idx == 1, "Closer primary (y) should win"

    def test_horizontal_primary_distance_dominates(self):
        """Same as above but for horizontal movement."""
        # All on same y-band so they overlap vertically
        w0 = _w(x=0, y=50, width=10, height=40)    # center_x=5
        w1 = _w(x=15, y=50, width=10, height=40)   # center_x=20, closer
        w2 = _w(x=80, y=50, width=10, height=40)   # center_x=85, farther
        app = _app([w0, w1, w2])
        set_focus(app, 0)
        focus_move_direction(app, "right")
        assert app.focus_idx == 1, "Closer primary (x) should win"


class TestFocusMoveWrapAround:
    """Kill mutant: fallback direction for cycle (1 vs -1)."""

    def test_down_wraps_via_forward_cycle(self):
        """When no widget is below, cycle forward (direction=1)."""
        w0 = _w(x=0, y=100, width=30, height=10)  # bottom-most
        w1 = _w(x=0, y=0, width=30, height=10)     # top
        app = _app([w0, w1])
        set_focus(app, 0)
        focus_move_direction(app, "down")
        assert app.focus_idx == 1

    def test_up_wraps_via_backward_cycle(self):
        """When no widget is above, cycle backward (direction=-1)."""
        w0 = _w(x=0, y=0, width=30, height=10)     # top-most
        w1 = _w(x=0, y=100, width=30, height=10)   # bottom
        app = _app([w0, w1])
        set_focus(app, 0)
        focus_move_direction(app, "up")
        assert app.focus_idx == 1


# ═══════════════════════════════════════════════════════════════════════
# text_metrics.py — boundary conditions
# ═══════════════════════════════════════════════════════════════════════

class TestEllipsizeCharsBoundaries:
    """Kill mutants in ellipsize_chars boundary checks."""

    def test_exact_fit_no_ellipsis(self):
        """Kill mutant: `<=` → `<` in `if len(s) <= max_chars`."""
        assert ellipsize_chars("abc", 3) == "abc"

    def test_one_over_ellipsized(self):
        """Sanity: 4 chars in 3 → ellipsis."""
        assert ellipsize_chars("abcd", 3) == "..."

    def test_max_chars_zero_returns_empty(self):
        """Kill mutant: `<=` → `<` in `if max_chars <= 0`."""
        assert ellipsize_chars("hello", 0) == ""

    def test_ellipsis_longer_than_max_chars(self):
        """Kill mutant: `>=` → `>` in `if len(ellipsis) >= max_chars`."""
        assert ellipsize_chars("abcdef", 3, ellipsis="...") == "..."

    def test_empty_ellipsis_truncates_plain(self):
        """Kill mutant: removing `if not ellipsis` branch."""
        assert ellipsize_chars("abcdef", 3, ellipsis="") == "abc"

    def test_truncation_point_exact(self):
        """Kill mutant: `max_chars - len(ellipsis)` → `max_chars - len(ellipsis) + 1`."""
        result = ellipsize_chars("abcdefgh", 5, ellipsis="..")
        assert result == "abc.."
        assert len(result) == 5


class TestWrapTextCharsBoundaries:
    """Kill mutants in wrap_text_chars."""

    def test_max_chars_zero_returns_empty(self):
        """Kill mutant: `<=` → `<` in `if max_chars <= 0`."""
        lines, trunc = wrap_text_chars("hello", max_chars=0, max_lines=5)
        assert lines == []
        assert trunc is True

    def test_max_lines_zero_returns_empty(self):
        """Kill mutant: `<=` → `<` in `if max_lines <= 0`."""
        lines, trunc = wrap_text_chars("hello", max_chars=10, max_lines=0)
        assert lines == []
        assert trunc is True

    def test_exact_fit_one_line(self):
        """Kill mutant: `<=` → `<` in `if len(cand) <= max_chars`."""
        lines, trunc = wrap_text_chars("abc", max_chars=3, max_lines=5)
        assert lines == ["abc"]
        assert trunc is False

    def test_max_lines_reached_truncates(self):
        """Kill mutant: `>=` → `>` in `if len(lines) >= max_lines`."""
        lines, trunc = wrap_text_chars("aaa bbb ccc", max_chars=5, max_lines=2)
        assert len(lines) == 2
        assert trunc is True

    def test_long_word_chunked_exactly(self):
        """Kill mutant: range(0, len(word), max_chars) off-by-one."""
        lines, trunc = wrap_text_chars("abcdef", max_chars=3, max_lines=10)
        assert lines == ["abc", "def"]
        assert trunc is False


class TestTextTruncatesInWidget:
    """Kill mutants in text_truncates_in_widget."""

    def test_exact_fit_not_truncated(self):
        """Kill mutant: `>` → `>=` in `return len(flat) > max_chars`."""
        # inner_w for a 30px wide bordered button: 30 - (1+1)*2 = 26px
        # 26 // 6 = 4 chars. So exactly 4 chars should NOT truncate.
        w = _w(width=30, height=12, text="abcd", border=True)
        assert text_truncates_in_widget(w, "abcd") is False

    def test_one_char_over_truncates(self):
        """One char past max_chars DOES truncate."""
        w = _w(width=30, height=12, text="abcde", border=True)
        assert text_truncates_in_widget(w, "abcde") is True

    def test_zero_width_widget_truncates_text(self):
        """Kill mutant: `<=` → `<` in `if inner_w <= 0`."""
        w = _w(width=0, height=12, text="a")
        assert text_truncates_in_widget(w, "a") is True

    def test_zero_height_widget_truncates_text(self):
        """Kill mutant: `<=` → `<` in `if inner_h <= 0`."""
        w = _w(width=30, height=0, text="a")
        assert text_truncates_in_widget(w, "a") is True

    def test_empty_text_not_truncated(self):
        """Empty text should never be flagged as truncated."""
        w = _w(width=30, height=12, text="")
        assert text_truncates_in_widget(w, "") is False


class TestInnerTextAreaPx:
    """Kill mutants in inner_text_area_px calculations."""

    def test_zero_width_returns_zero(self):
        """Kill mutant: `<=` → `<` in `if width <= 0`."""
        # WidgetConfig enforces min 1, so use SimpleNamespace
        w = SimpleNamespace(type="button", width=0, height=20, border=True)
        assert inner_text_area_px(w) == (0, 0)

    def test_zero_height_returns_zero(self):
        w = SimpleNamespace(type="button", width=20, height=0, border=True)
        assert inner_text_area_px(w) == (0, 0)

    def test_negative_width_returns_zero(self):
        w = SimpleNamespace(type="button", width=-5, height=20, border=True)
        assert inner_text_area_px(w) == (0, 0)

    def test_bordered_button_inset(self):
        """Kill mutant: changing `(inset + pad) * 2` term.
        border=True → inset=1, pad=1 → deduction = 4 per axis."""
        w = _w(width=20, height=16, border=True)
        inner_w, inner_h = inner_text_area_px(w)
        assert inner_w == 20 - 4  # (1+1)*2
        assert inner_h == 16 - 4

    def test_no_border_less_inset(self):
        """Kill mutant: border False → inset should be 0."""
        w = _w(width=20, height=16, border=False)
        inner_w, inner_h = inner_text_area_px(w)
        assert inner_w == 20 - 2  # (0+1)*2
        assert inner_h == 16 - 2

    def test_checkbox_box_size_subtracted(self):
        """Kill mutant: messing with `box = 6` calculation."""
        w = _w(type="checkbox", width=40, height=12)
        inner_w, _h = inner_text_area_px(w)
        # box = 6 (height > 6), inner_w = 40 - 6 - 4 = 30
        assert inner_w == 30

    def test_checkbox_small_height(self):
        """Kill mutant: `height - 2` for box when height <= 6."""
        w = _w(type="checkbox", width=40, height=6)
        inner_w, _h = inner_text_area_px(w)
        # box = 6-2 = 4, inner_w = 40 - 4 - 4 = 32
        assert inner_w == 32


# ═══════════════════════════════════════════════════════════════════════
# layout.py — layout rectangle calculations
# ═══════════════════════════════════════════════════════════════════════

class TestLayoutCalculations:
    """Kill mutants in layout.py region calculations."""

    def _make_layout(self, width=800, height=600):
        from cyberpunk_designer.layout import Layout
        return Layout(width, height)

    def test_body_top_is_toolbar_plus_tabs(self):
        """Kill mutant: `+` → `-` in toolbar_h + scene_tabs_h."""
        lm = self._make_layout()
        expected = lm.toolbar_h + lm.scene_tabs_h
        assert lm._body_top == expected
        assert expected > 0

    def test_canvas_width_deducts_both_panels(self):
        """Kill mutant: dropping one of palette_w or inspector_w."""
        lm = self._make_layout()
        cr = lm.canvas_rect
        assert cr.width == lm.width - lm.palette_w - lm.inspector_w

    def test_palette_height_fills_body(self):
        """Kill mutant: `+` → `-` in height - body_top - status_h."""
        lm = self._make_layout()
        pr = lm.palette_rect
        expected = lm.height - lm._body_top - lm.status_h
        assert pr.height == expected
        assert expected > 0

    def test_canvas_rect_position(self):
        """Kill mutant: x offset for canvas not accounting for palette."""
        lm = self._make_layout()
        r = lm.canvas_rect
        assert r.x == lm.palette_w
        assert r.y == lm._body_top

    def test_inspector_on_right_edge(self):
        """Kill mutant: inspector x not at width - inspector_w."""
        lm = self._make_layout()
        r = lm.inspector_rect
        assert r.x == lm.width - lm.inspector_w

    def test_status_at_bottom(self):
        """Kill mutant: status y = height - status_h."""
        lm = self._make_layout()
        r = lm.status_rect
        assert r.y == lm.height - lm.status_h
        assert r.width == lm.width

    def test_scene_tabs_below_toolbar(self):
        """Kill mutant: scene_tabs y != toolbar_h."""
        lm = self._make_layout()
        r = lm.scene_tabs_rect
        assert r.y == lm.toolbar_h

    def test_nonzero_scene_tabs_shifts_body_down(self):
        """Kill mutant: scene_tabs_h not included in _body_top."""
        from cyberpunk_designer.layout import Layout
        lm = Layout(800, 600, scene_tabs_h=20)
        assert lm._body_top == lm.toolbar_h + 20
