"""Tests targeting uncovered exception branches in clipboard, transforms, propagation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pygame
import pytest

from ui_models import WidgetConfig

# ---------------------------------------------------------------------------
# Shared helpers
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


def _make_save_raise(app):
    """Make _save_state raise so except-branches are covered."""
    app.designer._save_state = MagicMock(side_effect=RuntimeError("boom"))


def _make_asdict_raise(monkeypatch):
    """Monkeypatch asdict in a module so WidgetConfig(**asdict(w)) raises."""
    # We'll use a broken __iter__ on widget instead
    pass


class _BrokenWidget:
    """Widget-like object whose asdict() will raise."""

    def __init__(self):
        self.type = "label"
        self.x = 0
        self.y = 0
        self.width = 60
        self.height = 20
        self.text = "hello"


# ===========================================================================
# selection_ops/clipboard.py
# ===========================================================================


class TestClipboardExceptions:
    """Cover except-branches in clipboard.py."""

    # ---- copy_selection: asdict exception (lines 25-26) ----
    def test_copy_selection_asdict_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        # Make asdict raise for the widget
        original_asdict = clipboard.asdict
        call_count = [0]

        def bad_asdict(obj):
            call_count[0] += 1
            if call_count[0] <= 1:
                raise RuntimeError("broken asdict")
            return original_asdict(obj)

        monkeypatch.setattr(clipboard, "asdict", bad_asdict)
        clipboard.copy_selection(app)
        # Should have continued past the exception — 0 copied
        assert app.clipboard == []

    # ---- paste_clipboard: _save_state exception (lines 39-40) ----
    def test_paste_clipboard_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.clipboard = [_w(x=10, y=10)]
        app.pointer_pos = (100, 100)
        _make_save_raise(app)
        clipboard.paste_clipboard(app)
        # Should still paste despite _save_state error
        assert len(app.state.current_scene().widgets) == 2

    # ---- paste_clipboard: empty clipboard after save (line 43) ----
    def test_paste_clipboard_becomes_empty_after_save(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.clipboard = [_w()]
        app.pointer_pos = (100, 100)

        def clear_clipboard():
            app.clipboard = []

        app.designer._save_state = clear_clipboard
        clipboard.paste_clipboard(app)
        # After _save_state cleared clipboard, should return early

    # ---- paste_clipboard: pointer calc exception (lines 56-57) ----
    def test_paste_clipboard_pointer_calc_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.clipboard = [_w(x=10, y=10)]

        # pointer_pos passes collidepoint but causes exception inside int() math
        # Create a scene_rect that returns True for collidepoint but pointer_pos
        # has values that break int() arithmetic
        class BadRect:
            x = 0
            y = 0

            def collidepoint(self, pos):
                return True

        app.scene_rect = BadRect()
        app.pointer_pos = (float("inf"), float("inf"))
        clipboard.paste_clipboard(app)
        # Should fall back to GRID*2 offset
        assert len(app.state.current_scene().widgets) == 2

    # ---- paste_clipboard: asdict exception in loop (lines 63-64) ----
    def test_paste_clipboard_asdict_exception_in_loop(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.clipboard = [_w(x=10, y=10)]
        app.pointer_pos = (100, 100)

        monkeypatch.setattr(clipboard, "asdict", MagicMock(side_effect=RuntimeError("bad")))
        clipboard.paste_clipboard(app)
        # asdict fails → continue → 0 pasted
        assert len(app.state.current_scene().widgets) == 1  # no new widgets

    # ---- cut_selection: nothing selected (line 85-86) ----
    def test_cut_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = []
        clipboard.cut_selection(app)

    # ---- duplicate_selection: _save_state exception (lines 99-100) ----
    def test_duplicate_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        _make_save_raise(app)
        clipboard.duplicate_selection(app)
        assert len(app.state.current_scene().widgets) == 2

    # ---- duplicate_selection: asdict exception (lines 108-109) ----
    def test_duplicate_asdict_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        monkeypatch.setattr(clipboard, "asdict", MagicMock(side_effect=RuntimeError("bad")))
        clipboard.duplicate_selection(app)
        # asdict fails → 0 duplicated
        assert len(app.state.current_scene().widgets) == 1

    # ---- copy_to_next_scene: _save_state exception (lines 136-137) ----
    def test_copy_to_next_scene_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        # Need 2 scenes
        from ui_designer import SceneConfig

        app.designer.scenes["scene2"] = SceneConfig(
            name="scene2", width=256, height=128, widgets=[], bg_color="black"
        )
        app.state.selected = [0]
        _make_save_raise(app)
        clipboard.copy_to_next_scene(app)

    # ---- copy_to_next_scene: only 1 scene (line 141) ----
    def test_copy_to_next_scene_single_scene(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        # Only 1 scene by default
        clipboard.copy_to_next_scene(app)

    # ---- copy_to_next_scene: nothing selected (lines 145-146) — actually line coverage ----
    def test_copy_to_next_scene_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        clipboard.copy_to_next_scene(app)

    # ---- copy_to_next_scene: OOB index (lines 166-167) ----
    def test_copy_to_next_scene_oob_index(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        from ui_designer import SceneConfig

        app.designer.scenes["scene2"] = SceneConfig(
            name="scene2", width=256, height=128, widgets=[], bg_color="black"
        )
        app.state.selected = [999]  # OOB
        clipboard.copy_to_next_scene(app)

    # ---- copy_to_next_scene: target scene None (lines 172-173) ----
    def test_copy_to_next_scene_target_none(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        from ui_designer import SceneConfig

        app.designer.scenes["scene2"] = SceneConfig(
            name="scene2", width=256, height=128, widgets=[], bg_color="black"
        )
        app.state.selected = [0]
        # Make scenes.get return None for the target
        current = app.designer.current_scene
        names = list(app.designer.scenes.keys())
        ci = names.index(current)
        next_name = names[(ci + 1) % len(names)]
        app.designer.scenes[next_name] = None  # type: ignore[assignment]
        clipboard.copy_to_next_scene(app)

    # ---- paste_in_place: _save_state exception (lines 199-200) ----
    def test_paste_in_place_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.clipboard = [_w(x=10, y=10)]
        _make_save_raise(app)
        clipboard.paste_in_place(app)
        assert len(app.state.current_scene().widgets) == 2

    # ---- paste_in_place: asdict exception (line 208) ----
    def test_paste_in_place_asdict_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.clipboard = [_w(x=10, y=10)]
        monkeypatch.setattr(clipboard, "asdict", MagicMock(side_effect=RuntimeError("bad")))
        clipboard.paste_in_place(app)
        assert len(app.state.current_scene().widgets) == 1

    # ---- broadcast_to_all_scenes: _save_state exception (lines 230-231) ----
    def test_broadcast_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        from ui_designer import SceneConfig

        app.designer.scenes["scene2"] = SceneConfig(
            name="scene2", width=256, height=128, widgets=[], bg_color="black"
        )
        app.state.selected = [0]
        _make_save_raise(app)
        clipboard.broadcast_to_all_scenes(app)

    # ---- broadcast: nothing selected (lines 255-256) ----
    def test_broadcast_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        clipboard.broadcast_to_all_scenes(app)

    # ---- broadcast: only 1 scene (line 305-306) — approximation ----
    def test_broadcast_single_scene(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        clipboard.broadcast_to_all_scenes(app)

    # ---- quick_clone: _save_state exception (lines 334-335) ----
    def test_quick_clone_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        app.state.selected = [0]
        _make_save_raise(app)
        clipboard.quick_clone(app)
        assert len(app.state.current_scene().widgets) == 2

    # ---- quick_clone: nothing selected ----
    def test_quick_clone_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        clipboard.quick_clone(app)

    # ---- quick_clone: OOB index ----
    def test_quick_clone_oob_index(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        clipboard.quick_clone(app)
        assert len(app.state.current_scene().widgets) == 1

    # ---- extract_to_new_scene: _save_state exception ----
    def test_extract_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        _make_save_raise(app)
        clipboard.extract_to_new_scene(app)
        assert len(app.designer.scenes) == 2

    # ---- extract: nothing selected ----
    def test_extract_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = []
        clipboard.extract_to_new_scene(app)
        assert len(app.designer.scenes) == 1

    # ---- extract: OOB → no valid widgets ----
    def test_extract_oob_no_valid(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        clipboard.extract_to_new_scene(app)
        assert len(app.designer.scenes) == 1

    # ---- duplicate_below: _save_state exception ----
    def test_duplicate_below_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        app.state.selected = [0]
        _make_save_raise(app)
        clipboard.duplicate_below(app)
        assert len(app.state.current_scene().widgets) == 2

    # ---- duplicate_below: nothing selected ----
    def test_duplicate_below_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        clipboard.duplicate_below(app)

    # ---- duplicate_below: OOB → no valid ----
    def test_duplicate_below_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        clipboard.duplicate_below(app)
        assert len(app.state.current_scene().widgets) == 1

    # ---- duplicate_right: _save_state exception ----
    def test_duplicate_right_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        app.state.selected = [0]
        _make_save_raise(app)
        clipboard.duplicate_right(app)
        assert len(app.state.current_scene().widgets) == 2

    # ---- duplicate_right: nothing selected ----
    def test_duplicate_right_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        clipboard.duplicate_right(app)

    # ---- duplicate_right: OOB → no valid ----
    def test_duplicate_right_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        clipboard.duplicate_right(app)
        assert len(app.state.current_scene().widgets) == 1

    # ---- export_selection_json: pygame.scrap exception ----
    def test_export_selection_json_scrap_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        monkeypatch.setattr(
            pygame,
            "scrap",
            MagicMock(
                init=MagicMock(side_effect=RuntimeError("no scrap")),
            ),
        )
        clipboard.export_selection_json(app)

    # ---- export_selection_json: nothing selected ----
    def test_export_selection_json_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        clipboard.export_selection_json(app)

    # ---- export_selection_json: OOB → no valid widgets ----
    def test_export_selection_json_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        clipboard.export_selection_json(app)


# ===========================================================================
# selection_ops/transforms.py
# ===========================================================================


class TestTransformsExceptions:
    """Cover except-branches in transforms.py."""

    # ---- move_selection: locked widget (line 20) ----
    def test_move_locked_widget(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.current_scene().widgets[0].locked = True
        app.state.selected = [0]
        transforms.move_selection(app, 8, 8)

    # ---- move_selection: _save_state exception (lines 41-42) ----
    def test_move_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        app.state.selected = [0]
        _make_save_raise(app)
        transforms.move_selection(app, 8, 0)
        assert app.state.current_scene().widgets[0].x == 18

    # ---- move_selection: OOB index (line 45) ----
    def test_move_oob_index(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        app.state.selected = [0, 999]
        transforms.move_selection(app, 8, 0)

    # ---- move_selection: no movement needed (line 45 → ddx==0 && ddy==0) ----
    def test_move_zero_delta(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=0, y=0)])
        app.state.selected = [0]
        # Already at origin, moving -8 would be clamped to 0 → ddx=0
        transforms.move_selection(app, -16, -16)

    # ---- resize_selection_to: locked widget (line 67) ----
    def test_resize_locked(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.current_scene().widgets[0].locked = True
        app.state.selected = [0]
        result = transforms.resize_selection_to(app, 100, 50)
        assert result is False

    # NOTE: resize_selection_to lines 84 (bounds.width<=0) and 89-90 (float
    # division exception) are dead-code guards — selection_bounds enforces
    # max(GRID,...) for width/height so these can never be reached.

    # ---- resize_selection_to: _save_state exception (lines 94-95) ----
    def test_resize_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10, width=40, height=20)])
        app.state.selected = [0]
        _make_save_raise(app)
        result = transforms.resize_selection_to(app, 80, 40)
        assert result is True

    # ---- resize_selection_to: OOB index (line 99) ----
    def test_resize_oob_index(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10, width=40, height=20)])
        app.state.selected = [0, 999]
        transforms.resize_selection_to(app, 80, 40)

    # ---- resize with snap enabled (line 148) ----
    def test_resize_with_snap(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(
            tmp_path, monkeypatch, widgets=[_w(x=8, y=8, width=40, height=24)], snap=True
        )
        app.state.selected = [0]
        result = transforms.resize_selection_to(app, 80, 48)
        assert result is True

    # ---- mirror_selection: _save_state exception (lines 151-152) ----
    def test_mirror_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        app.state.selected = [0]
        _make_save_raise(app)
        transforms.mirror_selection(app, "h")

    # ---- mirror_selection: OOB index (line 155) ----
    def test_mirror_oob_index(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        app.state.selected = [0, 999]
        transforms.mirror_selection(app, "v")

    # ---- mirror_selection: nothing selected (line 148) ----
    def test_mirror_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        transforms.mirror_selection(app, "h")

    # ---- swap_fg_bg: _save_state exception (lines 178-179) ----
    def test_swap_fg_bg_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        _make_save_raise(app)
        transforms.swap_fg_bg(app)

    # ---- swap_fg_bg: nothing selected (line 196→176) ----
    def test_swap_fg_bg_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        transforms.swap_fg_bg(app)

    # ---- make_full_width: locked (line 196) ----
    def test_make_full_width_locked(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.current_scene().widgets[0].locked = True
        app.state.selected = [0]
        transforms.make_full_width(app)

    # ---- make_full_width: _save_state exception (lines 202-203) ----
    def test_make_full_width_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        _make_save_raise(app)
        transforms.make_full_width(app)
        assert app.state.current_scene().widgets[0].width == 256

    # ---- make_full_width: nothing selected ----
    def test_make_full_width_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        transforms.make_full_width(app)

    # ---- make_full_width: OOB → no items ----
    def test_make_full_width_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        transforms.make_full_width(app)

    # ---- make_full_height: locked (line 220→226) ----
    def test_make_full_height_locked(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.current_scene().widgets[0].locked = True
        app.state.selected = [0]
        transforms.make_full_height(app)

    # ---- make_full_height: _save_state exception (lines 226-227) ----
    def test_make_full_height_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        _make_save_raise(app)
        transforms.make_full_height(app)
        assert app.state.current_scene().widgets[0].height == 128

    # ---- make_full_height: nothing selected ----
    def test_make_full_height_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        transforms.make_full_height(app)

    # ---- swap_dimensions: locked (line 244) ----
    def test_swap_dimensions_locked(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(width=60, height=20)])
        app.state.current_scene().widgets[0].locked = True
        app.state.selected = [0]
        transforms.swap_dimensions(app)

    # ---- swap_dimensions: _save_state exception (lines 250-251) ----
    def test_swap_dimensions_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(width=60, height=20)])
        app.state.selected = [0]
        _make_save_raise(app)
        transforms.swap_dimensions(app)
        w = app.state.current_scene().widgets[0]
        assert w.width == 20
        assert w.height == 60

    # ---- swap_dimensions: nothing selected ----
    def test_swap_dimensions_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        transforms.swap_dimensions(app)

    # ---- swap_dimensions: OOB → no items ----
    def test_swap_dimensions_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        transforms.swap_dimensions(app)

    # ---- move_selection_to_origin: _save_state exception (lines 266-267) ----
    def test_move_to_origin_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=40, y=30)])
        app.state.selected = [0]
        _make_save_raise(app)
        transforms.move_selection_to_origin(app)
        assert app.state.current_scene().widgets[0].x == 0
        assert app.state.current_scene().widgets[0].y == 0

    # ---- move_selection_to_origin: nothing selected (line 260→261) ----
    def test_move_to_origin_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        transforms.move_selection_to_origin(app)

    # ---- move_selection_to_origin: OOB → no valid (line 270) ----
    def test_move_to_origin_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        transforms.move_selection_to_origin(app)

    # ---- swap_positions: _save_state exception (lines 294-295) ----
    def test_swap_positions_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=20), _w(x=50, y=60)])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        transforms.swap_positions(app)
        assert app.state.current_scene().widgets[0].x == 50

    # ---- swap_positions: not exactly 2 (line 311→282) ----
    def test_swap_positions_not_two(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        transforms.swap_positions(app)

    # ---- swap_positions: OOB indices (lines 314-315→288) ----
    def test_swap_positions_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0, 999]
        transforms.swap_positions(app)

    # ---- flip_vertical: _save_state exception (lines 337-338→320-321) ----
    def test_flip_vertical_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        app.state.selected = [0]
        _make_save_raise(app)
        transforms.flip_vertical(app)

    # ---- flip_vertical: nothing selected ----
    def test_flip_vertical_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        transforms.flip_vertical(app)

    # ---- flip_vertical: OOB → no valid ----
    def test_flip_vertical_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        transforms.flip_vertical(app)

    # ---- swap_content: _save_state exception (lines 356→345) ----
    def test_swap_content_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(text="A"), _w(text="B")])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        transforms.swap_content(app)
        assert app.state.current_scene().widgets[0].text == "B"

    # ---- swap_content: not exactly 2 ----
    def test_swap_content_not_two(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        transforms.swap_content(app)

    # ---- swap_content: OOB ----
    def test_swap_content_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0, 999]
        transforms.swap_content(app)

    # ---- flip_horizontal: _save_state exception (lines 359-360) ----
    def test_flip_horizontal_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        app.state.selected = [0]
        _make_save_raise(app)
        transforms.flip_horizontal(app)

    # ---- flip_horizontal: nothing selected ----
    def test_flip_horizontal_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        transforms.flip_horizontal(app)

    # ---- flip_horizontal: OOB → no valid ----
    def test_flip_horizontal_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        transforms.flip_horizontal(app)

    # ---- mirror_scene_horizontal: no widgets ----
    def test_mirror_scene_horizontal_empty(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch)
        transforms.mirror_scene_horizontal(app)

    # ---- mirror_scene_horizontal: normal ----
    def test_mirror_scene_horizontal_normal(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10, width=30)])
        transforms.mirror_scene_horizontal(app)

    # ---- mirror_scene_vertical: no widgets ----
    def test_mirror_scene_vertical_empty(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch)
        transforms.mirror_scene_vertical(app)

    # ---- mirror_scene_vertical: normal ----
    def test_mirror_scene_vertical_normal(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10, height=20)])
        transforms.mirror_scene_vertical(app)

    # ---- move_selection with snap enabled ----
    def test_move_with_snap(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import transforms

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=8, y=8)], snap=True)
        app.state.selected = [0]
        transforms.move_selection(app, 10, 10)


# ===========================================================================
# selection_ops/propagation.py
# ===========================================================================


class TestPropagationExceptions:
    """Cover except-branches in propagation.py."""

    # ---- paste_style: _save_state exception (lines 34-35) ----
    def test_paste_style_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app._style_clipboard = {"style": "cyber", "color_fg": "green"}
        app.state.selected = [0]
        _make_save_raise(app)
        propagation.paste_style(app)

    # ---- paste_style: nothing in clipboard (line 53→26) ----
    def test_paste_style_no_clipboard(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app._style_clipboard = None
        propagation.paste_style(app)

    # ---- paste_style: nothing selected (line 53) ----
    def test_paste_style_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app._style_clipboard = {"style": "cyber"}
        app.state.selected = []
        propagation.paste_style(app)

    # ---- copy_style: nothing selected (line 60-61→8) ----
    def test_copy_style_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app.state.selected_idx = None
        propagation.copy_style(app)

    # ---- propagate_border: _save_state exception (lines 69→63-64) ----
    def test_propagate_border_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        propagation.propagate_border(app)

    # ---- propagate_border: fewer than 2 selected (line 83→48) ----
    def test_propagate_border_single(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        propagation.propagate_border(app)

    # ---- propagate_border: first idx OOB (line 87-88) ----
    def test_propagate_border_first_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999, 0]
        propagation.propagate_border(app)

    # ---- propagate_style: _save_state exception (lines 106→97) ----
    def test_propagate_style_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        propagation.propagate_style(app)

    # ---- propagate_style: fewer than 2 (lines 110-111→85) ----
    def test_propagate_style_single(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        propagation.propagate_style(app)

    # ---- propagate_style: first idx OOB (line 129→91) ----
    def test_propagate_style_first_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999, 0]
        propagation.propagate_style(app)

    # ---- clone_text: _save_state exception (lines 135-136→115) ----
    def test_clone_text_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(text="src"), _w(text="dst")])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        propagation.clone_text(app)
        assert app.state.current_scene().widgets[1].text == "src"

    # ---- clone_text: fewer than 2 (line 155→103) ----
    def test_clone_text_single(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        propagation.clone_text(app)

    # ---- clone_text: first idx OOB (lines 161-162→109) ----
    def test_clone_text_first_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999, 0]
        propagation.clone_text(app)

    # ---- propagate_align: _save_state exception (lines 181→139) ----
    def test_propagate_align_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        propagation.propagate_align(app)

    # ---- propagate_align: fewer than 2 (lines 188-189→126) ----
    def test_propagate_align_single(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        propagation.propagate_align(app)

    # ---- propagate_align: first idx OOB (line 209→132) ----
    def test_propagate_align_first_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999, 0]
        propagation.propagate_align(app)

    # ---- propagate_colors: _save_state exception (lines 215-216→160) ----
    def test_propagate_colors_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        propagation.propagate_colors(app)

    # ---- propagate_colors: fewer than 2 (line 235→148) ----
    def test_propagate_colors_single(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        propagation.propagate_colors(app)

    # ---- propagate_colors: first idx OOB (lines 241-242→154) ----
    def test_propagate_colors_first_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999, 0]
        propagation.propagate_colors(app)

    # ---- propagate_value: _save_state exception (lines 265→184) ----
    def test_propagate_value_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        propagation.propagate_value(app)

    # ---- propagate_value: fewer than 2 (lines 283-284→174) ----
    def test_propagate_value_single(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        propagation.propagate_value(app)

    # ---- propagate_value: first idx OOB (line 304→180) ----
    def test_propagate_value_first_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999, 0]
        propagation.propagate_value(app)

    # ---- propagate_border: border_width not None (line 69) ----
    def test_propagate_border_with_border_width(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.current_scene().widgets[0].border_width = 2
        app.state.selected = [0, 1]
        propagation.propagate_border(app)
        assert app.state.current_scene().widgets[1].border_width == 2

    # ---- propagate_padding: first idx OOB (line 209) ----
    def test_propagate_padding_first_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999, 0]
        propagation.propagate_padding(app)

    # ---- propagate_padding: _save_state exception (lines 215-216) ----
    def test_propagate_padding_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        propagation.propagate_padding(app)

    # ---- propagate_padding: fewer than 2 ----
    def test_propagate_padding_single(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        propagation.propagate_padding(app)

    # ---- propagate_margin: first idx OOB (line 235) ----
    def test_propagate_margin_first_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999, 0]
        propagation.propagate_margin(app)

    # ---- propagate_margin: _save_state exception (lines 241-242) ----
    def test_propagate_margin_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        propagation.propagate_margin(app)

    # ---- propagate_margin: fewer than 2 ----
    def test_propagate_margin_single(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        propagation.propagate_margin(app)

    # ---- propagate_appearance: first idx OOB (line 265) ----
    def test_propagate_appearance_first_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999, 0]
        propagation.propagate_appearance(app)

    # ---- propagate_appearance: _save_state exception (lines 283-284) ----
    def test_propagate_appearance_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        propagation.propagate_appearance(app)

    # ---- propagate_appearance: fewer than 2 ----
    def test_propagate_appearance_single(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        propagation.propagate_appearance(app)

    # ---- propagate_text: first idx OOB (line 304) ----
    def test_propagate_text_first_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999, 0]
        propagation.propagate_text(app)

    # ---- propagate_text: fewer than 2 ----
    def test_propagate_text_single(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        propagation.propagate_text(app)

    # ---- propagate_text: normal (covers _save_undo_state path) ----
    def test_propagate_text_normal(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import propagation

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(text="src"), _w(text="dst")])
        app.state.selected = [0, 1]
        propagation.propagate_text(app)
        assert app.state.current_scene().widgets[1].text == "src"


# ===========================================================================
# Additional clipboard.py tests for remaining uncovered lines
# ===========================================================================


class TestClipboardExtraEdges:
    # ---- copy_to_next_scene: current not in names (lines 136-137) ----
    def test_copy_to_next_scene_current_not_in_names(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        from ui_designer import SceneConfig

        app.designer.scenes["scene2"] = SceneConfig(
            name="scene2", width=256, height=128, widgets=[], bg_color="black"
        )
        app.state.selected = [0]
        current = app.designer.current_scene

        # Replace scenes with a dict subclass whose keys() omits the current name
        class TrickyDict(dict):
            def keys(self):
                return [k for k in super().keys() if k != current] + ["_phantom_"]  # noqa: SIM118

            def get(self, key, default=None):
                if key == "_phantom_":
                    return super().get(current, default)
                return super().get(key, default)

        trick = TrickyDict(app.designer.scenes)
        app.designer.scenes = trick
        clipboard.copy_to_next_scene(app)

    # ---- broadcast_to_all_scenes: target scene is None (line 208) ----
    def test_broadcast_target_scene_none(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import clipboard

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        from ui_designer import SceneConfig

        # Add 2 extra scenes, make one None
        app.designer.scenes["scene2"] = None  # type: ignore[assignment]
        app.designer.scenes["scene3"] = SceneConfig(
            name="scene3", width=256, height=128, widgets=[], bg_color="black"
        )
        app.state.selected = [0]
        clipboard.broadcast_to_all_scenes(app)


# ===========================================================================
# selection_ops/layout.py — exception branches and edge cases
# ===========================================================================


# Functions that require 2+ widgets selected
_LAYOUT_2PLUS = [
    "arrange_in_row",
    "arrange_in_column",
    "stack_vertical",
    "stack_horizontal",
    "equalize_widths",
    "equalize_heights",
    "space_evenly_h",
    "space_evenly_v",
    "grid_arrange",
]


class TestLayoutSelectOpsEdges:
    """Cover except/return branches in selection_ops/layout.py."""

    @pytest.mark.parametrize("func_name", _LAYOUT_2PLUS)
    def test_layout_2plus_single_selected(self, tmp_path, monkeypatch, func_name):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        getattr(layout_mod, func_name)(app)

    @pytest.mark.parametrize("func_name", _LAYOUT_2PLUS)
    def test_layout_2plus_save_state_exception(self, tmp_path, monkeypatch, func_name):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=0, y=0), _w(x=40, y=0)])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        getattr(layout_mod, func_name)(app)

    @pytest.mark.parametrize("func_name", _LAYOUT_2PLUS)
    def test_layout_2plus_oob_indices(self, tmp_path, monkeypatch, func_name):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999, 998]
        getattr(layout_mod, func_name)(app)

    def test_compact_widgets_empty(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch)
        layout_mod.compact_widgets(app)

    def test_compact_widgets_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10)])
        _make_save_raise(app)
        layout_mod.compact_widgets(app)

    def test_equalize_gaps_auto(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(
            tmp_path, monkeypatch, widgets=[_w(x=0, y=0, width=20), _w(x=40, y=0, width=20)]
        )
        app.state.selected = [0, 1]
        layout_mod.equalize_gaps(app, axis="auto")

    def test_equalize_gaps_single(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        layout_mod.equalize_gaps(app)

    def test_equalize_gaps_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [998, 999]
        layout_mod.equalize_gaps(app)

    def test_equalize_gaps_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=0, y=0), _w(x=40, y=0)])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        layout_mod.equalize_gaps(app)

    def test_auto_flow_layout_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        _make_save_raise(app)
        layout_mod.auto_flow_layout(app)

    def test_auto_flow_layout_empty(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch)
        layout_mod.auto_flow_layout(app)

    def test_shrink_to_content_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(text="test")])
        app.state.selected = [0]
        _make_save_raise(app)
        layout_mod.shrink_to_content(app)

    def test_shrink_to_content_empty(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        layout_mod.shrink_to_content(app)

    def test_shrink_to_content_continue_branch(self, tmp_path, monkeypatch):
        """Widget with no text and no icon -> skip (continue branch)."""
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(text="")])
        app.state.current_scene().widgets[0].icon_char = ""
        app.state.selected = [0]
        layout_mod.shrink_to_content(app)

    def test_distribute_columns_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        layout_mod.distribute_columns(app, col_count=2)

    def test_distribute_columns_empty(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        layout_mod.distribute_columns(app)

    def test_distribute_columns_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        layout_mod.distribute_columns(app)

    def test_distribute_rows_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0, 1]
        _make_save_raise(app)
        layout_mod.distribute_rows(app, row_count=2)

    def test_distribute_rows_empty(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        layout_mod.distribute_rows(app)

    def test_distribute_rows_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        layout_mod.distribute_rows(app)

    def test_cascade_arrange_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        _make_save_raise(app)
        layout_mod.cascade_arrange(app)

    def test_distribute_columns_3(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import layout as layout_mod

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w(), _w()])
        app.state.selected = [0, 1, 2]
        layout_mod.distribute_columns_3(app)


# ===========================================================================
# selection_ops/batch_ops.py — exception branches and edge cases
# ===========================================================================

# batch_ops functions that take only (app), need selected widgets, and have
# _save_state except branches
_BATCH_SAVE_STATE = [
    "reset_to_defaults",
    "auto_rename",
    "clear_margins",
    "hide_unselected",
    "fit_scene_to_content",
    "show_all_widgets",
    "unlock_all_widgets",
    "toggle_all_borders",
    "remove_degenerate_widgets",
    "enable_all_widgets",
    "sort_widgets_by_position",
    "snap_sizes_to_grid",
    "clear_padding",
    "flatten_z_indices",
    "reverse_widget_order",
    "normalize_sizes",
    "auto_name_scene",
    "remove_duplicates",
    "increment_text",
]

# Functions that check nothing selected → return
_BATCH_EMPTY_RETURN = [
    "reorder_selection",
    "reset_to_defaults",
    "array_duplicate",
    "auto_rename",
    "clear_margins",
    "hide_unselected",
    "increment_text",
    "measure_selection",
]


class TestBatchOpsEdges:
    """Cover except/return branches in selection_ops/batch_ops.py."""

    @pytest.mark.parametrize("func_name", _BATCH_SAVE_STATE)
    def test_batch_save_state_exception(self, tmp_path, monkeypatch, func_name):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10, text="hello")])
        app.state.selected = [0]
        _make_save_raise(app)
        getattr(batch_ops, func_name)(app)

    def test_reorder_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        batch_ops.reorder_selection(app, -1)

    def test_reorder_single_widget(self, tmp_path, monkeypatch):
        """n < 2 → return."""
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        batch_ops.reorder_selection(app, -1)

    def test_reorder_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [1]
        _make_save_raise(app)
        batch_ops.reorder_selection(app, -1)

    def test_reorder_boundary_first_up(self, tmp_path, monkeypatch):
        """First widget can't go up → return."""
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [0]
        batch_ops.reorder_selection(app, -1)

    def test_reorder_boundary_last_down(self, tmp_path, monkeypatch):
        """Last widget can't go down → return."""
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        app.state.selected = [1]
        batch_ops.reorder_selection(app, 1)

    def test_reset_to_defaults_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        batch_ops.reset_to_defaults(app)

    def test_widget_info_nothing(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        app.state.selected_idx = None
        batch_ops.widget_info(app)

    def test_array_duplicate_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        batch_ops.array_duplicate(app, 2, 8, 8)

    def test_array_duplicate_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        _make_save_raise(app)
        batch_ops.array_duplicate(app, 2, 8, 8)

    def test_array_duplicate_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        batch_ops.array_duplicate(app, 2, 8, 8)

    def test_array_duplicate_asdict_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        monkeypatch.setattr(batch_ops, "asdict", MagicMock(side_effect=RuntimeError("bad")))
        batch_ops.array_duplicate(app, 2, 8, 8)

    def test_auto_rename_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        batch_ops.auto_rename(app)

    def test_scene_stats_with_disabled(self, tmp_path, monkeypatch):
        """Cover disabled widget counter (line 204) and disabled flag (line 212)."""
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.current_scene().widgets[0].enabled = False
        batch_ops.scene_stats(app)

    def test_clear_margins_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        batch_ops.clear_margins(app)

    def test_remove_degenerate_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(width=0, height=0)])
        _make_save_raise(app)
        batch_ops.remove_degenerate_widgets(app)

    def test_remove_degenerate_nothing_removed(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(width=60, height=20)])
        batch_ops.remove_degenerate_widgets(app)

    def test_enable_all_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        _make_save_raise(app)
        batch_ops.enable_all_widgets(app)

    def test_enable_all_already_enabled(self, tmp_path, monkeypatch):
        """All widgets already enabled → 0 changed."""
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        batch_ops.enable_all_widgets(app)

    def test_sort_widgets_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        _make_save_raise(app)
        batch_ops.sort_widgets_by_position(app)

    def test_sort_widgets_empty(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch)
        batch_ops.sort_widgets_by_position(app)

    def test_snap_sizes_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        _make_save_raise(app)
        batch_ops.snap_sizes_to_grid(app)

    def test_snap_sizes_empty(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch)
        batch_ops.snap_sizes_to_grid(app)

    def test_snap_sizes_no_change(self, tmp_path, monkeypatch):
        """Widget already grid-aligned → 0 changed."""
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=8, y=8, width=24, height=16)])
        batch_ops.snap_sizes_to_grid(app)

    def test_clear_padding_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        batch_ops.clear_padding(app)

    def test_flatten_z_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        _make_save_raise(app)
        batch_ops.flatten_z_indices(app)

    def test_flatten_z_empty(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch)
        batch_ops.flatten_z_indices(app)


