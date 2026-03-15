"""Tests for CyberpunkEditorApp methods — batch 2.

Covers: _apply_template, _apply_first_template, _new_scene,
_build_widget_presets_actions, _coalesce_motion_and_wheel, _dedupe_keydowns,
_smart_dirty_tracking, _auto_adjust_quality.
"""

from __future__ import annotations

from collections import deque
from types import SimpleNamespace

import pygame

from cyberpunk_editor import CyberpunkEditorApp
from ui_designer import WidgetConfig
from ui_template_manager import Template, TemplateMetadata

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add(app, **kw):
    defaults = dict(type="label", x=0, y=0, width=80, height=16, text="W")
    defaults.update(kw)
    w = WidgetConfig(**defaults)
    sc = app.state.current_scene()
    sc.widgets.append(w)
    return w


def _sel(app, *indices):
    app.state.selected = list(indices)
    app.state.selected_idx = indices[0] if indices else None


def _make_template(widget_dicts, name="TestTpl"):
    """Build a Template with the given widget dicts."""
    meta = TemplateMetadata(name=name, category="Test", description="")
    scene = SimpleNamespace(_raw_data={"widgets": widget_dicts})
    return Template(metadata=meta, scene=scene)


# ===================================================================
# _apply_template
# ===================================================================


class TestApplyTemplate:
    def test_replaces_widgets(self, make_app):
        app = make_app()
        _add(app, text="old")
        tpl = _make_template(
            [
                {"type": "button", "x": 0, "y": 0, "width": 40, "height": 16, "text": "new"},
            ]
        )
        app._apply_template(tpl)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 1
        assert sc.widgets[0].text == "new"

    def test_sets_selection(self, make_app):
        app = make_app()
        tpl = _make_template(
            [
                {"type": "label", "x": 0, "y": 0, "width": 40, "height": 16, "text": "a"},
            ]
        )
        app._apply_template(tpl)
        assert app.state.selected_idx == 0
        assert app.state.selected == [0]

    def test_empty_template(self, make_app):
        app = make_app()
        _add(app, text="old")
        tpl = _make_template([])
        app._apply_template(tpl)
        sc = app.state.current_scene()
        assert len(sc.widgets) == 0
        assert app.state.selected_idx is None
        assert app.state.selected == []

    def test_skips_invalid_widget_dicts(self, make_app):
        app = make_app()
        tpl = _make_template(
            [
                {"type": "label", "x": 0, "y": 0, "width": 40, "height": 16, "text": "ok"},
                {"invalid": True},  # should be skipped
            ]
        )
        app._apply_template(tpl)
        # Only valid widget survives
        assert len(app.state.current_scene().widgets) == 1


# ===================================================================
# _apply_first_template
# ===================================================================


class TestApplyFirstTemplate:
    def test_applies_first(self, make_app):
        app = make_app()
        tpl = _make_template(
            [
                {"type": "label", "x": 0, "y": 0, "width": 40, "height": 16, "text": "first"},
            ]
        )
        app.template_library.templates = [tpl]
        app._apply_first_template()
        assert app.state.current_scene().widgets[0].text == "first"

    def test_noop_when_no_templates(self, make_app):
        app = make_app()
        _add(app, text="keep")
        app.template_library.templates = []
        app._apply_first_template()
        assert app.state.current_scene().widgets[0].text == "keep"


# ===================================================================
# _new_scene
# ===================================================================


class TestNewScene:
    def test_resets_to_empty(self, make_app):
        app = make_app()
        _add(app, text="old")
        app._new_scene()
        sc = app.state.current_scene()
        assert len(sc.widgets) == 0

    def test_new_designer(self, make_app):
        app = make_app()
        old_designer = app.designer
        app._new_scene()
        assert app.designer is not old_designer

    def test_dirty_set(self, make_app):
        app = make_app()
        app._dirty = False
        app._new_scene()
        assert app._dirty is True


# ===================================================================
# _build_widget_presets_actions
# ===================================================================


class TestBuildWidgetPresetsActions:
    def test_returns_header_and_slots(self, make_app):
        app = make_app()
        actions = app._build_widget_presets_actions()
        # Header + 3 slots × 3 actions each = 10
        assert len(actions) == 10
        assert actions[0][0] == "-- Widget Presets --"
        assert actions[0][1] is None

    def test_slot_labels(self, make_app):
        app = make_app()
        actions = app._build_widget_presets_actions()
        labels = [a[0] for a in actions]
        assert "Save preset slot 1" in labels
        assert "Apply preset slot 1" in labels
        assert "Add preset slot 1" in labels
        assert "Save preset slot 3" in labels

    def test_slot_callbacks_callable(self, make_app):
        app = make_app()
        actions = app._build_widget_presets_actions()
        for _label, cb in actions:
            if cb is not None:
                assert callable(cb)


# ===================================================================
# _coalesce_motion_and_wheel (static method)
# ===================================================================


