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
        app = _layout_app(canvas_w=256, canvas_h=128, toolbar_h=20, scene_tabs_h=16, status_h=12)
        w, h = _base_layout_size(app, palette_w=60, inspector_w=120)
        assert w == 256 + 60 + 120
        assert h == 128 + 20 + 16 + 12

    def test_zero_canvas(self):
        app = _layout_app(canvas_w=0, canvas_h=0, toolbar_h=0, scene_tabs_h=0, status_h=0)
        w, h = _base_layout_size(app, palette_w=0, inspector_w=0)
        assert w >= 1
        assert h >= 1

    def test_only_palette(self):
        app = _layout_app(canvas_w=100, canvas_h=50, toolbar_h=0, scene_tabs_h=0, status_h=0)
        w, h = _base_layout_size(app, palette_w=40, inspector_w=0)
        assert w == 140
        assert h == 50

    def test_large_inspector(self):
        app = _layout_app(canvas_w=128, canvas_h=64, toolbar_h=10, scene_tabs_h=10, status_h=10)
        w, h = _base_layout_size(app, palette_w=50, inspector_w=200)
        assert w == 378
        assert h == 94


def _recompute_app(
    canvas_w=256,
    canvas_h=128,
    toolbar_h=20,
    scene_tabs_h=16,
    status_h=12,
    max_auto_scale=4,
    panels_collapsed=False,
    palette_w=60,
    inspector_w=120,
):
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
        app = _recompute_app(
            canvas_w=256,
            canvas_h=128,
            toolbar_h=20,
            scene_tabs_h=16,
            status_h=12,
            palette_w=60,
            inspector_w=120,
        )
        # base_w = 256+60+120 = 436, base_h = 128+20+16+12 = 176
        recompute_scale_for_window(app, 436, 176)
        assert app.scale == 1

    def test_double_window(self):
        app = _recompute_app(
            canvas_w=256,
            canvas_h=128,
            toolbar_h=20,
            scene_tabs_h=16,
            status_h=12,
            palette_w=60,
            inspector_w=120,
        )
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


# ---------------------------------------------------------------------------
# AU: Windowing extreme case tests
# ---------------------------------------------------------------------------


class TestScreenToLogicalExtreme:
    def test_fractional_scale(self):
        """Non-integer scale factors work correctly."""
        app = _mock_app(scale_x=1.5, scale_y=1.5, offset_x=0, offset_y=0)
        lx, ly = screen_to_logical(app, 150, 150)
        assert lx == 100
        assert ly == 100

    def test_very_large_scale(self):
        """Very large scale (100x) still produces correct results."""
        app = _mock_app(scale_x=100.0, scale_y=100.0, offset_x=0, offset_y=0)
        lx, ly = screen_to_logical(app, 10000, 5000)
        assert lx == 100
        assert ly == 50

    def test_very_small_scale(self):
        """Very small scale (0.1x) still produces correct results."""
        app = _mock_app(scale_x=0.1, scale_y=0.1, offset_x=0, offset_y=0)
        lx, ly = screen_to_logical(app, 10, 10)
        assert lx == 100
        assert ly == 100

    def test_negative_offset(self):
        """Negative offsets work correctly."""
        app = _mock_app(scale_x=1.0, scale_y=1.0, offset_x=-50, offset_y=-50)
        lx, ly = screen_to_logical(app, 0, 0)
        assert lx == 50
        assert ly == 50

    def test_large_coordinates(self):
        """Large screen coordinates survive without overflow."""
        app = _mock_app(scale_x=1.0, scale_y=1.0, offset_x=0, offset_y=0)
        lx, ly = screen_to_logical(app, 100000, 100000)
        assert lx == 100000
        assert ly == 100000


class TestFitScaleExtreme:
    def test_huge_window(self):
        """Very large window should be capped by max_auto_scale."""
        app = _mock_app(max_auto_scale=4)
        assert _fit_scale(app, 10000, 10000, 100, 100) == 4

    def test_tiny_window(self):
        """Window smaller than base always returns 1."""
        app = _mock_app(max_auto_scale=4)
        assert _fit_scale(app, 10, 10, 800, 600) == 1

    def test_one_pixel_base(self):
        """Base of 1x1 pixel allows max scale."""
        app = _mock_app(max_auto_scale=10)
        assert _fit_scale(app, 10, 10, 1, 1) == 10

    def test_max_scale_1(self):
        """max_auto_scale=1 always returns 1."""
        app = _mock_app(max_auto_scale=1)
        assert _fit_scale(app, 5000, 5000, 100, 100) == 1


class TestBaseLayoutSizeExtreme:
    def test_negative_canvas_treated_as_zero(self):
        """Negative canvas dimensions are clamped via max(1,...)."""
        app = _layout_app(canvas_w=-10, canvas_h=-5, toolbar_h=0, scene_tabs_h=0, status_h=0)
        w, h = _base_layout_size(app, palette_w=0, inspector_w=0)
        assert w >= 1
        assert h >= 1

    def test_very_large_layout(self):
        """Large dimensions don't cause integer overflow."""
        app = _layout_app(canvas_w=4000, canvas_h=2000, toolbar_h=50, scene_tabs_h=30, status_h=20)
        w, h = _base_layout_size(app, palette_w=200, inspector_w=400)
        assert w == 4600
        assert h == 2100


