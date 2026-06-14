from __future__ import annotations

import sys
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_STUDIO_SPEC = importlib.util.spec_from_file_location(
    "m5_dinmeter_studio", ROOT / "tools" / "dinmeter_studio.py"
)
assert _STUDIO_SPEC is not None and _STUDIO_SPEC.loader is not None
studio = importlib.util.module_from_spec(_STUDIO_SPEC)
sys.modules[_STUDIO_SPEC.name] = studio
_STUDIO_SPEC.loader.exec_module(studio)


def test_build_view_clamps_invalid_controls_and_preserves_valid_palette_cells() -> None:
    view, page = studio.build_view(
        {
            "state": "PALI",
            "mode": "invalid",
            "shape": "99",
            "shape_param": "not-an-int",
            "period_ms": "99999",
            "repeat": "-7",
            "intensity": "101",
            "led0": "-1",
            "led1": "999",
            "led2": "120",
            "led3": "bad",
            "battery_percent": "-5",
            "selected_row": "7",
            "selected_delay_led": "9",
            "elapsed_ms": "9999",
            "page": "missing",
            "pre_trigger": "true",
            "rows_visible": "TRUE",
            "editing": "0",
            "pal_count": "3",
            "pal0": "#000102",
            "pal1": "bad",
            "pal2": "abcdef",
        }
    )

    assert page == "main"
    assert view.status == "PALI"
    assert view.mode == "fire"
    assert view.armed is False
    assert view.battery_percent == 0
    assert view.rows_visible is True
    assert view.row_scroll == 6
    assert view.selected_row == 7
    assert view.editing is False
    assert view.selected_delay_led == 3
    assert view.elapsed_ms == 3000
    assert view.palette == ((0, 1, 2), studio.P.View().palette[1], (171, 205, 239))

    assert view.config.pre_trigger is True
    assert view.config.shape == studio.P.EFFECT_SHAPE_EXP
    assert view.config.shape_param == studio.P.EffectConfig().shape_param
    assert view.config.period_ms == 3000
    assert view.config.repeat == 0
    assert view.config.intensity == 100
    assert view.config.led_delay_ms == (0, 500, 120, studio.P.EffectConfig().led_delay_ms[3])


@pytest.mark.parametrize(
    "state,expected_status,expected_mode,expected_armed",
    [
        ("KLID", "KLID", "idle", False),
        ("NABITO", "NABITO", "idle", True),
        ("PALI", "PALI", "fire", False),
        ("STOP", "STOP", "idle", False),
        ("bogus", "KLID", "idle", False),
    ],
)
def test_state_selection_sets_status_mode_and_armed_defaults(
    state: str,
    expected_status: str,
    expected_mode: str,
    expected_armed: bool,
) -> None:
    view, page = studio.build_view({"state": state, "page": "delays"})

    assert page == "delays"
    assert view.status == expected_status
    assert view.mode == expected_mode
    assert view.armed is expected_armed


def test_explicit_mode_can_override_state_default_when_allowed() -> None:
    view, _ = studio.build_view({"state": "NABITO", "mode": "preview"})

    assert view.status == "NABITO"
    assert view.mode == "preview"
    assert view.armed is True


def test_defaults_match_renderer_defaults_and_hex_palette_format() -> None:
    defaults = studio.DEFAULTS
    renderer_view = studio.P.View()

    assert defaults["state"] == "KLID"
    assert defaults["shape"] == studio.P.EFFECT_SHAPE_SINE2
    assert defaults["period_ms"] == studio.P.DEFAULT_PERIOD_MS
    assert defaults["repeat"] == studio.P.DEFAULT_REPEAT
    assert defaults["pal_count"] == len(renderer_view.palette)

    for index in range(8):
        color = renderer_view.palette[index] if index < len(renderer_view.palette) else (255, 255, 255)
        assert defaults[f"pal{index}"] == "#%02x%02x%02x" % color


@pytest.mark.parametrize("name,scene", studio.P.scenes().items())
def test_presets_reconstruct_supported_renderer_scene_fields_through_build_view(
    name: str,
    scene: tuple[studio.P.View, str],
) -> None:
    expected_view, expected_page = scene
    actual_view, actual_page = studio.build_view({key: str(value) for key, value in studio.PRESETS[name].items()})

    assert actual_page == expected_page
    assert actual_view.status == ("PALI" if expected_view.mode == "fire" else expected_view.status)
    assert actual_view.mode == ("fire" if expected_view.mode == "fire" else "idle")
    assert actual_view.armed == expected_view.armed
    assert actual_view.config == expected_view.config
    assert actual_view.battery_percent == expected_view.battery_percent
    assert actual_view.rows_visible == expected_view.rows_visible
    assert actual_view.row_scroll == max(0, min(max(0, expected_view.selected_row), 6))
    assert actual_view.selected_row == max(0, expected_view.selected_row)
    assert actual_view.editing == expected_view.editing
    assert actual_view.selected_delay_led == expected_view.selected_delay_led
    assert actual_view.elapsed_ms == expected_view.elapsed_ms
    assert actual_view.palette_fade == expected_view.palette_fade
    assert actual_view.palette == expected_view.palette
