from __future__ import annotations

import sys
import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_RENDER_SPEC = importlib.util.spec_from_file_location(
    "m5_preview_din_rx_render", ROOT / "tools" / "preview_din_rx_render.py"
)
assert _RENDER_SPEC is not None and _RENDER_SPEC.loader is not None
render = importlib.util.module_from_spec(_RENDER_SPEC)
sys.modules[_RENDER_SPEC.name] = render
_RENDER_SPEC.loader.exec_module(render)


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


def test_dinmeter_render_records_text_boxes_and_czech_labels_inside_screen() -> None:
    scenarios = {
        "fire": render.scenes()["main_firing"],
        "fade": render.scenes()["main_idle"],
        "saw_down": (
            render.View(
                rows_visible=True,
                row_scroll=3,
                selected_row=3,
                config=render.EffectConfig(shape=render.EFFECT_SHAPE_SAWTOOTH, shape_param=20, repeat=0),
            ),
            "main",
        ),
        "infinite_total": (
            render.View(config=render.EffectConfig(repeat=0), rows_visible=False),
            "main",
        ),
    }
    labels: set[str] = set()

    for name, (view, page) in scenarios.items():
        text_ops = [op for op in render.render_ops(view, page=page) if op.kind == "text"]
        labels.update(op.text for op in text_ops)
        for op in text_ops:
            assert op.bbox is not None, (name, op)
            left, top, right, bottom = op.bbox
            assert 0 <= left < right <= render.SCREEN_W, (name, op)
            assert 0 <= top < bottom <= render.SCREEN_H, (name, op)

    for label in {"PÁLÍ", "PŘECHOD", "SMĚR", "DOLŮ", "CELKOVÁ DOBA", "nekon."}:
        assert label in labels


def test_dinmeter_preview_orange_screen_keeps_lower_content_nonblank() -> None:
    view, page = render.scenes()["main_preview"]
    ops = render.render_ops(view, page=page)
    lower_text = [
        op
        for op in ops
        if op.kind == "text" and op.bbox is not None and op.bbox[1] >= render.ROW_Y
    ]

    assert any(op.text == "CELKOVÁ DOBA" for op in lower_text)
    assert any(op.text == "PŘED" for op in lower_text)


def test_dinmeter_builtin_scene_text_boxes_do_not_collide() -> None:
    def intersects(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
        ax0, ay0, ax1, ay1 = a
        bx0, by0, bx1, by1 = b
        return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1

    for name, (view, page) in render.scenes().items():
        text_ops = [
            op
            for op in render.render_ops(view, page=page)
            if op.kind == "text" and op.bbox is not None and op.text != "!"
        ]
        for i, left in enumerate(text_ops):
            for right in text_ops[i + 1 :]:
                assert not intersects(left.bbox, right.bbox), (name, left, right)