class TestRecomputeScaleExtreme:
    def test_zero_window(self):
        """Zero window size results in scale=1."""
        app = _recompute_app()
        recompute_scale_for_window(app, 0, 0)
        assert app.scale == 1

    def test_negative_window(self):
        """Negative window size results in scale=1."""
        app = _recompute_app()
        recompute_scale_for_window(app, -100, -100)
        assert app.scale == 1

    def test_scale_10x(self):
        """Window 10x base size with max_auto_scale=10 → scale=10."""
        app = _recompute_app(
            canvas_w=100,
            canvas_h=50,
            toolbar_h=0,
            scene_tabs_h=0,
            status_h=0,
            max_auto_scale=10,
            palette_w=0,
            inspector_w=0,
        )
        recompute_scale_for_window(app, 1000, 500)
        assert app.scale == 10


class TestSetScaleExtreme:
    def test_negative_clamped_to_1(self):
        app = _recompute_app(max_auto_scale=4)
        app.window = None
        app._mark_dirty = lambda: setattr(app, "_dirty", True)
        set_scale(app, -5)
        assert app.scale == 1

    def test_very_large_clamped(self):
        app = _recompute_app(max_auto_scale=4)
        app.window = None
        app._mark_dirty = lambda: setattr(app, "_dirty", True)
        set_scale(app, 999)
        assert app.scale == 4

    def test_set_1(self):
        app = _recompute_app(max_auto_scale=4)
        app.window = None
        app._mark_dirty = lambda: setattr(app, "_dirty", True)
        set_scale(app, 1)
        assert app.scale == 1


# ===================================================================
# BG – windowing edge cases
# ===================================================================


class TestScreenToLogicalFractional:
    def test_fractional_scale(self):
        """Non-integer scale produces valid integer coordinates."""
        app = _mock_app(scale_x=1.5, scale_y=1.5, offset_x=0, offset_y=0)
        result = screen_to_logical(app, 150, 150)
        assert result == (100, 100)

    def test_large_offset(self):
        """Large offsets produce negative logical coordinates."""
        app = _mock_app(scale_x=1.0, scale_y=1.0, offset_x=1000, offset_y=1000)
        result = screen_to_logical(app, 0, 0)
        assert result == (-1000, -1000)

    def test_both_scale_and_offset(self):
        app = _mock_app(scale_x=2.0, scale_y=3.0, offset_x=10, offset_y=20)
        lx, ly = screen_to_logical(app, 110, 320)
        assert lx == int((110 - 10) / 2.0)
        assert ly == int((320 - 20) / 3.0)


class TestFitScaleBoundary:
    def test_exact_multiple(self):
        """Window is exactly N times base size."""
        app = _mock_app(max_auto_scale=10)
        assert _fit_scale(app, 300, 300, 100, 100) == 3

    def test_just_below_next_scale(self):
        """Window is just below 3x size → returns 2."""
        app = _mock_app(max_auto_scale=10)
        assert _fit_scale(app, 299, 300, 100, 100) == 2

    def test_negative_window_clamped(self):
        app = _mock_app(max_auto_scale=4)
        result = _fit_scale(app, -10, -10, 100, 100)
        assert result >= 1

    def test_negative_base_clamped(self):
        app = _mock_app(max_auto_scale=4)
        result = _fit_scale(app, 800, 600, -100, -50)
        assert result >= 1


class TestBaseLayoutSizeEdge:
    def test_missing_toolbar_attrs(self):
        """Missing toolbar/scene_tabs/status treated as 0."""
        app = SimpleNamespace(designer=SimpleNamespace(width=256, height=128))
        w, h = _base_layout_size(app, palette_w=0, inspector_w=0)
        assert w >= 1
        assert h >= 1

    def test_very_large_panels(self):
        app = _layout_app(canvas_w=10, canvas_h=10, toolbar_h=0, scene_tabs_h=0, status_h=0)
        w, h = _base_layout_size(app, palette_w=5000, inspector_w=5000)
        assert w == 10010
        assert h == 10


class TestRecomputeScaleEdge:
    def test_zero_window_size(self):
        """Zero window size shouldn't crash."""
        app = _recompute_app(max_auto_scale=4)
        recompute_scale_for_window(app, 0, 0)
        assert app.scale >= 1

    def test_very_small_canvas(self):
        """Tiny canvas can scale up more."""
        app = _recompute_app(canvas_w=1, canvas_h=1, toolbar_h=0,
                             scene_tabs_h=0, status_h=0,
                             palette_w=0, inspector_w=0, max_auto_scale=10)
        recompute_scale_for_window(app, 10, 10)
        assert app.scale == 10

    def test_asymmetric_window(self):
        """Window much wider than tall limits scale."""
        app = _recompute_app(canvas_w=100, canvas_h=100, toolbar_h=0,
                             scene_tabs_h=0, status_h=0,
                             palette_w=0, inspector_w=0, max_auto_scale=10)
        recompute_scale_for_window(app, 1000, 200)
        # Height limits: 200 // 100 = 2
        assert app.scale == 2


class TestSetScaleEdge:
    def test_set_zero_becomes_1(self):
        app = _recompute_app(max_auto_scale=4)
        app.window = None
        app._mark_dirty = lambda: None
        set_scale(app, 0)
        assert app.scale == 1

    def test_set_exact_max(self):
        app = _recompute_app(max_auto_scale=3)
        app.window = None
        app._mark_dirty = lambda: None
        set_scale(app, 3)
        assert app.scale == 3
