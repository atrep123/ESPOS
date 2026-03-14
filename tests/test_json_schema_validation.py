"""Tests for JSON schema validation of UI design files.

AQ: Validates main_scene.json against schemas/ui_design.schema.json
and tests that invalid designs are correctly rejected.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "ui_design.schema.json"
MAIN_SCENE_PATH = Path(__file__).resolve().parents[1] / "main_scene.json"


@pytest.fixture(scope="module")
def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def main_scene():
    return json.loads(MAIN_SCENE_PATH.read_text(encoding="utf-8"))


def _minimal_design(widgets=None, **scene_kw):
    """Build a minimal valid design dict."""
    scene = {"widgets": widgets or [], "width": 128, "height": 64}
    scene.update(scene_kw)
    return {"scenes": {"main": scene}}


def _validate(data, schema):
    jsonschema.validate(data, schema)


def _is_valid(data, schema):
    try:
        _validate(data, schema)
        return True
    except jsonschema.ValidationError:
        return False


# ── main_scene.json validates against schema ─────────────────────────


def test_main_scene_is_valid(schema, main_scene):
    """The actual main_scene.json must validate against the schema."""
    _validate(main_scene, schema)


# ── Required top-level structure ─────────────────────────────────────


def test_empty_object_invalid(schema):
    assert not _is_valid({}, schema)


def test_scenes_required(schema):
    assert not _is_valid({"width": 256, "height": 128}, schema)


def test_minimal_valid(schema):
    d = _minimal_design()
    assert _is_valid(d, schema)


# ── Widget type enum validation ──────────────────────────────────────


def test_valid_widget_types(schema):
    for wtype in [
        "label",
        "box",
        "button",
        "gauge",
        "progressbar",
        "checkbox",
        "radiobutton",
        "slider",
        "textbox",
        "panel",
        "icon",
        "chart",
        "list",
        "toggle",
    ]:
        d = _minimal_design(
            [
                {
                    "type": wtype,
                    "x": 0,
                    "y": 0,
                    "width": 20,
                    "height": 10,
                }
            ]
        )
        assert _is_valid(d, schema), f"{wtype} should be valid"


def test_invalid_widget_type(schema):
    d = _minimal_design(
        [
            {
                "type": "not_a_widget",
                "x": 0,
                "y": 0,
                "width": 20,
                "height": 10,
            }
        ]
    )
    assert not _is_valid(d, schema)


# ── Widget required fields ───────────────────────────────────────────


def test_widget_missing_type(schema):
    d = _minimal_design([{"x": 0, "y": 0, "width": 20, "height": 10}])
    assert not _is_valid(d, schema)


def test_widget_missing_x(schema):
    d = _minimal_design([{"type": "label", "y": 0, "width": 20, "height": 10}])
    assert not _is_valid(d, schema)


def test_widget_missing_y(schema):
    d = _minimal_design([{"type": "label", "x": 0, "width": 20, "height": 10}])
    assert not _is_valid(d, schema)


def test_widget_missing_width(schema):
    d = _minimal_design([{"type": "label", "x": 0, "y": 0, "height": 10}])
    assert not _is_valid(d, schema)


def test_widget_missing_height(schema):
    d = _minimal_design([{"type": "label", "x": 0, "y": 0, "width": 20}])
    assert not _is_valid(d, schema)


# ── Type violations ──────────────────────────────────────────────────


def test_width_must_be_integer(schema):
    d = _minimal_design(
        [
            {
                "type": "label",
                "x": 0,
                "y": 0,
                "width": "twenty",
                "height": 10,
            }
        ]
    )
    assert not _is_valid(d, schema)


def test_x_must_be_integer(schema):
    d = _minimal_design(
        [
            {
                "type": "label",
                "x": "zero",
                "y": 0,
                "width": 20,
                "height": 10,
            }
        ]
    )
    assert not _is_valid(d, schema)


def test_checked_must_be_boolean(schema):
    d = _minimal_design(
        [
            {
                "type": "checkbox",
                "x": 0,
                "y": 0,
                "width": 14,
                "height": 14,
                "checked": "yes",
            }
        ]
    )
    assert not _is_valid(d, schema)


def test_border_must_be_boolean(schema):
    d = _minimal_design(
        [
            {
                "type": "label",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 12,
                "border": 1,
            }
        ]
    )
    assert not _is_valid(d, schema)


def test_z_index_must_be_integer(schema):
    d = _minimal_design(
        [
            {
                "type": "label",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 12,
                "z_index": "front",
            }
        ]
    )
    assert not _is_valid(d, schema)


# ── Minimum value constraints ────────────────────────────────────────


def test_width_minimum_1(schema):
    d = _minimal_design(
        [
            {
                "type": "label",
                "x": 0,
                "y": 0,
                "width": 0,
                "height": 10,
            }
        ]
    )
    assert not _is_valid(d, schema)


def test_height_minimum_1(schema):
    d = _minimal_design(
        [
            {
                "type": "label",
                "x": 0,
                "y": 0,
                "width": 10,
                "height": 0,
            }
        ]
    )
    assert not _is_valid(d, schema)


def test_x_minimum_0(schema):
    d = _minimal_design(
        [
            {
                "type": "label",
                "x": -1,
                "y": 0,
                "width": 10,
                "height": 10,
            }
        ]
    )
    assert not _is_valid(d, schema)


def test_scene_width_minimum_1(schema):
    d = _minimal_design(width=0)
    assert not _is_valid(d, schema)


# ── Enum field validation ────────────────────────────────────────────


def test_invalid_align(schema):
    d = _minimal_design(
        [
            {
                "type": "label",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 12,
                "align": "justify",
            }
        ]
    )
    assert not _is_valid(d, schema)


def test_valid_align(schema):
    for a in ["left", "center", "right"]:
        d = _minimal_design(
            [
                {
                    "type": "label",
                    "x": 0,
                    "y": 0,
                    "width": 40,
                    "height": 12,
                    "align": a,
                }
            ]
        )
        assert _is_valid(d, schema), f"align={a} should be valid"


def test_invalid_valign(schema):
    d = _minimal_design(
        [
            {
                "type": "label",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 12,
                "valign": "baseline",
            }
        ]
    )
    assert not _is_valid(d, schema)


def test_invalid_border_style(schema):
    d = _minimal_design(
        [
            {
                "type": "label",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 12,
                "border_style": "triple",
            }
        ]
    )
    assert not _is_valid(d, schema)


def test_invalid_text_overflow(schema):
    d = _minimal_design(
        [
            {
                "type": "label",
                "x": 0,
                "y": 0,
                "width": 40,
                "height": 12,
                "text_overflow": "scroll",
            }
        ]
    )
    assert not _is_valid(d, schema)


# ── Scene structure ──────────────────────────────────────────────────


def test_scene_widgets_must_be_array(schema):
    d = {"scenes": {"main": {"widgets": "not_an_array"}}}
    assert not _is_valid(d, schema)


def test_scene_requires_widgets(schema):
    d = {"scenes": {"main": {"width": 128, "height": 64}}}
    assert not _is_valid(d, schema)


def test_multiple_scenes_valid(schema):
    d = {
        "scenes": {
            "main": {"widgets": [], "width": 128, "height": 64},
            "settings": {"widgets": [], "width": 128, "height": 64},
        }
    }
    assert _is_valid(d, schema)


# ── Data points and list items ───────────────────────────────────────


def test_data_points_must_be_numbers(schema):
    d = _minimal_design(
        [
            {
                "type": "chart",
                "x": 0,
                "y": 0,
                "width": 80,
                "height": 40,
                "data_points": [10, "not_a_number", 30],
            }
        ]
    )
    assert not _is_valid(d, schema)


def test_list_items_must_be_strings(schema):
    d = _minimal_design(
        [
            {
                "type": "list",
                "x": 0,
                "y": 0,
                "width": 80,
                "height": 40,
                "list_items": ["A", 42, "C"],
            }
        ]
    )
    assert not _is_valid(d, schema)


def test_valid_data_points(schema):
    d = _minimal_design(
        [
            {
                "type": "chart",
                "x": 0,
                "y": 0,
                "width": 80,
                "height": 40,
                "data_points": [10, 20.5, 30],
            }
        ]
    )
    assert _is_valid(d, schema)


def test_valid_list_items(schema):
    d = _minimal_design(
        [
            {
                "type": "list",
                "x": 0,
                "y": 0,
                "width": 80,
                "height": 40,
                "list_items": ["Alpha", "Beta", "Gamma"],
            }
        ]
    )
    assert _is_valid(d, schema)
