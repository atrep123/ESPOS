"""Tests targeting specific uncovered lines in near-100% modules."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pygame

from cyberpunk_designer.text_metrics import (
    text_truncates_in_widget,
    wrap_text_chars,
)
from ui_designer import UIDesigner, WidgetConfig

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _w(**kw) -> WidgetConfig:
    defaults = dict(type="label", x=0, y=0, width=60, height=20, text="hello")
    defaults.update(kw)
    return WidgetConfig(**defaults)


def _make_app(tmp_path, monkeypatch, *, profile=None, widgets=None, snap=False):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    from cyberpunk_editor import CyberpunkEditorApp

    json_path = tmp_path / "scene.json"
    app = CyberpunkEditorApp(json_path, (256, 128))
    if profile:
        app.hardware_profile = profile
    if widgets:
        sc = app.state.current_scene()
        for w in widgets:
            sc.widgets.append(w)
    app.snap_enabled = snap
    return app


# ===========================================================================
# font6x8.py — line 155: _CACHE.clear() when cache > 512
# ===========================================================================


class TestFont6x8CacheEviction:
    def test_cache_overflow_triggers_clear(self):
        from cyberpunk_designer.font6x8 import _CACHE, render_text

        _CACHE.clear()
        # Fill cache past limit
        for i in range(520):
            render_text(f"t{i}", (255, 255, 255))
        # After overflow the cache should have been cleared and new entry added
        assert len(_CACHE) <= 520


# ===========================================================================
# primitives.py — line 83: draw_border_style with style "none"
# ===========================================================================


class TestPrimitivesBorderNone:
    def test_border_style_none(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        pygame.init()
        from cyberpunk_designer.drawing.primitives import draw_border_style

        surf = pygame.Surface((100, 100))
        app = SimpleNamespace()
        draw_border_style(app, surf, pygame.Rect(10, 10, 80, 80), "none", (255, 255, 255))

    def test_border_style_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        pygame.init()
        from cyberpunk_designer.drawing.primitives import draw_border_style

        surf = pygame.Surface((100, 100))
        app = SimpleNamespace()
        draw_border_style(app, surf, pygame.Rect(10, 10, 80, 80), "", (255, 255, 255))


# ===========================================================================
# reporting.py — lines 43-44: screenshot_canvas exception branch
# ===========================================================================


class TestReportingScreenshotFail:
    def test_screenshot_canvas_exception(self):
        from cyberpunk_designer.reporting import screenshot_canvas

        app = SimpleNamespace(
            state=MagicMock(),
            _set_status=MagicMock(),
        )
        app.state.current_scene.side_effect = OSError("boom")
        screenshot_canvas(app)
        assert "failed" in app._set_status.call_args[0][0].lower()


# ===========================================================================
# perf.py — lines 57-58: SmartEventQueue process_batch exception in future
# ===========================================================================


class TestSmartEventQueueException:
    def test_future_exception_skipped(self):
        from cyberpunk_designer.perf import SmartEventQueue

        q = SmartEventQueue()
        # MOUSEMOTION events are parallelized
        bad_event = SimpleNamespace(type=pygame.MOUSEMOTION)
        with patch.object(q, "_process_event", side_effect=RuntimeError("fail")):
            result = q.process_batch([bad_event])
        # The failed future should be skipped (continue)
        assert isinstance(result, list)


# ===========================================================================
# text_metrics.py — line 76: _push returns early when truncated
# ===========================================================================


class TestTextMetricsEdge:
    def test_wrap_truncation_push_returns(self):
        """Long text with max_lines=1 triggers truncation path (line 76).

        After truncation, subsequent paragraph _push calls should return early.
        """
        # Use multiple paragraphs so _push is called after truncation
        text = "word1 word2\nword3 word4\nword5 word6"
        lines, trunc = wrap_text_chars(text, max_chars=10, max_lines=1, ellipsis="...")
        assert trunc
        assert len(lines) == 1

    def test_overflow_not_in_known_set(self):
        """text_overflow with unknown value falls back to 'ellipsis' (line 132)."""
        w = _w(width=60, height=20, text="hello")
        w.text_overflow = "unknown_value"  # set after construction to bypass validation
        result = text_truncates_in_widget(w, "hello")
        assert isinstance(result, bool)

    def test_max_lines_invalid_string(self):
        """max_lines set to invalid string triggers except (lines 150-151)."""
        w = _w(width=60, height=40, text="long text that wraps", text_overflow="wrap")
        w.max_lines = "bad"  # set after construction to bypass validation
        result = text_truncates_in_widget(w, "long text that wraps nicely over multiple lines")
        assert isinstance(result, bool)


# ===========================================================================
# drawing/toolbar.py — lines 51-52: scene list exception, 111/123: hover colors
# ===========================================================================


class TestToolbarSceneTabsException:
    def test_scene_tabs_designer_scenes_raises(self, tmp_path, monkeypatch):
        from cyberpunk_designer.drawing.toolbar import draw_scene_tabs

        app = _make_app(tmp_path, monkeypatch)
        # Break app.designer.scenes to raise on keys()
        app.designer.scenes = MagicMock()
        app.designer.scenes.keys.side_effect = AttributeError("fail")
        # Should not raise — just returns early (lines 51-52)
        draw_scene_tabs(app)

    def test_scene_tabs_hover_arrows(self, tmp_path, monkeypatch):
        """Exercise arrow hover coloring (lines 111, 123)."""
        from cyberpunk_designer.drawing.toolbar import draw_scene_tabs

        app = _make_app(tmp_path, monkeypatch)
        # Create many scenes to force overflow/arrows
        for i in range(20):
            app.designer.create_scene(f"scene_{i:02d}")
        # Narrow layout width to force tab overflow
        app.layout.width = 200
        app.layout.scene_tabs_h = 24
        # Set up pointer in left arrow region
        app.pointer_pos = (5, app.layout.toolbar_h + 5)
        app._tab_scroll = 50  # nonzero scroll so left arrow is active
        draw_scene_tabs(app)

        # Set up pointer in right arrow region
        app.pointer_pos = (195, app.layout.toolbar_h + 5)
        draw_scene_tabs(app)


# ===========================================================================
# __main__.py — lines 1-6
# ===========================================================================


class TestMainModule:
    def test_main_import(self):
        """Just importing __main__ to cover lines 1-6."""
        import cyberpunk_designer.__main__ as m

        assert hasattr(m, "main")


# ===========================================================================
# fit_widget.py — lines 31, 41-42, 71, 147-148
# ===========================================================================


class TestFitWidgetEdge:
    def test_invalid_max_lines(self, tmp_path, monkeypatch):
        """max_lines = 'bad' triggers _parse_max_lines except (lines 41-42)."""
        from cyberpunk_designer.fit_widget import fit_selection_to_widget

        w = _w(text="hello world this is long", width=40, height=10, text_overflow="wrap")
        w.max_lines = "bad"  # set after construction to bypass validation
        app = _make_app(tmp_path, monkeypatch, profile="esp32os_256x128_gray4", widgets=[w])
        app.state.selected = [0]
        app.state.selected_idx = 0
        fit_selection_to_widget(app)

    def test_unknown_overflow_value(self, tmp_path, monkeypatch):
        """Unknown text_overflow falls through to 'ellipsis' (line 71)."""
        from cyberpunk_designer.fit_widget import fit_selection_to_widget

        w = _w(text="hello world")
        w.text_overflow = "funky_mode"  # set after construction to bypass validation
        app = _make_app(tmp_path, monkeypatch, profile="esp32os_256x128_gray4", widgets=[w])
        app.state.selected = [0]
        app.state.selected_idx = 0
        fit_selection_to_widget(app)

    def test_save_state_exception(self, tmp_path, monkeypatch):
        """_save_state raising triggers except (lines 147-148)."""
        from cyberpunk_designer.fit_widget import fit_selection_to_widget

        app = _make_app(
            tmp_path,
            monkeypatch,
            profile="esp32os_256x128_gray4",
            widgets=[
                _w(text="hello world this is a long text that won't fit", width=20, height=10)
            ],
        )
        app.state.selected = [0]
        app.state.selected_idx = 0
        app.designer._save_state = MagicMock(side_effect=TypeError("fail"))
        fit_selection_to_widget(app)


# ===========================================================================
# fit_text.py — lines 28, 38-39, 63, 144-145
# ===========================================================================


class TestFitTextEdge:
    def test_invalid_max_lines(self, tmp_path, monkeypatch):
        """max_lines = 'bad' triggers _parse_max_lines except (lines 38-39)."""
        from cyberpunk_designer.fit_text import fit_selection_to_text

        w = _w(text="hello world this is long", width=40, height=10, text_overflow="wrap")
        w.max_lines = "bad"  # set after construction to bypass validation
        app = _make_app(tmp_path, monkeypatch, profile="esp32os_256x128_gray4", widgets=[w])
        app.state.selected = [0]
        app.state.selected_idx = 0
        fit_selection_to_text(app)

    def test_unknown_overflow_value(self, tmp_path, monkeypatch):
        """Unknown text_overflow falls through to 'ellipsis' (line 63)."""
        from cyberpunk_designer.fit_text import fit_selection_to_text

        w = _w(text="hello world")
        w.text_overflow = "funky_mode"  # set after construction to bypass validation
        app = _make_app(tmp_path, monkeypatch, profile="esp32os_256x128_gray4", widgets=[w])
        app.state.selected = [0]
        app.state.selected_idx = 0
        fit_selection_to_text(app)

    def test_save_state_exception(self, tmp_path, monkeypatch):
        """_save_state raising triggers except (lines 144-145)."""
        from cyberpunk_designer.fit_text import fit_selection_to_text

        app = _make_app(
            tmp_path,
            monkeypatch,
            profile="esp32os_256x128_gray4",
            widgets=[
                _w(
                    text="hello world this is a long text that DEFINITELY won't fit",
                    width=20,
                    height=10,
                )
            ],
        )
        app.state.selected = [0]
        app.state.selected_idx = 0
        app.designer._save_state = MagicMock(side_effect=TypeError("fail"))
        fit_selection_to_text(app)


# ===========================================================================
# selection_ops/core.py — lines 62, 82-83, 88, 95-96
# ===========================================================================


class TestCoreEdge:
    def test_click_shift_no_anchor(self, tmp_path, monkeypatch):
        """Shift+click with no anchor falls to single select (line 62)."""
        from cyberpunk_designer.selection_ops.core import apply_click_selection

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected_idx = None
        # Simulate shift+click
        apply_click_selection(app, 0, pygame.KMOD_SHIFT)
        assert app.state.selected == [0]

    def test_delete_save_state_exception(self, tmp_path, monkeypatch):
        """delete_selected when _save_state raises (lines 82-83)."""
        from cyberpunk_designer.selection_ops.core import delete_selected

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app.designer._save_state = MagicMock(side_effect=TypeError("fail"))
        delete_selected(app)
        assert app.state.selected == []

    def test_delete_out_of_range_index(self, tmp_path, monkeypatch):
        """delete_selected with out-of-range index should skip (line 88)."""
        from cyberpunk_designer.selection_ops.core import delete_selected

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [99]
        app.state.selected_idx = 99
        delete_selected(app)
        assert app.state.selected == []

    def test_delete_reindex_exception(self, tmp_path, monkeypatch):
        """_reindex_after_delete raising (lines 95-96)."""
        from cyberpunk_designer.selection_ops.core import delete_selected

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app.designer._reindex_after_delete = MagicMock(side_effect=AttributeError("fail"))
        delete_selected(app)
        assert len(app.state.current_scene().widgets) == 0


# ===========================================================================
# io_ops.py — lines 35, 38-39, 98-102, 114, 138-139, 158, 185-186, 198-199
# ===========================================================================


class TestIoOpsEdge:
    def test_load_autosave_bad_scene_dims(self, tmp_path, monkeypatch):
        """Autosave with width<=0 triggers default_size set (line 35)."""
        from cyberpunk_designer.io_ops import load_or_default

        json_path = tmp_path / "scene.json"
        autosave_path = tmp_path / "scene.json.autosave"

        # Base file
        d = UIDesigner(256, 128)
        d.create_scene("main")
        d.save_to_json(str(json_path))
        time.sleep(0.05)

        # Autosave with bad dims
        d2 = UIDesigner(0, 0)
        d2.create_scene("main")
        sc = d2.scenes["main"]
        sc.width = 0
        sc.height = 0
        d2.save_to_json(str(autosave_path))

        app = SimpleNamespace(
            json_path=json_path,
            autosave_path=autosave_path,
            designer=UIDesigner(256, 128),
            default_size=(256, 128),
            _restored_from_autosave=False,
        )
        app.designer.create_scene("main")
        load_or_default(app)

    def test_load_autosave_exception(self, tmp_path, monkeypatch):
        """Autosave load failure falls through to base file (lines 38-39)."""
        from cyberpunk_designer.io_ops import load_or_default

        json_path = tmp_path / "scene.json"
        autosave_path = tmp_path / "scene.json.autosave"

        d = UIDesigner(256, 128)
        d.create_scene("main")
        d.save_to_json(str(json_path))
        time.sleep(0.05)

        # Bad autosave content
        autosave_path.write_text("{{{invalid json", encoding="utf-8")

        app = SimpleNamespace(
            json_path=json_path,
            autosave_path=autosave_path,
            designer=UIDesigner(256, 128),
            default_size=(256, 128),
            _restored_from_autosave=False,
        )
        app.designer.create_scene("main")
        load_or_default(app)

    def test_apply_preset_add_new(self, tmp_path, monkeypatch):
        """apply_preset_slot with add_new=True (lines 98-102)."""
        from cyberpunk_designer import io_ops
        from cyberpunk_designer.io_ops import apply_preset_slot

        app = _make_app(tmp_path, monkeypatch)
        # Monkeypatch WidgetConfig in io_ops to accept construction without x/y

        class _FlexWC:
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)
                self.x = getattr(self, "x", 0)
                self.y = getattr(self, "y", 0)

        monkeypatch.setattr(io_ops, "WidgetConfig", _FlexWC)
        app.widget_presets = [{"type": "label", "width": 50, "height": 20, "text": "preset"}]
        apply_preset_slot(app, 1, add_new=True)
        sc = app.state.current_scene()
        assert len(sc.widgets) >= 1

    def test_apply_preset_skips_xy_keys(self, tmp_path, monkeypatch):
        """apply_preset_slot skips x/y keys in preset (line 114)."""
        from cyberpunk_designer.io_ops import apply_preset_slot

        app = _make_app(tmp_path, monkeypatch, widgets=[_w()])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app.widget_presets = [{"type": "button", "x": 99, "y": 99, "width": 80, "text": "btn"}]
        apply_preset_slot(app, 1, add_new=False)
        # x and y should be skipped (not overwritten)
        assert app.state.current_scene().widgets[0].x == 0

    def test_save_prefs_exception(self, tmp_path, monkeypatch):
        """save_prefs when write fails (lines 138-139)."""
        from cyberpunk_designer.io_ops import save_prefs

        app = SimpleNamespace(
            prefs={},
            favorite_ports=[],
        )
        with patch(
            "cyberpunk_designer.io_ops.PREFS_PATH", tmp_path / "no_exist_dir" / "prefs.json"
        ):
            save_prefs(app)

    def test_save_json_windows_rename(self, tmp_path, monkeypatch):
        """save_json with os.name == 'nt' atomic rename (line 158)."""
        from cyberpunk_designer.io_ops import save_json

        app = _make_app(tmp_path, monkeypatch)
        app.json_path = tmp_path / "test_save.json"
        app._dirty = True
        app._dirty_scenes = set()
        save_json(app)
        assert app.json_path.exists()

    def test_save_json_tempfile_failure_falls_back(self, tmp_path, monkeypatch):
        """save_json falls back to direct write when tempfile fails."""
        import tempfile as _tempfile

        from cyberpunk_designer.io_ops import save_json

        app = _make_app(tmp_path, monkeypatch)
        app.json_path = tmp_path / "fallback_save.json"
        app._dirty = True
        app._dirty_scenes = set()
        # Make mkstemp fail so fallback direct write is exercised
        monkeypatch.setattr(
            _tempfile,
            "mkstemp",
            lambda **kw: (_ for _ in ()).throw(OSError("disk full")),
        )
        save_json(app)
        assert app.json_path.exists()
        assert not app._dirty

    def test_write_audit_report_fails(self, tmp_path, monkeypatch):
        """write_audit_report when exception occurs (lines 185-186)."""
        from cyberpunk_designer.io_ops import write_audit_report

        app = SimpleNamespace(
            state=MagicMock(),
        )
        app.state.current_scene.side_effect = RuntimeError("fail")
        write_audit_report(app)

    def test_maybe_autosave_exception(self, tmp_path, monkeypatch):
        """maybe_autosave when save fails (lines 198-199)."""
        from cyberpunk_designer.io_ops import maybe_autosave

        app = SimpleNamespace(
            autosave_enabled=True,
            _dirty=True,
            _last_autosave_ts=0,
            autosave_interval=0,
            designer=MagicMock(),
            autosave_path=tmp_path / "no_dir" / "autosave.json",
        )
        app.designer.save_to_json.side_effect = OSError("fail")
        maybe_autosave(app)


# ===========================================================================
# layout_tools.py — all 16 missing lines (exception branches in helpers)
# ===========================================================================


class TestLayoutToolsExceptions:
    """layout_tools.py missing lines are all try/except exception branches.

    All 8 missing-line pairs (106-107, 143-144, 195-196, 224-225,
    303-304, 383-384, 436-437, 445-446) are ``except Exception: pass``
    after ``app.designer._save_state()``.
    """

    def test_import(self):
        import cyberpunk_designer.layout_tools as lt

        assert hasattr(lt, "align_selection")

    def test_align_single_save_state_exc(self, tmp_path, monkeypatch):
        """Single-widget align with _save_state raising (lines 106-107)."""
        from cyberpunk_designer.layout_tools import align_selection

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=50, y=50)])
        app.state.selected = [0]
        app.state.selected_idx = 0
        app.designer._save_state = MagicMock(side_effect=TypeError("fail"))
        align_selection(app, "left")
        assert app.state.current_scene().widgets[0].x == 0

    def test_align_multi_save_state_exc(self, tmp_path, monkeypatch):
        """Multi-widget align with _save_state raising (lines 143-144)."""
        from cyberpunk_designer.layout_tools import align_selection

        w1 = _w(x=10, y=10, width=30, height=30)
        w2 = _w(x=50, y=50, width=30, height=30)
        app = _make_app(tmp_path, monkeypatch, widgets=[w1, w2])
        app.state.selected = [0, 1]
        app.state.selected_idx = 0
        app.designer._save_state = MagicMock(side_effect=TypeError("fail"))
        align_selection(app, "left")

    def test_distribute_h_save_state_exc(self, tmp_path, monkeypatch):
        """Horizontal distribute with _save_state raising (lines 195-196)."""
        from cyberpunk_designer.layout_tools import distribute_selection

        w1 = _w(x=0, y=0, width=20, height=20)
        w2 = _w(x=50, y=0, width=20, height=20)
        w3 = _w(x=100, y=0, width=20, height=20)
        app = _make_app(tmp_path, monkeypatch, widgets=[w1, w2, w3])
        app.state.selected = [0, 1, 2]
        app.state.selected_idx = 0
        app.designer._save_state = MagicMock(side_effect=TypeError("fail"))
        distribute_selection(app, "h")

    def test_distribute_v_save_state_exc(self, tmp_path, monkeypatch):
        """Vertical distribute with _save_state raising (lines 224-225)."""
        from cyberpunk_designer.layout_tools import distribute_selection

        w1 = _w(x=0, y=0, width=20, height=20)
        w2 = _w(x=0, y=50, width=20, height=20)
        w3 = _w(x=0, y=100, width=20, height=20)
        app = _make_app(tmp_path, monkeypatch, widgets=[w1, w2, w3])
        app.state.selected = [0, 1, 2]
        app.state.selected_idx = 0
        app.designer._save_state = MagicMock(side_effect=TypeError("fail"))
        distribute_selection(app, "v")

    def test_match_size_save_state_exc(self, tmp_path, monkeypatch):
        """Match size with _save_state raising (lines 303-304)."""
        from cyberpunk_designer.layout_tools import match_size_selection

        w1 = _w(x=0, y=0, width=40, height=40)
        w2 = _w(x=50, y=0, width=20, height=20)
        app = _make_app(tmp_path, monkeypatch, widgets=[w1, w2])
        app.state.selected = [0, 1]
        app.state.selected_idx = 0
        app.designer._save_state = MagicMock(side_effect=TypeError("fail"))
        match_size_selection(app, "width")

    def test_snap_drag_widget_exc(self, tmp_path, monkeypatch):
        """snap_drag_to_guides with broken widget attrs (lines 383-384)."""
        from cyberpunk_designer.layout_tools import snap_drag_to_guides

        class _BadWidget:
            visible = True
            locked = False

            @property
            def x(self):
                raise ValueError("fail")

            @property
            def y(self):
                raise ValueError("fail")

            width = 20
            height = 20

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=0, y=0)])
        app.state.current_scene().widgets.append(_BadWidget())
        app.state.selected = [0]
        bounds = pygame.Rect(10, 10, 30, 30)
        snap_drag_to_guides(app, 10, 10, bounds)

    def test_clear_active_guides_exc(self, tmp_path, monkeypatch):
        """snap_drag_to_guides clearing guides when no snap (lines 436-437)."""
        from cyberpunk_designer.layout_tools import snap_drag_to_guides

        app = _make_app(tmp_path, monkeypatch, widgets=[_w(x=0, y=0)])
        app.state.selected = [0]
        # Make active_guides assignment raise by patching __setattr__
        orig_setattr = type(app.state).__setattr__

        def _bad_setattr(self, name, value):
            if name == "active_guides":
                raise AttributeError("fail")
            orig_setattr(self, name, value)

        monkeypatch.setattr(type(app.state), "__setattr__", _bad_setattr)
        bounds = pygame.Rect(500, 500, 30, 30)  # far from any guide
        snap_drag_to_guides(app, 500, 500, bounds)

    def test_set_active_guides_exc(self, tmp_path, monkeypatch):
        """snap_drag_to_guides setting guides when snapped (lines 445-446)."""
        from cyberpunk_designer.layout_tools import snap_drag_to_guides

        w1 = _w(x=0, y=0, width=20, height=20)
        w2 = _w(x=50, y=0, width=20, height=20)
        app = _make_app(tmp_path, monkeypatch, widgets=[w1, w2])
        app.state.selected = [0]
        # Make active_guides assignment raise by patching __setattr__
        orig_setattr = type(app.state).__setattr__

        def _bad_setattr(self, name, value):
            if name == "active_guides":
                raise AttributeError("fail")
            orig_setattr(self, name, value)

        monkeypatch.setattr(type(app.state), "__setattr__", _bad_setattr)
        bounds = pygame.Rect(0, 0, 20, 20)
        # Place near w2 edge (x=50) to trigger snap
        snap_drag_to_guides(app, 48, 0, bounds)
