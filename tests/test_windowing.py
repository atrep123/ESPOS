"""Tests for cyberpunk_designer/windowing.py pure functions."""

from types import SimpleNamespace

from cyberpunk_designer.windowing import (
    _base_layout_size,
    _fit_scale,
    recompute_scale_for_window,
    screen_to_logical,
    set_scale,
)


def _mock_app(scale_x=1.0, scale_y=1.0, offset_x=0, offset_y=0, max_auto_scale=4):
    """Create a minimal mock app object for windowing functions."""
    return SimpleNamespace(
        _render_scale_x=scale_x,
        _render_scale_y=scale_y,
        _render_offset_x=offset_x,
        _render_offset_y=offset_y,
        max_auto_scale=max_auto_scale,
    )


class TestScreenToLogical:
    def test_identity(self):
        app = _mock_app(scale_x=1.0, scale_y=1.0, offset_x=0, offset_y=0)
        assert screen_to_logical(app, 100, 200) == (100, 200)

    def test_double_scale(self):
        app = _mock_app(scale_x=2.0, scale_y=2.0, offset_x=0, offset_y=0)
        assert screen_to_logical(app, 200, 100) == (100, 50)

    def test_with_offset(self):
        app = _mock_app(scale_x=1.0, scale_y=1.0, offset_x=10, offset_y=20)
        assert screen_to_logical(app, 110, 120) == (100, 100)

    def test_scale_and_offset(self):
        app = _mock_app(scale_x=2.0, scale_y=2.0, offset_x=10, offset_y=10)
        lx, ly = screen_to_logical(app, 110, 110)
        assert lx == 50
        assert ly == 50

    def test_zero_scale_clamped(self):
        """Zero scale uses fallback of 1.0."""
        app = _mock_app(scale_x=0, scale_y=0)
        lx, ly = screen_to_logical(app, 50, 50)
        assert lx == 50
        assert ly == 50

    def test_negative_scale_treated_as_fallback(self):
        app = _mock_app(scale_x=-1, scale_y=-1)
        # Negative scale < 0, so fallback to 1.0
        lx, ly = screen_to_logical(app, 50, 50)
        assert lx == 50
        assert ly == 50


class TestFitScale:
    def test_exact_fit(self):
        app = _mock_app(max_auto_scale=4)
        assert _fit_scale(app, 800, 600, 800, 600) == 1

    def test_double_fit(self):
        app = _mock_app(max_auto_scale=4)
        assert _fit_scale(app, 1600, 1200, 800, 600) == 2

    def test_limited_by_max(self):
        app = _mock_app(max_auto_scale=2)
        assert _fit_scale(app, 3200, 2400, 800, 600) == 2

    def test_min_is_1(self):
        app = _mock_app(max_auto_scale=4)
        assert _fit_scale(app, 100, 100, 800, 600) == 1

    def test_asymmetric_uses_smaller(self):
        app = _mock_app(max_auto_scale=10)
        # Width fits 4x, height fits 2x → should be 2
        assert _fit_scale(app, 3200, 1200, 800, 600) == 2

    def test_zero_dimensions_safe(self):
        app = _mock_app(max_auto_scale=4)
        # Should handle 0 gracefully (clamped to 1)
        result = _fit_scale(app, 0, 0, 0, 0)
        assert result >= 1


def _layout_app(canvas_w=256, canvas_h=128, toolbar_h=20, scene_tabs_h=16, status_h=12):
    designer = SimpleNamespace(width=canvas_w, height=canvas_h)
    return SimpleNamespace(
        designer=designer,
        toolbar_h=toolbar_h,
        scene_tabs_h=scene_tabs_h,
        status_h=status_h,
    )


