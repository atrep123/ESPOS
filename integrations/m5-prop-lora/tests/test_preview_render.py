from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import preview_din_rx_render as render  # noqa: E402


def pixel_int(image, x: int, y: int) -> int:
    r, g, b = image.getpixel((x, y))
    return (r << 16) | (g << 8) | b


def unique_pixels(image) -> set[tuple[int, int, int]]:
    colors = image.getcolors(maxcolors=image.width * image.height)
    assert colors is not None
    return {color for _, color in colors}


@pytest.mark.parametrize("name,scene", render.scenes().items())
def test_builtin_preview_scenes_render_deterministic_rgb_images(
    name: str,
    scene: tuple[render.View, str],
) -> None:
    view, page = scene
    first = render.render(view, page)
    second = render.render(view, page)

    assert first.mode == "RGB", name
    assert first.size == (render.SCREEN_W, render.SCREEN_H)
    assert first.tobytes() == second.tobytes()
    assert len(unique_pixels(first)) > 12, name


def test_hires_render_returns_supersampled_canvas_without_downscaling() -> None:
    image = render.render(render.View(), hires=True)

    assert image.mode == "RGB"
    assert image.size == (render.SCREEN_W * render.S, render.SCREEN_H * render.S)


@pytest.mark.parametrize(
    "view,point,expected",
    [
        (render.View(status="KLID", mode="idle", armed=False), (0, 20), render.COLOR_GOOD),
        (render.View(status="NABITO", mode="idle", armed=True), (100, 4), render.COLOR_WARN),
        (render.View(status="PALI", mode="fire", armed=False), (100, 4), render.COLOR_BAD),
        (render.View(status="STOP", mode="idle", armed=False), (100, 4), render.COLOR_BLUE),
    ],
)
def test_state_surfaces_use_expected_safety_colours(
    view: render.View,
    point: tuple[int, int],
    expected: int,
) -> None:
    image = render.render(view)

    assert pixel_int(image, *point) == expected


def test_live_states_draw_outer_alarm_frames_after_content() -> None:
    armed = render.render(render.View(status="NABITO", mode="idle", armed=True))
    firing = render.render(render.View(status="PALI", mode="fire", armed=False))
    stopped = render.render(render.View(status="STOP", mode="idle", armed=False))

    assert pixel_int(armed, render.SCREEN_W - 1, render.SCREEN_H - 1) == render.COLOR_WARN
    assert pixel_int(firing, render.SCREEN_W - 1, render.SCREEN_H - 1) == render.COLOR_BAD
    assert pixel_int(stopped, render.SCREEN_W - 1, render.SCREEN_H - 1) != render.COLOR_BLUE


def test_preview_playhead_position_tracks_elapsed_time_on_plot() -> None:
    config = render.EffectConfig(period_ms=1000, repeat=2, led_delay_ms=(0, 80, 160, 240))
    elapsed = render.plot_duration_ms(config) // 2
    view = render.View(status="NABITO", mode="preview", armed=True, config=config, elapsed_ms=elapsed)
    image = render.render(view, hires=True)

    x = render.PLOT_X + elapsed * render.plot_span_pixels(config) // render.plot_duration_ms(config)

    assert pixel_int(image, x * render.S, render.PLOT_TOP * render.S) == render.COLOR_TEXT


def test_palette_modes_render_distinct_legend_strips() -> None:
    fade = render.render(render.View(palette_fade=True))
    step = render.render(render.View(palette_fade=False))

    fade_pixels = unique_pixels(fade.crop((70, render.PALETTE_Y - 1, 140, render.PALETTE_Y + 8)))
    step_pixels = unique_pixels(step.crop((70, render.PALETTE_Y - 1, 140, render.PALETTE_Y + 8)))

    assert render.rgb(render.dim_rgb(render.COLOR_TEAL, 55)) in fade_pixels
    assert render.rgb(render.dim_rgb(render.COLOR_WARN, 55)) in step_pixels
    assert fade_pixels != step_pixels


def test_waveform_plot_contracts_cover_infinite_repeat_and_pretrigger_floor() -> None:
    infinite = render.EffectConfig(repeat=0)
    pretrigger = replace(infinite, pre_trigger=True)

    assert render.plot_has_multiplier(infinite) is True
    assert render.plot_visible_cycles(infinite) == render.PLOT_MAX_CYCLES
    assert render.finite_effect_total_ms(infinite) == (False, 0)
    assert render.plot_level_at(pretrigger, 2, -1) == render.plot_floor_level(pretrigger) == 41