# ---------------------------------------------------------------------------
# property_cycles.py — _save_state except & OOB default branches
# ---------------------------------------------------------------------------

# Functions that follow the _save_state except + OOB first_idx pattern:
#   cycle_style, cycle_widget_type, cycle_border_style, cycle_text_overflow,
#   cycle_align, cycle_valign
_CYCLE_SAVE_OOB = [
    ("cycle_style", "style"),
    ("cycle_widget_type", "type"),
    ("cycle_border_style", "border_style"),
    ("cycle_text_overflow", "text_overflow"),
    ("cycle_align", "align"),
    ("cycle_valign", "valign"),
]

# Functions with _save_state except but NO OOB first_idx default:
#   toggle_visibility, toggle_border, cycle_color_preset,
#   adjust_value, toggle_enabled, toggle_checked,
#   cycle_gray_fg, cycle_gray_bg, outline_mode
_SAVE_ONLY = [
    "toggle_visibility",
    "toggle_border",
    "cycle_color_preset",
    "adjust_value",
    "toggle_enabled",
    "cycle_gray_fg",
    "cycle_gray_bg",
    "outline_mode",
]

# Functions using _save_undo_state with OOB continue:
#   set_inverse_style, set_bold_style, set_default_style, outline_only
_UNDO_OOB = [
    "set_inverse_style",
    "set_bold_style",
    "set_default_style",
    "outline_only",
]