class TestBaseLayoutSize:
    def test_basic(self):
        app = _layout_app(canvas_w=256, canvas_h=128, toolbar_h=20,
                          scene_tabs_h=16, status_h=12)
        w, h = _base_layout_size(app, palette_w=60, inspector_w=120)
        assert w == 256 + 60 + 120
        assert h == 128 + 20 + 16 + 12

    def test_zero_canvas(self):
        app = _layout_app(canvas_w=0, canvas_h=0, toolbar_h=0,
                          scene_tabs_h=0, status_h=0)
        w, h = _base_layout_size(app, palette_w=0, inspector_w=0)
        assert w >= 1
        assert h >= 1

    def test_only_palette(self):
        app = _layout_app(canvas_w=100, canvas_h=50, toolbar_h=0,
                          scene_tabs_h=0, status_h=0)
        w, h = _base_layout_size(app, palette_w=40, inspector_w=0)
        assert w == 140
        assert h == 50

    def test_large_inspector(self):
        app = _layout_app(canvas_w=128, canvas_h=64, toolbar_h=10,
                          scene_tabs_h=10, status_h=10)
        w, h = _base_layout_size(app, palette_w=50, inspector_w=200)
        assert w == 378
        assert h == 94


def _recompute_app(canvas_w=256, canvas_h=128, toolbar_h=20,
                   scene_tabs_h=16, status_h=12,
                   max_auto_scale=4, panels_collapsed=False,
                   palette_w=60, inspector_w=120):
    designer = SimpleNamespace(width=canvas_w, height=canvas_h)
    return SimpleNamespace(
        designer=designer,
        toolbar_h=toolbar_h,
        scene_tabs_h=scene_tabs_h,
        status_h=status_h,
        max_auto_scale=max_auto_scale,
        panels_collapsed=panels_collapsed,
        _default_palette_w=palette_w,
        _default_inspector_w=inspector_w,
        scale=1,
    )


class TestRecomputeScaleForWindow:
    def test_exact_1x(self):
        app = _recompute_app(canvas_w=256, canvas_h=128, toolbar_h=20,
                             scene_tabs_h=16, status_h=12,
                             palette_w=60, inspector_w=120)
        # base_w = 256+60+120 = 436, base_h = 128+20+16+12 = 176
        recompute_scale_for_window(app, 436, 176)
        assert app.scale == 1

    def test_double_window(self):
        app = _recompute_app(canvas_w=256, canvas_h=128, toolbar_h=20,
                             scene_tabs_h=16, status_h=12,
                             palette_w=60, inspector_w=120)
        recompute_scale_for_window(app, 872, 352)
        assert app.scale == 2

    def test_capped_by_max(self):
        app = _recompute_app(max_auto_scale=2)
        recompute_scale_for_window(app, 5000, 5000)
        assert app.scale == 2

    def test_small_window(self):
        app = _recompute_app()
        recompute_scale_for_window(app, 100, 50)
        assert app.scale == 1

    def test_panels_collapsed(self):
        app = _recompute_app(panels_collapsed=True, palette_w=60, inspector_w=120)
        # collapsed → palette_w=0, inspector_w=0
        # base_w = 256+0+0 = 256, base_h = 176
        recompute_scale_for_window(app, 512, 352)
        assert app.scale == 2


class TestSetScale:
    def test_clamp_to_max(self):
        app = _recompute_app(max_auto_scale=3)
        app.window = None
        app._mark_dirty = lambda: setattr(app, "_dirty", True)
        app._dirty = False
        set_scale(app, 5)
        assert app.scale == 3
        assert app._dirty

    def test_clamp_to_min(self):
        app = _recompute_app(max_auto_scale=4)
        app.window = None
        app._mark_dirty = lambda: setattr(app, "_dirty", True)
        app._dirty = False
        set_scale(app, 0)
        assert app.scale == 1
        assert app._dirty

    def test_normal_set(self):
        app = _recompute_app(max_auto_scale=4)
        app.window = None
        app._mark_dirty = lambda: setattr(app, "_dirty", True)
        app._dirty = False
        set_scale(app, 2)
        assert app.scale == 2
