"""Regressions at the optional model and profile boundaries used by type checks."""

from dataclasses import replace

import pytest

from tools import validate_design
from ui_designer import UIDesigner, _preflight_scene
from ui_models import WidgetConfig


@pytest.mark.parametrize("size", [None, 0, -1])
def test_model_dimension_defaults_remain_resizable(size):
    designer = UIDesigner(256, 128)
    scene = designer.create_scene("main")
    widget = WidgetConfig(type="button", x=2, y=2, width=20, height=12, text="OK")
    widget.width = size
    widget.height = size
    scene.widgets.append(widget)
    designer.current_scene = scene.name
    before = (widget.width, widget.height)

    designer.resize_widget(0, 2, 3)

    result = _preflight_scene(scene)

    assert (widget.width, widget.height) == (before[0] + 2, before[1] + 3)
    assert result["ok"] is True


@pytest.mark.parametrize("size", [None, 0, -1])
def test_raw_json_invalid_dimensions_are_not_clamped_by_type_narrowing(size):
    data = {
        "scenes": {
            "main": {
                "width": 256,
                "height": 128,
                "widgets": [{"type": "box", "x": 2, "y": 2, "width": size, "height": 12}],
            }
        }
    }
    issues = validate_design.validate_data(data, file_label="raw.json", warnings_as_errors=False)
    assert any(issue.level == "ERROR" for issue in issues)


def test_unrestricted_font_still_validates_geometry_and_text_fit(monkeypatch):
    profile = replace(validate_design.PROFILE_OLED256, name="unrestricted", font_chars=None)
    monkeypatch.setitem(validate_design.PROFILES, profile.name, profile)
    data = {
        "device": profile.name,
        "scenes": {
            "main": {
                "width": 256,
                "height": 128,
                "widgets": [
                    {
                        "type": "label",
                        "x": 2,
                        "y": 2,
                        "width": 10,
                        "height": 12,
                        "text": "Žluťoučký",
                        "color_fg": "white",
                        "color_bg": "black",
                    }
                ],
            }
        },
    }

    messages = [
        issue.message
        for issue in validate_design.validate_data(
            data, file_label="unrestricted.json", warnings_as_errors=False
        )
    ]

    assert not any("unsupported chars" in message for message in messages)
    assert any("overflows max" in message for message in messages)