class TestCoalesceMotionAndWheel:
    def test_keeps_only_last_motion(self):
        m1 = SimpleNamespace(type=pygame.MOUSEMOTION, pos=(10, 10))
        m2 = SimpleNamespace(type=pygame.MOUSEMOTION, pos=(20, 20))
        other = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a)
        result = CyberpunkEditorApp._coalesce_motion_and_wheel([m1, other, m2])
        motions = [e for e in result if getattr(e, "type", None) == pygame.MOUSEMOTION]
        assert len(motions) == 1
        assert motions[0].pos == (20, 20)

    def test_keeps_only_last_wheel(self):
        w1 = SimpleNamespace(type=pygame.MOUSEWHEEL, y=1)
        w2 = SimpleNamespace(type=pygame.MOUSEWHEEL, y=-1)
        result = CyberpunkEditorApp._coalesce_motion_and_wheel([w1, w2])
        wheels = [e for e in result if getattr(e, "type", None) == pygame.MOUSEWHEEL]
        assert len(wheels) == 1
        assert wheels[0].y == -1

    def test_preserves_other_events(self):
        k = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a)
        q = SimpleNamespace(type=pygame.QUIT)
        result = CyberpunkEditorApp._coalesce_motion_and_wheel([k, q])
        assert len(result) == 2

    def test_empty_list(self):
        assert CyberpunkEditorApp._coalesce_motion_and_wheel([]) == []


# ===================================================================
# _dedupe_keydowns (static method)
# ===================================================================


class TestDedupeKeydowns:
    def test_removes_duplicate_keys(self):
        k1 = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a, repeat=False)
        k2 = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a, repeat=False)
        result = CyberpunkEditorApp._dedupe_keydowns([k1, k2])
        keydowns = [e for e in result if getattr(e, "type", None) == pygame.KEYDOWN]
        assert len(keydowns) == 1

    def test_keeps_different_keys(self):
        k1 = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a, repeat=False)
        k2 = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_b, repeat=False)
        result = CyberpunkEditorApp._dedupe_keydowns([k1, k2])
        assert len(result) == 2

    def test_drops_repeat_flag(self):
        k1 = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a, repeat=True)
        result = CyberpunkEditorApp._dedupe_keydowns([k1])
        assert len(result) == 0

    def test_keeps_keyup(self):
        kd = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a, repeat=False)
        ku = SimpleNamespace(type=pygame.KEYUP, key=pygame.K_a)
        result = CyberpunkEditorApp._dedupe_keydowns([kd, ku])
        assert len(result) == 2

    def test_empty(self):
        assert CyberpunkEditorApp._dedupe_keydowns([]) == []


# ===================================================================
# _smart_dirty_tracking
# ===================================================================


class TestSmartDirtyTracking:
    def test_force_full_redraw(self, make_app):
        app = make_app()
        app._force_full_redraw = True
        app._smart_dirty_tracking()
        assert len(app.dirty_rects) == 1

    def test_help_overlay_forces_full(self, make_app):
        app = make_app()
        app.show_help_overlay = True
        app._smart_dirty_tracking()
        assert len(app.dirty_rects) == 1

    def test_dragging_directs_canvas(self, make_app):
        app = make_app()
        app._force_full_redraw = False
        app.show_help_overlay = False
        app.state.dragging = True
        app._smart_dirty_tracking()
        assert any(r == app.layout.canvas_rect for r in app.dirty_rects)

    def test_inspector_field_active(self, make_app):
        app = make_app()
        app._force_full_redraw = False
        app.show_help_overlay = False
        app.state.dragging = False
        app.state.resizing = False
        app.state.inspector_selected_field = "text"
        app._smart_dirty_tracking()
        assert any(r == app.layout.inspector_rect for r in app.dirty_rects)

    def test_nothing_specific_full_redraw(self, make_app):
        app = make_app()
        app._force_full_redraw = False
        app.show_help_overlay = False
        app.state.dragging = False
        app.state.resizing = False
        app.state.inspector_selected_field = None
        app._smart_dirty_tracking()
        assert len(app.dirty_rects) == 1  # full redraw fallback


# ===================================================================
# _auto_adjust_quality
# ===================================================================


class TestAutoAdjustQuality:
    def test_noop_when_disabled(self, make_app):
        app = make_app()
        app.auto_optimize = False
        app.fps_history = deque([60] * 60, maxlen=60)
        app.show_grid = True
        app._auto_adjust_quality()
        assert app.show_grid is True  # unchanged

    def test_noop_when_insufficient_history(self, make_app):
        app = make_app()
        app.auto_optimize = True
        app.fps_history = deque([10] * 10, maxlen=60)
        app.show_grid = True
        app._auto_adjust_quality()
        assert app.show_grid is True  # unchanged

    def test_low_fps_disables_grid(self, make_app):
        app = make_app()
        app.auto_optimize = True
        app.min_acceptable_fps = 30
        app.fps_history = deque([15] * 60, maxlen=60)
        app.show_grid = True
        app._auto_adjust_quality()
        assert app.show_grid is False

    def test_high_fps_enables_grid(self, make_app):
        app = make_app()
        app.auto_optimize = True
        app.min_acceptable_fps = 30
        app.fps_history = deque([120] * 60, maxlen=60)
        app.show_grid = False
        app._auto_adjust_quality()
        assert app.show_grid is True