class TestPropertyCyclesEdges:
    """Cover _save_state except and OOB first_idx branches in property_cycles."""

    # ---- parametrized _save_state except + OOB default for cycle_* funcs ----
    @pytest.mark.parametrize(("func_name", "attr"), _CYCLE_SAVE_OOB)
    def test_save_except(self, func_name, attr, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import property_cycles as pc

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        _make_save_raise(app)
        getattr(pc, func_name)(app)

    @pytest.mark.parametrize(("func_name", "attr"), _CYCLE_SAVE_OOB)
    def test_oob_default(self, func_name, attr, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import property_cycles as pc

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        getattr(pc, func_name)(app)

    # ---- parametrized _save_state except for toggle/non-cycle funcs ----
    @pytest.mark.parametrize("func_name", _SAVE_ONLY)
    def test_save_only_except(self, func_name, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import property_cycles as pc

        # adjust_value needs delta arg
        if func_name == "adjust_value":
            app = _make_app(
                tmp_path,
                monkeypatch,
                widgets=[_w(type="gauge", value=50, min_value=0, max_value=100)],
            )
            app.state.selected = [0]
            _make_save_raise(app)
            pc.adjust_value(app, 5)
        else:
            widgets = [_w(type="checkbox")] if func_name == "toggle_checked" else [_w()]
            app = _make_app(tmp_path, monkeypatch, widgets=widgets)
            app.state.selected = [0]
            _make_save_raise(app)
            getattr(pc, func_name)(app)

    # ---- _save_undo_state + OOB continue ----
    @pytest.mark.parametrize("func_name", _UNDO_OOB)
    def test_undo_oob_continue(self, func_name, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import property_cycles as pc

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        getattr(pc, func_name)(app)

    # ---- smart_edit OOB return ----
    def test_smart_edit_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import property_cycles as pc

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        pc.smart_edit(app)

    # ---- smart_edit checkbox toggle + _save_state except ----
    def test_smart_edit_checkbox_save_except(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import property_cycles as pc

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(type="checkbox", checked=False)])
        app.state.selected = [0]
        _make_save_raise(app)
        pc.smart_edit(app)

    # ---- adjust_value OOB continue ----
    def test_adjust_value_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import property_cycles as pc

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        _make_save_raise(app)
        pc.adjust_value(app, 1)

    # ---- toggle_enabled OOB return ----
    def test_toggle_enabled_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import property_cycles as pc

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        pc.toggle_enabled(app)

    # ---- toggle_checked: OOB items = empty → return, save_except ----
    def test_toggle_checked_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import property_cycles as pc

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(type="checkbox")])
        app.state.selected = [999]
        pc.toggle_checked(app)

    def test_toggle_checked_save_except(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import property_cycles as pc

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(type="checkbox", checked=False)])
        app.state.selected = [0]
        _make_save_raise(app)
        pc.toggle_checked(app)

    # ---- cycle_gray_fg / cycle_gray_bg OOB return ----
    def test_cycle_gray_fg_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import property_cycles as pc

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        pc.cycle_gray_fg(app)

    def test_cycle_gray_bg_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import property_cycles as pc

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        pc.cycle_gray_bg(app)

    # ---- outline_mode OOB valid=[] → return ----
    def test_outline_mode_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import property_cycles as pc

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        pc.outline_mode(app)

    # ---- cycle_color_preset OOB first_idx ----
    def test_cycle_color_preset_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import property_cycles as pc

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        pc.cycle_color_preset(app)

    def test_reverse_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(), _w()])
        _make_save_raise(app)
        batch_ops.reverse_widget_order(app)

    def test_reverse_empty(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch)
        batch_ops.reverse_widget_order(app)

    def test_reverse_single(self, tmp_path, monkeypatch):
        """Single widget → return early."""
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        batch_ops.reverse_widget_order(app)

    def test_normalize_sizes_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        _make_save_raise(app)
        batch_ops.normalize_sizes(app)

    def test_auto_name_scene_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        _make_save_raise(app)
        batch_ops.auto_name_scene(app)

    def test_remove_duplicates_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=0, y=0), _w(x=0, y=0)])
        _make_save_raise(app)
        batch_ops.remove_duplicates(app)

    def test_remove_duplicates_empty(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch)
        batch_ops.remove_duplicates(app)

    def test_increment_text_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(text="Item 1")])
        app.state.selected = [0]
        _make_save_raise(app)
        batch_ops.increment_text(app)

    def test_increment_text_nothing_selected(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        batch_ops.increment_text(app)

    def test_measure_selection_nothing(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        batch_ops.measure_selection(app)

    def test_replace_text_save_state_exception(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(text="hello")])
        _make_save_raise(app)
        batch_ops.replace_text_in_scene(app)

    def test_zoom_to_selection_save_state(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        batch_ops.zoom_to_selection(app)

    def test_zoom_to_selection_nothing(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import batch_ops

        app = _make_app(tmp_path, monkeypatch)
        app.state.selected = []
        batch_ops.zoom_to_selection(app)


# ---------------------------------------------------------------------------
# query_select.py — OOB returns, empty-scene, edge branches
# ---------------------------------------------------------------------------

# Functions with OOB first_idx → return pattern
_QS_OOB = [
    "select_same_z",
    "select_same_style",
    "select_same_type",
    "select_same_color",
    "select_parent_panel",
    "select_children",
    "select_same_size",
    "select_same_type_as_current",
]


class TestQuerySelectEdges:
    """Cover OOB returns and edge branches in query_select."""

    @pytest.mark.parametrize("func_name", _QS_OOB)
    def test_oob_return(self, func_name, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import query_select as qs

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        getattr(qs, func_name)(app)

    # select_overlapping OOB valid=[] → return
    def test_overlapping_oob(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import query_select as qs

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [999]
        qs.select_overlapping(app)

    # select_locked: all unlocked → "No locked widgets found."
    def test_locked_no_locked(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import query_select as qs

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(locked=False)])
        app.state.selected = []
        qs.select_locked(app)

    # select_overflow: empty scene
    def test_overflow_empty_scene(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import query_select as qs

        app = _make_app(tmp_path, monkeypatch)
        qs.select_overflow(app)

    # select_overflow: icon type branch
    def test_overflow_icon_branch(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import query_select as qs

        app = _make_app(
            tmp_path, monkeypatch, widgets=[_w(type="icon", icon_char="X", width=10, height=10)]
        )
        qs.select_overflow(app)

    # select_overflow: no overflow found (large widget, small text)
    def test_overflow_no_overflow(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import query_select as qs

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(text="Hi", width=200, height=100)])
        qs.select_overflow(app)

    # select_overflow: import exception for text_metrics
    def test_overflow_import_fail(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import query_select as qs

        _make_app(tmp_path, monkeypatch, widgets=[_w()])
        # Make the relative import of text_metrics fail
        import cyberpunk_designer.text_metrics as tm

        monkeypatch.setattr(
            tm, "text_truncates_in_widget", MagicMock(side_effect=ImportError("no module"))
        )
        # The import itself won't fail (already cached), but we can make the
        # function inside the loop raise. Actually the except is around import.
        # We need to make the `from .. import text_metrics` fail.
        import sys

        saved = sys.modules.get("cyberpunk_designer.text_metrics")
        monkeypatch.delitem(sys.modules, "cyberpunk_designer.text_metrics", raising=False)
        monkeypatch.setitem(sys.modules, "cyberpunk_designer.text_metrics", None)
        # Force re-import by removing cached module reference
        if hasattr(qs, "_text_metrics_cache"):
            monkeypatch.delattr(qs, "_text_metrics_cache", raising=False)
        # Reload the module so the `from .. import text_metrics` re-executes
        import importlib

        try:
            importlib.reload(qs)
        except Exception:
            pass
        # Restore and re-import
        if saved is not None:
            monkeypatch.setitem(sys.modules, "cyberpunk_designer.text_metrics", saved)
        importlib.reload(qs)

    # select_parent_panel: no panel widgets → continue branch
    def test_parent_panel_no_panels(self, tmp_path, monkeypatch):
        from cyberpunk_designer.selection_ops import query_select as qs

        # Scene has only labels, no panels → all iterations hit "continue"
        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=10, y=10), _w(x=20, y=20)])
        app.state.selected = [0]
        qs.select_parent_panel(app)
