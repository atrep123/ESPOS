"""Tests for windowing.toggle_fullscreen and focus_nav beam/loose scoring edge cases."""

from __future__ import annotations

from types import SimpleNamespace

from cyberpunk_designer import windowing
from cyberpunk_designer.focus_nav import (
    activate_focused,
    adjust_focused_value,
    focus_move_direction,
)
from cyberpunk_designer.layout import Layout
from cyberpunk_editor import CyberpunkEditorApp

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path, monkeypatch, *, width=256, height=128, profile=None):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    json_path = tmp_path / "scene.json"
    return CyberpunkEditorApp(json_path, (width, height), profile=profile)


def _widget(wtype="button", x=0, y=0, w=40, h=14, text="btn",
            visible=True, enabled=True, **kw):
    return SimpleNamespace(
        type=wtype, x=x, y=y, width=w, height=h,
        text=text, visible=visible, enabled=enabled,
        _widget_id=kw.get("_widget_id", ""),
        value=kw.get("value", 0),
        min_value=kw.get("min_value", 0),
        max_value=kw.get("max_value", 100),
        checked=kw.get("checked", False),
    )


def _scene_with_widgets(widgets):
    return SimpleNamespace(widgets=widgets)


def _focus_app(widgets, focus_idx=None, sim_input_mode=False):
    """Create a minimal app for focus_nav testing."""
    sc = _scene_with_widgets(widgets)
    app = SimpleNamespace(
        focus_idx=focus_idx,
        focus_edit_value=False,
        sim_input_mode=sim_input_mode,
        _sim_listmodels={},
        _sim_runtime_snapshot={},
        dialog_message="",
    )
    app.state = SimpleNamespace(
        current_scene=lambda: sc,
        selected_idx=None,
        selection=set(),
    )
    app._set_selection = lambda idxs, anchor_idx=None: None
    app._set_status = lambda msg, ttl_sec=0: setattr(app, "dialog_message", msg)
    app._mark_dirty = lambda: None
    return app


# ===========================================================================
# toggle_fullscreen
# ===========================================================================

