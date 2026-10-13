"""Test-only adversarial numbers for deterministic C export."""

import json

import pytest

from tools.ui_codegen import as_int, chart_data_points, generate_ui_design_pair


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_nonfinite_layer_uses_integer_default(value):
    assert as_int(value, 7) == 7


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_nonfinite_chart_samples_are_skipped_without_inventing_zero(value):
    assert chart_data_points({"data_points": [12, value, -4, 1.9]}) == [12, -4, 1]


def test_chart_integer_limits_preserve_and_clamp_real_samples():
    assert chart_data_points({"data_points": [10**400, -(10**400), 32767, -32768]}) == [
        32767,
        -32768,
        32767,
        -32768,
    ]


@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_layer_numeric_mutation_does_not_abort_scene_export(value, tmp_path):
    scene = {
        "width": 1280,
        "height": 720,
        "widgets": [
            {
                "type": "label",
                "text": "control",
                "z_index": value,
                "x": 10,
                "y": 10,
                "width": 100,
                "height": 30,
            },
        ],
    }
    path = tmp_path / "test-only.json"
    path.write_text(json.dumps({"scenes": {"main": scene}}), encoding="utf-8")
    mutated = generate_ui_design_pair(path, scene_name="main", source_label="test-only")
    scene["widgets"][0]["z_index"] = 0
    path.write_text(json.dumps({"scenes": {"main": scene}}), encoding="utf-8")
    assert mutated == generate_ui_design_pair(path, scene_name="main", source_label="test-only")
