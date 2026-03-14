"""Tests for windowing.py functions not covered by test_windowing.py:
handle_video_resize, toggle_fullscreen, compute_scale, rebuild_layout,
hardware_accelerated_scale.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from cyberpunk_designer.windowing import (
    compute_scale,
    handle_video_resize,
    hardware_accelerated_scale,
    rebuild_layout,
    toggle_fullscreen,
)


@pytest.fixture(autouse=True)
def _init_pygame():
    pygame.init()
    pygame.display.set_mode((640, 480))
    yield
    pygame.quit()


def _full_app(
    canvas_w: int = 256,
    canvas_h: int = 128,
    scale: int = 2,
    panels_collapsed: bool = False,
) -> SimpleNamespace:
    """Build an app mock with enough state for rebuild_layout & friends."""
    designer = SimpleNamespace(width=canvas_w, height=canvas_h)
    state = SimpleNamespace(
        layout=None,
        current_scene=MagicMock(
            return_value=SimpleNamespace(width=canvas_w, height=canvas_h)
        ),
    )
    window = pygame.display.set_mode((640, 480))
    logical_surface = pygame.Surface((640, 480))
    return SimpleNamespace(
        designer=designer,
        state=state,
        window=window,
        logical_surface=logical_surface,
        layout=None,
        scale=scale,
        max_auto_scale=4,
        toolbar_h=24,
        scene_tabs_h=14,
        status_h=18,
        _default_palette_w=120,
        _default_inspector_w=200,
        panels_collapsed=panels_collapsed,
        fullscreen=False,
        _scale_locked=False,
        _render_scale_x=1.0,
        _render_scale_y=1.0,
        _render_offset_x=0,
        _render_offset_y=0,
        scene_rect=pygame.Rect(0, 0, canvas_w, canvas_h),
        _mark_dirty=MagicMock(),
    )


# ── handle_video_resize ─────────────────────────────────────────────────── #


class TestHandleVideoResize:
    def test_basic_resize(self):
        app = _full_app()
        handle_video_resize(app, 800, 600)
        assert app.layout is not None
        assert app.scale >= 1

    def test_locked_scale_preserved(self):
        app = _full_app(scale=2)
        app._scale_locked = True
        handle_video_resize(app, 1200, 900)
        # Locked scale should be respected (capped by fit)
        assert app.scale <= 2

    def test_small_window(self):
        app = _full_app()
        handle_video_resize(app, 100, 100)
        assert app.scale == 1

    def test_very_large_window(self):
        app = _full_app()
        handle_video_resize(app, 3840, 2160)
        assert app.scale >= 1
        assert app.scale <= app.max_auto_scale


# ── toggle_fullscreen ────────────────────────────────────────────────────── #


class TestToggleFullscreen:
    def test_enter_fullscreen(self):
        app = _full_app()
        assert not app.fullscreen
        with patch("pygame.display.Info") as mock_info:
            mock_info.return_value = SimpleNamespace(current_w=1920, current_h=1080)
            toggle_fullscreen(app)
        assert app.fullscreen is True
        assert app.layout is not None

    def test_exit_fullscreen(self):
        app = _full_app()
        app.fullscreen = True
        toggle_fullscreen(app)
        assert app.fullscreen is False
        assert app.layout is not None

    def test_toggle_twice_returns_to_windowed(self):
        app = _full_app()
        original_fullscreen = app.fullscreen
        with patch("pygame.display.Info") as mock_info:
            mock_info.return_value = SimpleNamespace(current_w=1920, current_h=1080)
            toggle_fullscreen(app)
            toggle_fullscreen(app)
        assert app.fullscreen == original_fullscreen


# ── compute_scale ────────────────────────────────────────────────────────── #


class TestComputeScale:
    def test_with_forced_window(self):
        app = _full_app()
        s = compute_scale(app, force_window=(1200, 800))
        assert isinstance(s, int)
        assert s >= 1

    def test_panels_collapsed_gives_higher_scale(self):
        app_normal = _full_app()
        app_collapsed = _full_app(panels_collapsed=True)
        s_normal = compute_scale(app_normal, force_window=(800, 600))
        s_collapsed = compute_scale(app_collapsed, force_window=(800, 600))
        assert s_collapsed >= s_normal

    def test_small_window_returns_1(self):
        app = _full_app()
        s = compute_scale(app, force_window=(100, 100))
        assert s == 1

    def test_large_window_respects_max(self):
        app = _full_app()
        app.max_auto_scale = 3
        s = compute_scale(app, force_window=(9999, 9999))
        assert s <= 3


# ── rebuild_layout ───────────────────────────────────────────────────────── #


class TestRebuildLayout:
    def test_creates_layout_and_surface(self):
        app = _full_app()
        rebuild_layout(app, window_size=(800, 600))
        assert app.layout is not None
        assert app.logical_surface is not None
        assert app.layout.width > 0
        assert app.layout.height > 0

    def test_scene_rect_computed(self):
        app = _full_app()
        rebuild_layout(app, window_size=(800, 600))
        assert isinstance(app.scene_rect, pygame.Rect)
        assert app.scene_rect.width >= 1
        assert app.scene_rect.height >= 1

    def test_lock_scale(self):
        app = _full_app()
        rebuild_layout(app, window_size=(1600, 1200), lock_scale=2)
        assert app.scale <= 2

    def test_collapsed_panels(self):
        app = _full_app(panels_collapsed=True)
        rebuild_layout(app, window_size=(800, 600))
        assert app.layout.palette_w == 0
        assert app.layout.inspector_w == 0

    def test_marks_dirty(self):
        app = _full_app()
        rebuild_layout(app, window_size=(800, 600))
        app._mark_dirty.assert_called()

    def test_state_layout_synced(self):
        app = _full_app()
        rebuild_layout(app, window_size=(800, 600))
        assert app.state.layout is app.layout

    def test_tiny_window(self):
        app = _full_app()
        rebuild_layout(app, window_size=(1, 1))
        assert app.scale == 1
        assert app.layout.width >= 1


# ── hardware_accelerated_scale ───────────────────────────────────────────── #


class TestHardwareAcceleratedScale:
    def test_basic_scaling(self):
        app = _full_app()
        rebuild_layout(app, window_size=(800, 600))
        hardware_accelerated_scale(app)
        assert app._render_scale_x >= 1.0
        assert app._render_scale_y >= 1.0
        assert app._render_offset_x >= 0
        assert app._render_offset_y >= 0

    def test_offsets_center_content(self):
        app = _full_app(canvas_w=100, canvas_h=50)
        rebuild_layout(app, window_size=(800, 600))
        hardware_accelerated_scale(app)
        # With a small scene and big window, there should be offsets
        assert app._render_offset_x >= 0
        assert app._render_offset_y >= 0

    def test_scale_clamped_by_max(self):
        app = _full_app()
        app.max_auto_scale = 1
        rebuild_layout(app, window_size=(800, 600))
        hardware_accelerated_scale(app)
        assert app._render_scale_x <= 1.0