class TestToggleFullscreen:
    def test_enter_fullscreen(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.fullscreen = False
        windowing.toggle_fullscreen(app)
        assert app.fullscreen is True
        assert isinstance(app.layout, Layout)

    def test_exit_fullscreen_restores_windowed(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        # First enter fullscreen
        app.fullscreen = False
        windowing.toggle_fullscreen(app)
        assert app.fullscreen is True
        # Now exit
        windowing.toggle_fullscreen(app)
        assert app.fullscreen is False
        assert isinstance(app.layout, Layout)

    def test_fullscreen_with_locked_scale(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.fullscreen = False
        app._scale_locked = True
        app.scale = 1
        windowing.toggle_fullscreen(app)
        assert app.fullscreen is True
        assert app.scale >= 1

    def test_fullscreen_toggle_round_trip(self, tmp_path, monkeypatch):
        app = _make_app(tmp_path, monkeypatch)
        app.fullscreen = False
        windowing.toggle_fullscreen(app)
        windowing.toggle_fullscreen(app)
        assert app.fullscreen is False
        assert app.layout.width > 0


# ===========================================================================
# focus_move_direction — beam scoring (overlapping axis)
# ===========================================================================

class TestFocusMoveBeamScoring:
    """Test that beam candidates (sharing axis overlap) are preferred."""

    def test_down_beam_prefers_vertical_overlap(self):
        # Layout:
        #   [btn_top]        at (10, 0,  40, 14)
        #   [btn_below]      at (10, 30, 40, 14)  — beam: x-overlap
        #   [btn_far_right]  at (200, 30, 40, 14) — no beam: no x-overlap
        widgets = [
            _widget("button", x=10, y=0, w=40, h=14, text="top"),
            _widget("button", x=10, y=30, w=40, h=14, text="below"),
            _widget("button", x=200, y=30, w=40, h=14, text="far_right"),
        ]
        app = _focus_app(widgets, focus_idx=0)
        focus_move_direction(app, "down")
        assert app.focus_idx == 1  # beam candidate wins

    def test_right_beam_prefers_horizontal_overlap(self):
        # Layout:
        #   [btn_left]       at (0, 10,  40, 14)
        #   [btn_right]      at (60, 10, 40, 14) — beam: y-overlap
        #   [btn_far_below]  at (60, 200, 40, 14) — no beam: no y-overlap
        widgets = [
            _widget("button", x=0, y=10, w=40, h=14, text="left"),
            _widget("button", x=60, y=10, w=40, h=14, text="right"),
            _widget("button", x=60, y=200, w=40, h=14, text="far_below"),
        ]
        app = _focus_app(widgets, focus_idx=0)
        focus_move_direction(app, "right")
        assert app.focus_idx == 1  # beam candidate wins

    def test_up_beam_candidate(self):
        widgets = [
            _widget("button", x=10, y=0, w=40, h=14, text="top"),
            _widget("button", x=10, y=50, w=40, h=14, text="bottom"),
        ]
        app = _focus_app(widgets, focus_idx=1)
        focus_move_direction(app, "up")
        assert app.focus_idx == 0

    def test_left_beam_candidate(self):
        widgets = [
            _widget("button", x=0, y=10, w=40, h=14, text="left"),
            _widget("button", x=60, y=10, w=40, h=14, text="right"),
        ]
        app = _focus_app(widgets, focus_idx=1)
        focus_move_direction(app, "left")
        assert app.focus_idx == 0


# ===========================================================================
# focus_move_direction — loose fallback (no beam overlap)
# ===========================================================================

class TestFocusMoveLooseFallback:
    """Test loose fallback when no beam candidate exists."""

    def test_down_loose_fallback_diagonal(self):
        # No x-overlap, but btn_diag is the only candidate below
        widgets = [
            _widget("button", x=0, y=0, w=20, h=14, text="cur"),
            _widget("button", x=100, y=50, w=20, h=14, text="diag"),
        ]
        app = _focus_app(widgets, focus_idx=0)
        focus_move_direction(app, "down")
        assert app.focus_idx == 1

    def test_right_loose_fallback_diagonal(self):
        widgets = [
            _widget("button", x=0, y=0, w=20, h=14, text="cur"),
            _widget("button", x=100, y=100, w=20, h=14, text="diag"),
        ]
        app = _focus_app(widgets, focus_idx=0)
        focus_move_direction(app, "right")
        assert app.focus_idx == 1

    def test_no_candidate_wraps_via_focus_cycle(self):
        # Only one focusable widget → down wraps to same
        widgets = [
            _widget("button", x=0, y=0, w=40, h=14, text="only"),
        ]
        app = _focus_app(widgets, focus_idx=0)
        focus_move_direction(app, "down")
        # With single widget, should stay on it (cycle wraps)
        assert app.focus_idx == 0

    def test_up_no_candidate_wraps(self):
        widgets = [
            _widget("button", x=0, y=0, w=40, h=14, text="only"),
        ]
        app = _focus_app(widgets, focus_idx=0)
        focus_move_direction(app, "up")
        assert app.focus_idx == 0


# ===========================================================================
# focus_move_direction — grid layout (multiple rows/columns)
# ===========================================================================

class TestFocusMoveGrid:
    """Test navigation across a 2x2 grid of buttons."""

    def _grid_widgets(self):
        return [
            _widget("button", x=0, y=0, w=40, h=14, text="TL"),     # 0
            _widget("button", x=60, y=0, w=40, h=14, text="TR"),    # 1
            _widget("button", x=0, y=30, w=40, h=14, text="BL"),    # 2
            _widget("button", x=60, y=30, w=40, h=14, text="BR"),   # 3
        ]

    def test_grid_down_from_top_left(self):
        app = _focus_app(self._grid_widgets(), focus_idx=0)
        focus_move_direction(app, "down")
        assert app.focus_idx == 2

    def test_grid_right_from_top_left(self):
        app = _focus_app(self._grid_widgets(), focus_idx=0)
        focus_move_direction(app, "right")
        assert app.focus_idx == 1

    def test_grid_up_from_bottom_right(self):
        app = _focus_app(self._grid_widgets(), focus_idx=3)
        focus_move_direction(app, "up")
        assert app.focus_idx == 1

    def test_grid_left_from_bottom_right(self):
        app = _focus_app(self._grid_widgets(), focus_idx=3)
        focus_move_direction(app, "left")
        assert app.focus_idx == 2

    def test_grid_up_from_top_left_wraps(self):
        app = _focus_app(self._grid_widgets(), focus_idx=0)
        focus_move_direction(app, "up")
        # No widget above → cycle wraps backward
        # Focus should move somewhere (cycle)
        assert app.focus_idx is not None


# ===========================================================================
# focus_move_direction — with unfocusable widgets
# ===========================================================================

class TestFocusMoveSkipsUnfocusable:
    def test_skips_label_between_buttons(self):
        widgets = [
            _widget("button", x=0, y=0, w=40, h=14, text="btn1"),
            _widget("label", x=0, y=20, w=40, h=14, text="label"),  # not focusable
            _widget("button", x=0, y=40, w=40, h=14, text="btn2"),
        ]
        app = _focus_app(widgets, focus_idx=0)
        focus_move_direction(app, "down")
        assert app.focus_idx == 2  # skips over label

    def test_skips_invisible_button(self):
        widgets = [
            _widget("button", x=0, y=0, w=40, h=14, text="btn1"),
            _widget("button", x=0, y=20, w=40, h=14, text="hidden", visible=False),
            _widget("button", x=0, y=40, w=40, h=14, text="btn2"),
        ]
        app = _focus_app(widgets, focus_idx=0)
        focus_move_direction(app, "down")
        assert app.focus_idx == 2


# ===========================================================================
# activate_focused — edge cases
# ===========================================================================

class TestActivateFocusedExtras:
    def test_activate_button_sets_status(self):
        widgets = [_widget("button", text="Submit")]
        app = _focus_app(widgets, focus_idx=0)
        activate_focused(app)
        assert "pressed" in app.dialog_message or "Submit" in app.dialog_message

    def test_activate_slider_toggles_edit_mode(self):
        widgets = [_widget("slider", value=50, min_value=0, max_value=100)]
        app = _focus_app(widgets, focus_idx=0)
        activate_focused(app)
        assert app.focus_edit_value is True
        activate_focused(app)
        assert app.focus_edit_value is False

    def test_activate_no_focus_does_nothing(self):
        widgets = [_widget("button")]
        app = _focus_app(widgets, focus_idx=None)
        activate_focused(app)
        # No crash, no change

    def test_activate_out_of_range_does_nothing(self):
        widgets = [_widget("button")]
        app = _focus_app(widgets, focus_idx=99)
        activate_focused(app)


# ===========================================================================
# adjust_focused_value — edge cases
# ===========================================================================

class TestAdjustFocusedValueExtras:
    def test_non_slider_does_nothing(self):
        widgets = [_widget("button", value=50)]
        app = _focus_app(widgets, focus_idx=0)
        adjust_focused_value(app, 5)
        # button value unchanged by adjust
        assert widgets[0].value == 50

    def test_no_focus_with_no_focusable_widgets(self):
        # Only unfocusable label → ensure_focus finds nothing
        widgets = [_widget("label", value=50)]
        app = _focus_app(widgets, focus_idx=None)
        adjust_focused_value(app, 5)
        assert widgets[0].value == 50
